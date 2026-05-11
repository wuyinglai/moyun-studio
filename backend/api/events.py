"""墨韵 - SSE 事件流 API

端点：
  GET /api/events   建立 SSE 连接，接收服务器推送事件
"""

import json
import asyncio

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["events"])


@router.get("/events")
async def sse_events(request: Request):
    """SSE 事件流端点"""

    async def _generator():
        event_bus = getattr(request.app.state, "event_bus", None)

        if event_bus is None:
            yield {"event": "error", "data": json.dumps({"message": "EventBus 未初始化"})}
            return

        # 使用 EventBus 的 subscribe 接口
        client_id, queue = event_bus.subscribe(event_types=None)  # 订阅所有事件

        # 先发心跳确认连接建立
        yield {"event": "connected", "data": json.dumps({"message": "SSE连接已建立"})}

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    # message 格式: {"type": event_type, "data": {...}}
                    event_type = message.get("type", "message")
                    data = message.get("data", {})

                    # 将 EventBus 事件类型映射到前端期望的格式
                    frontend_event = _map_event_type(event_type)
                    yield {
                        "event": frontend_event,
                        "data": json.dumps(data, ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    # 心跳保活
                    yield {"event": "heartbeat", "data": "{}"}

        finally:
            event_bus.unsubscribe(client_id, queue)

    return EventSourceResponse(_generator())


def _map_event_type(bus_event: str) -> str:
    """将 EventBus 事件类型映射到前端 SSE 事件名"""
    mapping = {
        "file:created": "file-created",
        "file:modified": "file-updated",
        "file:deleted": "file-deleted",
        "task:started": "task",
        "task:progress": "task",
        "task:completed": "task",
        "task:failed": "error",
        "project:created": "file-created",
        "project:updated": "file-updated",
        "generation": "generation",
        "done": "done",
        "error": "error",
        "llm-status": "llm-status",
        "thinking": "thinking",
    }
    return mapping.get(bus_event, bus_event)
