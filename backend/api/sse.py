"""墨韵 - SSE 事件流 API

提供 Server-Sent Events 实时推送功能，与EventBus集成
"""

import asyncio
from collections.abc import AsyncGenerator
import json
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sse"])

MAX_SSE_CONNECTIONS = 100


class SSEManager:
    """SSE 连接管理器，集成EventBus"""

    # EventBus → 前端事件名映射
    # 注意：generation/done/error 事件不再通过 EventBus 广播
    # 它们通过 streaming 响应直接返回，避免重复
    _EVENT_MAP = {
        "file:created": "file-created",
        "file:modified": "file-updated",
        "file:deleted": "file-deleted",
        "task:started": "task",
        "task:progress": "task",
        "task:completed": "task",
        "task:failed": "error",
        "project:created": "file-created",
        "project:updated": "file-updated",
        "thinking": "thinking",
        "step_done": "step_done",
        "prompt": "prompt",
    }

    @staticmethod
    def _map_event_type(bus_event: str) -> str:
        return SSEManager._EVENT_MAP.get(bus_event, bus_event)

    def __init__(self):
        self.connections: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        """订阅 SSE 事件流"""
        if len(self.connections) >= MAX_SSE_CONNECTIONS:
            raise RuntimeError("SSE连接数已达上限")
        queue = asyncio.Queue(maxsize=200)
        self.connections.add(queue)
        logger.info(f"新的 SSE 连接已建立 (当前: {len(self.connections)})")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        if queue in self.connections:
            self.connections.discard(queue)
            logger.info(f"SSE 连接已断开 (当前: {len(self.connections)})")

    async def broadcast(self, event_type: str, data: dict):
        """广播事件到所有连接（自动映射 EventBus 事件名到前端格式）"""
        frontend_type = self._map_event_type(event_type)
        message = f"event: {frontend_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        dead_queues = []
        for queue in list(self.connections):
            try:
                await asyncio.wait_for(queue.put(message), timeout=2.0)
            except asyncio.TimeoutError:
                dead_queues.append(queue)
            except Exception:
                dead_queues.append(queue)
        for q in dead_queues:
            self.unsubscribe(q)


# 全局 SSE 管理器
sse_manager = SSEManager()


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    """SSE 事件生成器"""
    queue = await sse_manager.subscribe()

    # 发送初始连接事件
    yield f"event: connected\ndata: {json.dumps({'timestamp': time.time(), 'connections': len(sse_manager.connections)})}\n\n"

    try:
        while True:
            if await request.is_disconnected():
                logger.info("客户端已断开连接")
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                yield message
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        logger.info("SSE 连接被取消")
    finally:
        sse_manager.unsubscribe(queue)


@router.get("/sse")
async def sse_endpoint(request: Request):
    """SSE 事件流端点"""
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
