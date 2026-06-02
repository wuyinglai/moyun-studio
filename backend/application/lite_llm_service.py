import asyncio
from collections.abc import AsyncGenerator

from backend.core.llm import LLMService


class LiteLLMService:
    """Service for handling Lite LLM calls with deadline and streaming support."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def complete_with_deadline(
        self,
        messages: list[dict],
        *,
        deadline: int,
        **kwargs,
    ) -> str:
        """Complete LLM request with a deadline timeout."""
        return (await asyncio.wait_for(
            self.llm_service.complete_sync(messages, **kwargs),
            timeout=deadline,
        )).strip()

    async def stream_llm_content(
        self,
        messages: list[dict],
        *,
        first_token_timeout: int = 90,
        token_timeout: int = 45,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM content with configurable timeouts."""
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def _produce() -> None:
            try:
                async for chunk in self.llm_service.complete(messages, stream=True, **kwargs):
                    await queue.put(chunk)
            finally:
                await queue.put(None)

        task = asyncio.create_task(_produce())
        has_chunk = False
        try:
            while True:
                timeout = token_timeout if has_chunk else first_token_timeout
                item = await asyncio.wait_for(queue.get(), timeout=timeout)
                if item is None:
                    break
                has_chunk = True
                yield item
        except Exception:
            task.cancel()
            raise
        finally:
            if not task.done():
                task.cancel()