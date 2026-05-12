"""墨韵 - SSE 事件流 API

提供 Server-Sent Events 实时推送功能
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sse"])


class SSEManager:
    """SSE 连接管理器"""

    def __init__(self):
        self.connections: list[asyncio.Queue] = []

    async def subscribe(self) -> asyncio.Queue:
        """订阅 SSE 事件流"""
        queue = asyncio.Queue()
        self.connections.append(queue)
        logger.info("新的 SSE 连接已建立")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        if queue in self.connections:
            self.connections.remove(queue)
            logger.info("SSE 连接已断开")

    async def broadcast(self, event_type: str, data: dict):
        """广播事件到所有连接"""
        message = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        for queue in self.connections[:]:
            try:
                await queue.put(message)
            except Exception:
                self.connections.remove(queue)


# 全局 SSE 管理器
sse_manager = SSEManager()


async def event_generator() -> AsyncGenerator[str, None]:
    """SSE 事件生成器"""
    queue = await sse_manager.subscribe()

    # 发送初始连接事件
    yield f"event: connected\ndata: {json.dumps({'timestamp': __import__('time').time()})}\n\n"

    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                yield message
            except asyncio.TimeoutError:
                # 发送 keep-alive
                yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        logger.info("SSE 连接被取消")
    finally:
        sse_manager.unsubscribe(queue)


@router.get("/sse")
async def sse_endpoint():
    """SSE 事件流端点"""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
