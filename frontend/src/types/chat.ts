// 聊天相关类型

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  thinking?: string
  taskId?: string
}

export interface ChatSession {
  projectId: string
  messages: ChatMessage[]
  isStreaming: boolean
}

// SSE 事件类型（前端用）
export interface SSEEvent {
  type: SSEEventType
  data: unknown
}

export type SSEEventType =
  | 'generation'
  | 'file-created'
  | 'file-updated'
  | 'file-renamed'
  | 'directory-created'
  | 'task'
  | 'queue'
  | 'llm-status'
  | 'thinking'
  | 'error'
  | 'done'
  | 'connected'
