"""墨韵 - LLM 熔断器

当 LLM 模型服务连续失败时，自动熔断，避免反复等待和重试拖慢系统。

状态机：
  closed → open     连续失败达到 failure_threshold
  open   → half_open reset_timeout 后自动尝试恢复
  half_open → closed  一次调用成功
  half_open → open    再次失败

支持按 provider+base_url+model 维度隔离状态。
"""

import asyncio
from enum import Enum
import json
import logging
from pathlib import Path
import time
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerConfig:
    """熔断器配置"""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_seconds: float = 60,
        half_open_max_calls: int = 1,
        enabled: bool = True,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.enabled = enabled


class _CircuitState:
    """单个 key 的熔断状态"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.half_open_calls: int = 0

    def allow_request(self) -> bool:
        """是否允许请求通过"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # 检查是否已过 reset_timeout
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.config.reset_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker 进入 half_open 状态，尝试恢复")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.half_open_max_calls:
                return True
            return False

        return False

    def record_success(self) -> None:
        """记录成功调用"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker 恢复为 closed 状态")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0

    def record_failure(self, error_type: str = "unknown") -> None:
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            # half_open 中失败，重新 open
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker half_open 调用失败，重新 open (error_type=%s)",
                error_type,
            )
            return

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker 进入 open 状态 (连续失败 %d 次, error_type=%s)",
                self.failure_count,
                error_type,
            )

    @property
    def remaining_timeout(self) -> float:
        """剩余熔断时间（秒）"""
        if self.state != CircuitState.OPEN:
            return 0
        elapsed = time.monotonic() - self.last_failure_time
        return max(0, self.config.reset_timeout_seconds - elapsed)


class LLMCircuitBreaker:
    """LLM 熔断器 — 按 provider+base_url+model 维度隔离"""

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._circuits: dict[str, _CircuitState] = {}

    @staticmethod
    def make_key(provider: str, base_url: str, model: str) -> str:
        """生成熔断器 key"""
        return f"{provider}|{base_url}|{model}"

    def _get_circuit(self, key: str) -> _CircuitState:
        if key not in self._circuits:
            self._circuits[key] = _CircuitState(self.config)
        return self._circuits[key]

    def allow_request(self, key: str) -> bool:
        """是否允许请求通过

        如果 breaker disabled，始终允许。
        """
        if not self.config.enabled:
            return True
        circuit = self._get_circuit(key)
        allowed = circuit.allow_request()
        if allowed and circuit.state == CircuitState.HALF_OPEN:
            circuit.half_open_calls += 1
        return allowed

    def record_success(self, key: str) -> None:
        """记录成功调用"""
        if not self.config.enabled:
            return
        circuit = self._get_circuit(key)
        circuit.record_success()

    def record_failure(self, key: str, error_type: str = "unknown") -> None:
        """记录失败调用"""
        if not self.config.enabled:
            return
        circuit = self._get_circuit(key)
        circuit.record_failure(error_type)

    def get_state(self, key: str) -> CircuitState:
        """获取指定 key 的熔断状态"""
        circuit = self._circuits.get(key)
        if circuit is None:
            return CircuitState.CLOSED
        return circuit.state

    def get_remaining_timeout(self, key: str) -> float:
        """获取剩余熔断时间"""
        circuit = self._circuits.get(key)
        if circuit is None:
            return 0
        return circuit.remaining_timeout

    def reset(self, key: str | None = None) -> None:
        """重置熔断状态

        Args:
            key: 指定 key 重置，None 则重置所有
        """
        if key:
            circuit = self._circuits.get(key)
            if circuit:
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.half_open_calls = 0
        else:
            for circuit in self._circuits.values():
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.half_open_calls = 0

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """获取所有 key 的熔断状态（用于调试/监控）"""
        result = {}
        for key, circuit in self._circuits.items():
            result[key] = {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "remaining_timeout": circuit.remaining_timeout,
            }
        return result

    async def save_state(self, state_file: Path) -> None:
        """将熔断状态持久化到文件"""
        data: dict[str, Any] = {}
        for key, circuit in self._circuits.items():
            data[key] = {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "last_failure_time": circuit.last_failure_time,
            }
        try:
            await asyncio.to_thread(state_file.parent.mkdir, parents=True, exist_ok=True)
            content = json.dumps(data, ensure_ascii=False, indent=2)
            await asyncio.to_thread(state_file.write_text, content, encoding="utf-8")
            logger.debug("熔断器状态已持久化到 %s (%d 条记录)", state_file, len(data))
        except OSError as e:
            logger.warning("熔断器状态持久化失败: %s", e)

    async def load_state(self, state_file: Path) -> None:
        """从文件恢复熔断状态"""
        if not await asyncio.to_thread(state_file.exists):
            return
        try:
            text = await asyncio.to_thread(state_file.read_text, encoding="utf-8")
            data = json.loads(text)
            for key, info in data.items():
                circuit = self._get_circuit(key)
                state_val = info.get("state", "closed")
                circuit.state = CircuitState(state_val)
                circuit.failure_count = info.get("failure_count", 0)
                circuit.last_failure_time = info.get("last_failure_time", 0)
            logger.info("熔断器状态已从 %s 恢复 (%d 条记录)", state_file, len(data))
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("熔断器状态恢复失败: %s", e)


# 全局熔断器实例（在 main.py lifespan 中初始化）
circuit_breaker: LLMCircuitBreaker | None = None

# 默认持久化文件路径
_STATE_FILE_NAME = ".circuit-breaker-state.json"


def get_circuit_breaker() -> LLMCircuitBreaker:
    """获取全局熔断器实例"""
    global circuit_breaker
    if circuit_breaker is None:
        circuit_breaker = LLMCircuitBreaker()
    return circuit_breaker


def init_circuit_breaker(config: CircuitBreakerConfig) -> LLMCircuitBreaker:
    """初始化全局熔断器"""
    global circuit_breaker
    circuit_breaker = LLMCircuitBreaker(config)
    logger.info(
        "LLM 熔断器已初始化 (enabled=%s, threshold=%d, reset_timeout=%ds)",
        config.enabled,
        config.failure_threshold,
        config.reset_timeout_seconds,
    )
    return circuit_breaker


def get_state_file_path(workspace_path: Path) -> Path:
    """获取熔断器状态文件路径"""
    return workspace_path / _STATE_FILE_NAME
