"""墨韵 - LLM 熔断器测试

测试内容：
1. 连续失败 3 次后 breaker open
2. open 状态下请求被快速拒绝
3. reset_timeout 后进入 half_open
4. half_open 成功后恢复 closed
5. 不同 model key 互不影响
6. breaker disabled 时不拦截请求
7. LLMService 集成：连续失败后第四次请求不调用模型
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.exceptions import LLMCircuitOpenError
from backend.core.llm_circuit_breaker import (
    CircuitBreakerConfig,
    CircuitState,
    LLMCircuitBreaker,
    _CircuitState,
    get_circuit_breaker,
    init_circuit_breaker,
)


class TestCircuitBreakerState:
    """测试 _CircuitState 状态机"""

    def test_initial_state_is_closed(self):
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        state = _CircuitState(config)
        assert state.state == CircuitState.CLOSED

    def test_consecutive_failures_open_circuit(self):
        """连续失败 3 次后 breaker open"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        state = _CircuitState(config)

        state.record_failure("timeout")
        assert state.state == CircuitState.CLOSED

        state.record_failure("timeout")
        assert state.state == CircuitState.CLOSED

        state.record_failure("timeout")
        assert state.state == CircuitState.OPEN

    def test_open_state_rejects_requests(self):
        """open 状态下请求被快速拒绝"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        state = _CircuitState(config)

        for _ in range(3):
            state.record_failure("error")

        assert state.state == CircuitState.OPEN
        assert state.allow_request() is False

    def test_reset_timeout_transitions_to_half_open(self):
        """reset_timeout 后进入 half_open"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=0.1)
        state = _CircuitState(config)

        for _ in range(3):
            state.record_failure("error")
        assert state.state == CircuitState.OPEN

        # 等待 reset_timeout
        time.sleep(0.15)

        assert state.allow_request() is True
        assert state.state == CircuitState.HALF_OPEN

    def test_half_open_success_restores_closed(self):
        """half_open 成功后恢复 closed"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=0.1)
        state = _CircuitState(config)

        for _ in range(3):
            state.record_failure("error")
        assert state.state == CircuitState.OPEN

        time.sleep(0.15)
        assert state.allow_request() is True
        assert state.state == CircuitState.HALF_OPEN

        state.record_success()
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0

    def test_half_open_failure_reopens(self):
        """half_open 中再次失败则重新 open"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=0.1)
        state = _CircuitState(config)

        for _ in range(3):
            state.record_failure("error")

        time.sleep(0.15)
        state.allow_request()  # 触发 half_open

        state.record_failure("error")
        assert state.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """成功调用清空失败计数"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        state = _CircuitState(config)

        state.record_failure("error")
        state.record_failure("error")
        assert state.failure_count == 2

        state.record_success()
        assert state.failure_count == 0
        assert state.state == CircuitState.CLOSED


class TestLLMCircuitBreaker:
    """测试 LLMCircuitBreaker 按 key 隔离"""

    def test_different_keys_independent(self):
        """不同 model key 互不影响"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        breaker = LLMCircuitBreaker(config)

        key_a = "openai|https://api.openai.com|gpt-4"
        key_b = "ollama|http://localhost:11434|llama3"

        # key_a 连续失败 3 次
        for _ in range(3):
            breaker.record_failure(key_a, "timeout")

        # key_a 被 open
        assert breaker.get_state(key_a) == CircuitState.OPEN
        assert breaker.allow_request(key_a) is False

        # key_b 不受影响
        assert breaker.get_state(key_b) == CircuitState.CLOSED
        assert breaker.allow_request(key_b) is True

    def test_disabled_breaker_allows_all(self):
        """breaker disabled 时不拦截请求"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_seconds=60,
            enabled=False,
        )
        breaker = LLMCircuitBreaker(config)

        key = "openai|https://api.openai.com|gpt-4"

        # 即使记录失败
        for _ in range(10):
            breaker.record_failure(key, "timeout")

        # 仍然允许请求
        assert breaker.allow_request(key) is True

    def test_make_key(self):
        """key 生成"""
        key = LLMCircuitBreaker.make_key("openai", "https://api.openai.com", "gpt-4")
        assert key == "openai|https://api.openai.com|gpt-4"

    def test_reset_specific_key(self):
        """重置指定 key"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        breaker = LLMCircuitBreaker(config)

        key_a = "openai|https://api.openai.com|gpt-4"
        key_b = "ollama|http://localhost:11434|llama3"

        for _ in range(3):
            breaker.record_failure(key_a, "timeout")
            breaker.record_failure(key_b, "timeout")

        assert breaker.get_state(key_a) == CircuitState.OPEN
        assert breaker.get_state(key_b) == CircuitState.OPEN

        breaker.reset(key_a)
        assert breaker.get_state(key_a) == CircuitState.CLOSED
        assert breaker.get_state(key_b) == CircuitState.OPEN

    def test_reset_all_keys(self):
        """重置所有 key"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        breaker = LLMCircuitBreaker(config)

        key_a = "openai|https://api.openai.com|gpt-4"
        key_b = "ollama|http://localhost:11434|llama3"

        for _ in range(3):
            breaker.record_failure(key_a, "timeout")
            breaker.record_failure(key_b, "timeout")

        breaker.reset()
        assert breaker.get_state(key_a) == CircuitState.CLOSED
        assert breaker.get_state(key_b) == CircuitState.CLOSED

    def test_get_all_states(self):
        """获取所有状态"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        breaker = LLMCircuitBreaker(config)

        key = "openai|https://api.openai.com|gpt-4"
        breaker.record_failure(key, "timeout")

        states = breaker.get_all_states()
        assert key in states
        assert states[key]["state"] == "closed"
        assert states[key]["failure_count"] == 1

    def test_remaining_timeout(self):
        """剩余超时时间"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        breaker = LLMCircuitBreaker(config)

        key = "openai|https://api.openai.com|gpt-4"
        for _ in range(3):
            breaker.record_failure(key, "timeout")

        remaining = breaker.get_remaining_timeout(key)
        assert 55 < remaining <= 60

    def test_remaining_timeout_when_closed(self):
        """closed 状态下剩余超时为 0"""
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_seconds=60)
        breaker = LLMCircuitBreaker(config)

        key = "openai|https://api.openai.com|gpt-4"
        assert breaker.get_remaining_timeout(key) == 0


class TestGlobalCircuitBreaker:
    """测试全局熔断器实例"""

    def test_init_circuit_breaker(self):
        """初始化全局熔断器"""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout_seconds=30,
            enabled=True,
        )
        breaker = init_circuit_breaker(config)
        assert breaker.config.failure_threshold == 5
        assert breaker.config.reset_timeout_seconds == 30

    def test_get_circuit_breaker_returns_instance(self):
        """获取全局实例"""
        breaker = get_circuit_breaker()
        assert breaker is not None
        assert isinstance(breaker, LLMCircuitBreaker)


class TestLLMServiceIntegration:
    """测试 LLMService 与熔断器集成"""

    @pytest.mark.asyncio
    async def test_circuit_open_prevents_llm_call(self):
        """连续失败后第四次请求不调用模型"""
        from backend.core.llm import LLMConfig, LLMService

        # 初始化熔断器（threshold=3, timeout 很短方便测试）
        config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_seconds=60,
            enabled=True,
        )
        breaker = init_circuit_breaker(config)

        llm_config = LLMConfig(
            provider="openai",
            api_key="test-key",
            api_base="https://api.openai.com",
            model="gpt-4",
        )
        service = LLMService(llm_config)

        # 模拟 LLM 调用失败 3 次
        key = LLMCircuitBreaker.make_key("openai", "https://api.openai.com", "gpt-4")
        for _ in range(3):
            breaker.record_failure(key, "APIError")

        # 第四次应该直接抛出 LLMCircuitOpenError
        with pytest.raises(LLMCircuitOpenError) as exc_info:
            async for _ in service.complete([{"role": "user", "content": "test"}]):
                pass

        assert exc_info.value.code == "LLM_CIRCUIT_OPEN"
        assert "熔断" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_circuit_open_error_details(self):
        """LLMCircuitOpenError 包含模型和剩余时间"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_seconds=60,
            enabled=True,
        )
        breaker = init_circuit_breaker(config)

        key = LLMCircuitBreaker.make_key("openai", "https://api.openai.com", "gpt-4")
        for _ in range(3):
            breaker.record_failure(key, "APIError")

        err = LLMCircuitOpenError(model="gpt-4", remaining_timeout=55)
        assert err.code == "LLM_CIRCUIT_OPEN"
        assert err.details["model"] == "gpt-4"
        assert err.details["remaining_timeout"] == 55
