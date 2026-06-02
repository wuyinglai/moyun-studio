import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.application.lite_llm_service import LiteLLMService


class TestLiteLLMService:
    """测试 LiteLLMService 类"""

    class TestCompleteWithDeadline:
        """测试 complete_with_deadline 方法"""

        @pytest.mark.anyio
        async def test_complete_with_deadline_returns_text(self):
            """返回 LLM 生成的文本"""
            mock_llm = MagicMock()
            mock_llm.complete_sync = AsyncMock(return_value="测试响应文本")
            
            service = LiteLLMService(mock_llm)
            result = await service.complete_with_deadline(
                [{"role": "user", "content": "测试 prompt"}],
                deadline=30,
                temperature=0.7,
                max_tokens=1000,
            )
            
            assert result == "测试响应文本"
            mock_llm.complete_sync.assert_called_once()

        @pytest.mark.anyio
        async def test_complete_with_deadline_timeout(self):
            """超时抛出异常"""
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(0.5)
                return "慢响应"
            
            mock_llm = MagicMock()
            mock_llm.complete_sync = slow_response
            
            service = LiteLLMService(mock_llm)
            
            with pytest.raises(asyncio.TimeoutError):
                await service.complete_with_deadline(
                    [{"role": "user", "content": "测试 prompt"}],
                    deadline=0.1,
                    temperature=0.7,
                    max_tokens=1000,
                )

    class TestStreamLLMContent:
        """测试 stream_llm_content 方法"""

        @pytest.mark.anyio
        async def test_stream_llm_content_yields_text_chunks(self):
            """yield 文本 chunk"""
            async def mock_stream(*args, **kwargs):
                for chunk in ["第", "一", "个", "字", "符"]:
                    yield chunk
            
            mock_llm = MagicMock()
            mock_llm.complete = mock_stream
            
            service = LiteLLMService(mock_llm)
            chunks = [chunk async for chunk in service.stream_llm_content(
                [{"role": "user", "content": "测试 prompt"}],
                first_token_timeout=5,
                token_timeout=5,
            )]
            
            assert "".join(chunks) == "第一个字符"

        @pytest.mark.anyio
        async def test_stream_llm_content_skips_empty_chunks(self):
            """空 chunk 不影响输出"""
            async def mock_stream_with_empty(*args, **kwargs):
                yield ""
                yield "有"
                yield ""
                yield "内"
                yield ""
                yield "容"
            
            mock_llm = MagicMock()
            mock_llm.complete = mock_stream_with_empty
            
            service = LiteLLMService(mock_llm)
            chunks = [chunk async for chunk in service.stream_llm_content(
                [{"role": "user", "content": "测试 prompt"}],
                first_token_timeout=5,
                token_timeout=5,
            )]
            
            assert "".join(chunks) == "有内容"

        @pytest.mark.anyio
        async def test_stream_llm_content_first_token_timeout(self):
            """首 token 超时"""
            async def slow_first_token(*args, **kwargs):
                await asyncio.sleep(0.5)
                yield "慢"
            
            mock_llm = MagicMock()
            mock_llm.complete = slow_first_token
            
            service = LiteLLMService(mock_llm)
            
            with pytest.raises(asyncio.TimeoutError):
                async for _ in service.stream_llm_content(
                    [{"role": "user", "content": "测试 prompt"}],
                    first_token_timeout=0.1,
                    token_timeout=5,
                ):
                    pass