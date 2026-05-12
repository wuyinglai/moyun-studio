"""墨韵 - Prompt模板引擎

渲染Jinja2模板，支持片段引用@{file_path}。
使用依赖注入来解耦FileService。
"""

import re
import tiktoken
from pathlib import Path
from typing import Any, TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from backend.services.base import FileServiceInterface


class PromptEngine:
    """Prompt模板引擎

    职责：
    - 加载Jinja2模板
    - 渲染变量
    - 解析片段引用 @{file_path}

    使用依赖注入接收FileService，便于测试时替换为Mock实现。
    """

    REFERENCE_PATTERN = re.compile(r"@\{([^}]+)\}")

    def __init__(
        self,
        prompts_path: Path | str | None = None,
        file_service: "FileServiceInterface | None" = None,
    ):
        if prompts_path is None:
            prompts_path = Path("workspace/prompts")

        self.prompts_path = Path(prompts_path)
        self.file_service = file_service
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_path)),
            autoescape=False,
        )

    def set_file_service(self, file_service: "FileServiceInterface") -> None:
        """设置文件服务（用于依赖注入）"""
        self.file_service = file_service

    def load_template(self, category: str, template_type: str) -> Any:
        """加载模板

        Args:
            category: 模板类别（generate/extract/transform）
            template_type: 模板类型（如 chapter, character）

        Returns:
            Jinja2 Template对象
        """
        template_path = f"{category}/{template_type}/main.md"
        return self.env.get_template(template_path)

    async def render(
        self,
        prompt_type: str,
        variables: dict[str, Any]
    ) -> str:
        """渲染模板

        Args:
            prompt_type: Prompt类型，格式为 category/template_type（如 generate/chapter）
            variables: 渲染变量

        Returns:
            渲染后的字符串
        """
        # 解析 prompt_type，支持 category/template_type 格式
        parts = prompt_type.split("/", 1)
        if len(parts) == 2:
            category, template_type = parts
        else:
            category = "generate"
            template_type = prompt_type
        
        resolved_variables = await self._resolve_references(variables)
        template = self.load_template(category, template_type)
        return template.render(**resolved_variables)

    async def _resolve_references(self, variables: dict[str, Any]) -> dict[str, Any]:
        """解析变量中的片段引用

        @{file_path} -> 文件内容
        """
        if self.file_service is None:
            return variables

        resolved = {}
        for key, value in variables.items():
            if isinstance(value, str):
                match = self.REFERENCE_PATTERN.search(value)
                if match:
                    file_path = match.group(1)
                    try:
                        content, _ = await self.file_service.read_file(file_path)
                        resolved[key] = content
                    except Exception:
                        resolved[key] = value
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = await self._resolve_references(value)
            elif isinstance(value, list):
                resolved_list = []
                for v in value:
                    if isinstance(v, str):
                        match = self.REFERENCE_PATTERN.search(v)
                        if match:
                            file_path = match.group(1)
                            try:
                                content, _ = await self.file_service.read_file(file_path)
                                resolved_list.append(content)
                            except Exception:
                                resolved_list.append(v)
                        else:
                            resolved_list.append(v)
                    else:
                        resolved_list.append(v)
                resolved[key] = resolved_list
            else:
                resolved[key] = value

        return resolved

    def resolve_reference_sync(self, content: str) -> str:
        """同步解析片段引用（不解析文件内容，只返回占位符）"""
        return self.REFERENCE_PATTERN.sub(r"[\g<1>]", content)

    async def estimate_tokens(self, text: str) -> int:
        """估算token数"""
        try:
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars * 0.5 + other_chars * 0.25)

    def get_template_path(self, category: str, template_type: str) -> Path:
        """获取模板文件路径"""
        return self.prompts_path / category / template_type / "main.md"
