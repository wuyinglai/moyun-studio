"""墨韵 - LLM服务

封装LiteLLM调用，提供流式输出和重试机制。
"""

import asyncio
from collections.abc import AsyncGenerator
import logging
from typing import TYPE_CHECKING, Any

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import tiktoken
except ImportError:
    tiktoken = None

from backend.core.exceptions import LLMAPIError, LLMCircuitOpenError, LLMError
from backend.core.llm_circuit_breaker import LLMCircuitBreaker, get_circuit_breaker

if TYPE_CHECKING:
    pass


def load_llm_config_from_workspace(settings) -> dict:
    """从工作区加载 LLM 配置

    按优先级读取：
    1. workspace/llm_config.json（旧格式）
    2. workspace/.config.json 下的 "llm" 键（LLM API 保存的格式）
    3. 回退到 Settings（.env 中的全局配置）

    返回 dict，包含键：apiType, apiKey, apiBase, model, thinking
    """
    import json

    # 1) 旧格式 llm_config.json
    config_file = settings.workspace_path / "llm_config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return {
                "apiType": data.get("apiType", data.get("api_type", settings.llm_provider)),
                "apiKey": data.get("apiKey") or data.get("api_key") or settings.llm_api_key,
                "apiBase": data.get("apiBase", data.get("api_base", settings.llm_api_base or "")),
                "model": data.get("model", settings.llm_model),
                "thinking": data.get("thinking", settings.llm_thinking),
            }
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger(__name__).warning(f"读取 llm_config.json 失败: {e}")

    # 2) .config.json（LLM API 保存到此文件）
    dot_config = settings.workspace_path / ".config.json"
    if dot_config.exists():
        try:
            full = json.loads(dot_config.read_text(encoding="utf-8"))
            data = full.get("llm") or {}
            if data.get("apiKey") or data.get("model"):
                return {
                    "apiType": data.get("apiType", data.get("api_type", settings.llm_provider)),
                    "apiKey": data.get("apiKey") or data.get("api_key") or settings.llm_api_key,
                    "apiBase": data.get("apiBase") or data.get("apiUrl") or data.get("api_base") or settings.llm_api_base or "",
                    "model": data.get("model", settings.llm_model),
                    "thinking": data.get("thinking", settings.llm_thinking),
                }
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger(__name__).warning(f"读取 .config.json 失败: {e}")

    # 3) 回退到 Settings
    return {
        "apiType": settings.llm_provider,
        "apiKey": settings.llm_api_key,
        "apiBase": settings.llm_api_base or "",
        "model": settings.llm_model,
        "thinking": settings.llm_thinking,
    }


def normalize_model_for_provider(model: str, api_type: str) -> str:
    """为 LiteLLM 调用规范化模型名称

    LiteLLM 使用 ``provider/model`` 格式路由请求。
    DeepSeek API 兼容 OpenAI 格式，但 LiteLLM 1.x 不支持 ``deepseek/`` 前缀，
    所以 deepseek provider 使用 ``openai/`` 前缀。
    """
    api_type = (api_type or "").lower()

    # 处理 api_type == deepseek 但模型已有 deepseek/ 前缀的情况
    if api_type == "deepseek" and model.startswith("deepseek/"):
        return "openai/" + model[len("deepseek/"):]

    if "/" in model:
        return model

    if api_type == "ollama":
        return f"ollama/{model}"
    if api_type == "anthropic":
        return f"anthropic/{model}"
    if api_type == "deepseek":
        # DeepSeek API 兼容 OpenAI 格式，LiteLLM 1.x 不支持 deepseek/ 前缀
        return f"openai/{model}"
    if api_type == "openai":
        # openai/ 前缀可省略，但显式加上更清晰
        return f"openai/{model}"
    # custom：不追加前缀，由 api_base 决定路由
    return model


def _is_openai_compatible_base_url(api_base: str | None) -> bool:
    """Return True for custom providers that expose OpenAI-compatible /v1 APIs."""
    if not api_base:
        return False
    normalized = api_base.rstrip("/").lower()
    return (
        normalized.endswith("/v1")
        or "openai" in normalized
        or "apihub.agnes-ai.com" in normalized
    )


def build_litellm_kwargs(llm_cfg: dict, model: str, messages: list, **kwargs) -> dict:
    """构建 litellm.acompletion() 的参数字典

    ``llm_cfg`` 由 ``load_llm_config_from_workspace`` 返回，
    额外参数（temperature、max_tokens、stream、timeout 等）
    通过 ``**kwargs`` 传入。
    """
    result = {
        "model": model,
        "messages": messages,
    }

    api_key = llm_cfg.get("apiKey") or llm_cfg.get("api_key")
    if api_key:
        result["api_key"] = api_key

    api_base = llm_cfg.get("apiBase") or llm_cfg.get("api_base")
    if api_base:
        result["api_base"] = api_base

    result.update(kwargs)
    return result


class LLMConfig:
    """LLM配置"""

    # 常见模型的上下文窗口映射
    MODEL_CONTEXT_WINDOW = {
        # OpenAI
        "gpt-4": 8192,
        "gpt-4-0613": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-3.5-turbo-1106": 16384,
        # DeepSeek
        "deepseek-chat": 8192,
        "deepseek-r1-chat": 128000,
        "deepseek-v4-flash": 128000,
        "deepseek-v3": 128000,
        "deepseek-v4": 128000,
        # Qwen
        "qwen-7b-chat": 8192,
        "qwen-14b-chat": 16384,
        "qwen-72b-chat": 32768,
        "qwen-1.5-7b-chat": 32768,
        "qwen-1.5-14b-chat": 32768,
        "qwen-1.5-32b-chat": 64000,
        "qwen-2-7b-instruct": 32768,
        "qwen-2-14b-instruct": 64000,
        "qwen-2-72b-instruct": 128000,
        # Llama 3
        "llama3-8b": 8192,
        "llama3-70b": 8192,
        "llama3-1-8b": 128000,
        "llama3-1-70b": 128000,
        # Mixtral
        "mixtral-8x7b": 32768,
        "mixtral-8x22b": 64000,
        # Claude
        "claude-3-sonnet": 200000,
        "claude-3-opus": 200000,
        "claude-3-5-sonnet": 200000,
        "claude-2": 100000,
        # Agnes AI
        "agnes-2.0-flash": 262144,
    }

    def __init__(
        self,
        provider: str = "openai",
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "gpt-4",
        max_tokens: int = 16000,
        temperature: float = 0.7,
        context_window: int | None = None,
        reserved_output_tokens: int = 3000,
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.reserved_output_tokens = reserved_output_tokens
        # 根据模型名推断上下文窗口
        self.context_window = context_window or self._infer_context_window(model)

    def _infer_context_window(self, model: str) -> int:
        """根据模型名称推断上下文窗口大小"""
        # 移除 provider 前缀
        model_name = model.split("/")[-1].lower()

        # 精确匹配
        for key, window in self.MODEL_CONTEXT_WINDOW.items():
            if key.lower() in model_name or model_name in key.lower():
                return window

        # 按参数推断
        if "7b" in model_name or "8b" in model_name:
            return 8192
        elif "14b" in model_name:
            return 16384
        elif "27b" in model_name:
            return 32768
        elif "32b" in model_name:
            return 32768
        elif "72b" in model_name or "70b" in model_name:
            return 64000

        # DeepSeek 族模型默认 128k（避免未录入的新模型回退到 8k）
        if "deepseek" in model_name:
            return 128000

        # Qwen 族模型默认 32k（未匹配到精确参数时）
        if "qwen" in model_name.lower():
            return 32768

        # 默认返回 GPT-4 级别
        return 8192

    @property
    def max_prompt_tokens(self) -> int:
        """计算最大提示词token数"""
        return max(0, self.context_window - self.reserved_output_tokens)


def _is_reasoning_only_model_response(text: str) -> bool:
    """检测文本是否像推理日志而非正式正文

    检查常见的推理/分析标记。如果检测到这些模式，
    说明模型可能输出了推理过程而非最终结果。
    """
    if not text:
        return False

    # 推理日志常见模式
    reasoning_patterns = [
        "*   Original",
        "*   Literal",
        "*   Context:",
        "*   Meaning:",
        "*   Strengths:",
        "*   Task:",
        "*   Constraint:",
        "*   Option",
        "Original phrase:",
        "Literal meaning:",
        "analysis",
        "Analysis:",
        "Task:",
    ]

    text_lower = text.lower()
    for pattern in reasoning_patterns:
        if pattern.lower() in text_lower:
            return True

    return False


def _clean_reasoning_channel_content(text: str) -> str:
    """清洗 reasoning_format=none 模式下的输出，提取纯净正文

    当使用 reasoning_format=none 时，内容会进入 content，但
    可能包含 <|channel>thought 标签和推理过程。这个函数尝试
    提取最后的正文部分，或者去掉推理标签。
    """
    if not text:
        return text

    # 首先尝试寻找：如果最后有明显的选项输出，例如 "*   *Option 1 ('...')"
    # 或者直接在最后一行有不带星号的中文句子
    lines = text.split("\n")
    useful_lines = []

    for line in lines:
        # 跳过明显的推理标签行
        line = line.strip()
        if not line:
            continue

        # 跳过 channel 标签
        if line.startswith("<|channel>") or line.startswith("</|channel>"):
            continue

        # 跳过 Input 开头的
        if line.startswith("*   Input") or line.startswith("*   Original"):
            continue

        # 跳过 Constraint/Task
        if line.startswith("*   Constraint") or line.startswith("*   Task"):
            continue

        # 跳过 Key elements/Atmosphere 等
        if line.startswith("*   Key elements:") or line.startswith("*   Atmosphere:"):
            continue

        # 跳过只有单个星号标记的行
        if (
            line.startswith("*   \"")
            or line.startswith("*   '")
            or line.startswith("*   Option")
        ):
            continue

        # 看起来像是有用内容的行
        useful_lines.append(line)

    if useful_lines:
        # 尝试找最后一个符合中文句子特征的
        for line in reversed(useful_lines):
            # 检查是否是中文字符为主
            chinese_count = sum(1 for c in line if '\u4e00' <= c <= '\u9fff')
            if chinese_count >= 5:
                # 找到了看起来像中文正文的
                return line.strip()

        # 没有特别明显的，就把有用的行合并
        return "\n".join(useful_lines)

    # 如果没有提取出有用内容，就原样返回
    return text


class LLMService:
    """LLM调用服务

    职责：
    - 封装LiteLLM调用
    - 提供流式输出
    - 自动重试机制
    - Token计数
    - 并发控制（Semaphore）
    """
    logger = logging.getLogger(__name__)

    # 类级别的并发限制（默认最多 3 个并发）
    _semaphore: asyncio.Semaphore | None = None
    _max_concurrent: int = 3

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        # 确保 Semaphore 已初始化
        if LLMService._semaphore is None:
            LLMService._semaphore = asyncio.Semaphore(self._max_concurrent)

    @classmethod
    def set_max_concurrent(cls, max_concurrent: int) -> None:
        """设置最大并发数（在应用启动时调用）"""
        cls._max_concurrent = max_concurrent
        # 重新创建 Semaphore（已有请求会继续使用旧的）
        cls._semaphore = asyncio.Semaphore(max_concurrent)
        cls.logger.info(f"LLM 并发限制已设置为 {max_concurrent}")

    @classmethod
    def from_workspace_config(cls, config_dict: dict, model: str | None = None) -> "LLMService":
        """从 workspace 配置字典创建 LLMService

        Args:
            config_dict: load_llm_config_from_workspace() 返回的配置字典
            model: 可选，覆盖模型名称
        """
        provider = config_dict.get("apiType", "openai")
        api_base = config_dict.get("apiBase")
        model = model or config_dict.get("model", "gpt-4")
        if provider == "custom" and _is_openai_compatible_base_url(api_base):
            provider = "openai"
        model = normalize_model_for_provider(model, provider)

        config = LLMConfig(
            provider=provider,
            api_key=config_dict.get("apiKey"),
            api_base=api_base,
            model=model,
        )
        return cls(config)

    @property
    def client(self):
        """懒加载LiteLLM客户端"""
        if self._client is None:
            litellm.drop_params = True
            self._client = litellm
        return self._client

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = True,
        stop_event: asyncio.Event | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """流式生成

        Args:
            messages: 消息列表
            model: 模型名称，默认使用配置中的模型
            stream: 是否流式输出
            stop_event: 可选的停止信号，设置后停止后续输出
            **kwargs: 传递给 litellm 的额外参数（如 timeout, thinking 等）

        Yields:
            生成的文本片段
        """
        model = model or self.config.model

        # ── 熔断器检查 ──────────────────────────────────────────
        breaker = get_circuit_breaker()
        breaker_key = LLMCircuitBreaker.make_key(
            self.config.provider,
            self.config.api_base or "",
            model,
        )
        if not breaker.allow_request(breaker_key):
            remaining = breaker.get_remaining_timeout(breaker_key)
            raise LLMCircuitOpenError(model=model, remaining_timeout=remaining)

        call_kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        if self.config.api_key:
            call_kwargs["api_key"] = self.config.api_key
        if self.config.api_base:
            call_kwargs["api_base"] = self.config.api_base
        call_kwargs.update(kwargs)

        # 使用 Semaphore 控制并发
        async with self._semaphore:
            try:
                response = await self._call_with_retry(**call_kwargs)

                if stream:
                    async for chunk in response:
                        if stop_event and stop_event.is_set():
                            break
                        if not chunk.choices:
                            continue
                        content = chunk.choices[0].delta.content
                        # Fallback to reasoning_content if content is empty (for reasoning models)
                        if not content and hasattr(chunk.choices[0].delta, 'reasoning_content'):
                            content = chunk.choices[0].delta.reasoning_content
                            # Warn if the fallback content looks like reasoning log
                            if _is_reasoning_only_model_response(content):
                                self.logger.warning(
                                    "LLM fallback to reasoning_content produced reasoning log, not final output. "
                                    "Consider using a model that outputs normal content."
                                )
                            # Try to clean it anyway
                            content = _clean_reasoning_channel_content(content)
                        elif content and _is_reasoning_only_model_response(content):
                            # Even in content field, if it looks like reasoning content, clean it
                            content = _clean_reasoning_channel_content(content)
                        if content:
                            yield content
                else:
                    if response.choices:
                        msg = response.choices[0].message
                        content = msg.content
                        # Fallback to reasoning_content if content is empty (for reasoning models)
                        if not content and hasattr(msg, 'reasoning_content'):
                            content = msg.reasoning_content
                            # Warn if the fallback content looks like reasoning log
                            if _is_reasoning_only_model_response(content):
                                self.logger.warning(
                                    "LLM fallback to reasoning_content produced reasoning log, not final output. "
                                    "Consider using a model that outputs normal content."
                                )
                            # Try to clean it anyway
                            content = _clean_reasoning_channel_content(content)
                        elif content and _is_reasoning_only_model_response(content):
                            # Even in content field, if it looks like reasoning content, clean it
                            content = _clean_reasoning_channel_content(content)
                        yield content

                # 调用成功，记录到熔断器
                breaker.record_success(breaker_key)

            except LLMCircuitOpenError:
                raise
            except asyncio.TimeoutError:
                breaker.record_failure(breaker_key, "timeout")
                raise LLMError(message=f"LLM 调用超时（{model}），请检查模型服务或增加超时时间") from None
            except litellm.exceptions.AuthenticationError:
                breaker.record_failure(breaker_key, "auth_error")
                raise LLMAPIError(model=model, reason="API Key 无效或已过期") from None
            except litellm.exceptions.RateLimitError:
                breaker.record_failure(breaker_key, "rate_limit")
                raise LLMAPIError(model=model, reason="请求频率超限，请稍后重试") from None
            except litellm.exceptions.Timeout:
                breaker.record_failure(breaker_key, "timeout")
                raise LLMError(message=f"LLM 请求超时（{model}），请检查网络连接或模型服务") from None
            except litellm.exceptions.APIError as e:
                breaker.record_failure(breaker_key, "api_error")
                raise LLMAPIError(model=model, reason=str(e)[:200], status_code=getattr(e, 'status_code', None)) from e
            except Exception as e:
                # 未知错误，记录到熔断器
                error_type = type(e).__name__
                self.logger.error(f"LLM 未知错误 [{error_type}]: {e}")
                breaker.record_failure(breaker_key, error_type)
                raise LLMError(message=f"LLM调用失败: {e!s}") from e

    async def _call_with_retry(self, **kwargs) -> Any:
        """带重试的调用"""
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            reraise=True
        )
        async def _call():
            return await litellm.acompletion(**kwargs)

        return await _call()

    async def complete_sync(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs,
    ) -> str:
        """同步生成（非流式）"""
        chunks = []
        async for chunk in self.complete(messages, model=model, stream=False, **kwargs):
            chunks.append(chunk)
        result = "".join(chunks)
        return result

    async def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """计算token数"""
        if tiktoken is None:
            from backend.utils.token_utils import estimate_tokens_fallback
            return estimate_tokens_fallback(text)
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.config.api_key and self.config.provider == "openai":
            return False
        return True
