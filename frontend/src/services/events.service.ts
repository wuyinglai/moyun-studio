/**
 * SSE 事件服务 - 管理 EventSource 连接
 * 注意：这是对 useSSE composable 的服务层封装，
 * 实际的 SSE 连接逻辑在 composables/useSSE.ts 中
 */
import type { SSEEventType } from '@/types/chat'

export const eventsService = {
  /** SSE 连接地址 */
  getSSEUrl() {
    return '/api/sse'
  },

  /** 解析 SSE 事件数据 */
  parseEvent<T = unknown>(event: MessageEvent): { type: SSEEventType; data: T } {
    return JSON.parse(event.data) as { type: SSEEventType; data: T }
  },
}
