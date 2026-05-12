/**
 * SSE 事件系统 - 实时接收后端推送
 * 事件类型：
 * - generation: AI 生成内容
 * - file-created: 新文件创建
 * - file-updated: 文件更新
 * - file-renamed: 文件被重命名
 * - directory-created: 目录被创建
 * - task: 任务状态变化
 * - queue: 队列变化
 * - llm-status: LLM 状态变化
 * - thinking: AI 思考中
 * - error: 错误
 * - done: 任务完成
 */

import { ref, readonly } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useFileStore } from '@/stores/file'
import { useTaskStore } from '@/stores/task'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'

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

export interface SSEEvent {
  type: SSEEventType
  data: any
}

export interface GenerationEvent {
  content: string
  taskId: string
}

export interface FileEvent {
  path: string
  name?: string
}

export interface TaskEvent {
  taskId: string
  status: 'pending' | 'running' | 'done' | 'failed'
  name?: string
  progress?: number
}

export interface LLMStatusEvent {
  connected: boolean
  model?: string
}

export interface ErrorEvent {
  code: string
  message: string
}

const MAX_RECONNECT_ATTEMPTS = 10
const INITIAL_RECONNECT_DELAY = 1000

class SSEService {
  private eventSource: EventSource | null = null
  private reconnectAttempts = 0
  private reconnectDelay = INITIAL_RECONNECT_DELAY
  private isConnecting = false
  private manualClose = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 状态
  private _isConnected = ref(false)
  private _isReconnecting = ref(false)
  private _lastError = ref<string | null>(null)

  // 事件监听器
  private listeners = new Map<SSEEventType, Set<(data: any) => void>>()

  // 只读状态
  public isConnected = readonly(this._isConnected)
  public isReconnecting = readonly(this._isReconnecting)
  public lastError = readonly(this._lastError)

  /**
   * 连接到 SSE
   */
  connect() {
    if (this.isConnecting || this.eventSource) {
      return
    }

    this.manualClose = false
    this.isConnecting = true
    this._lastError.value = null

    try {
      const url = '/api/sse'
      this.eventSource = new EventSource(url)

      this.eventSource.onopen = () => {
        this._isConnected.value = true
        this._isReconnecting.value = false
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.reconnectDelay = INITIAL_RECONNECT_DELAY
        this.emit('connected', { timestamp: Date.now() })
      }

      this.eventSource.onerror = () => {
        this._isConnected.value = false
        this.isConnecting = false
        this._lastError.value = 'SSE 连接错误'

        // 自动重连
        if (!this.manualClose) {
          this.scheduleReconnect()
        }
      }

      // 监听各类型事件
      this.setupEventListeners()
    } catch (error) {
      this.isConnecting = false
      this._lastError.value = 'SSE 连接失败'
      console.error('SSE 连接失败:', error)
    }
  }

  /**
   * 设置 EventSource 事件监听
   */
  private setupEventListeners() {
    if (!this.eventSource) return

    const eventTypes: SSEEventType[] = [
      'generation',
      'file-created',
      'file-updated',
      'file-renamed',
      'directory-created',
      'task',
      'queue',
      'llm-status',
      'thinking',
      'error',
      'done',
    ]

    eventTypes.forEach((type) => {
      this.eventSource!.addEventListener(type, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          this.handleEvent(type, data)
          this.emit(type, data)
        } catch (e) {
          console.error(`解析 ${type} 事件失败:`, e)
        }
      })
    })
  }

  /**
   * 处理各类事件
   */
  private handleEvent(type: SSEEventType, data: any) {
    const editorStore = useEditorStore()
    const fileStore = useFileStore()
    const taskStore = useTaskStore()
    const llmStore = useLLMStore()
    const notification = useNotificationStore()
    const chatStore = useChatStore()

    switch (type) {
      case 'generation':
        // AI 生成内容 - 更新编辑器和聊天
        // 后端发送格式: { delta: "...", content?: "..." }
        if (data.delta) {
          chatStore.appendAIMessage(data.delta)
        } else if (data.content) {
          editorStore.appendContent(data.content)
          chatStore.appendAIMessage(data.content)
        }
        break

      case 'file-created':
        // 新文件创建 - 刷新文件树
        if (data.path) {
          fileStore.handleFileCreated(data.path, data.name)
          notification.success(`已创建文件: ${data.name || data.path}`)
        }
        break

      case 'file-updated':
        // 文件更新 - 更新编辑器内容
        if (data.path) {
          editorStore.updateContent(data.path, data.content)
        }
        break

      case 'file-renamed':
        // 文件重命名 - 本地更新文件树（不做 API 调用，避免二次重命名）
        if (data.oldPath && data.newPath) {
          fileStore.handleFileRenamed(data.oldPath, data.newPath)
        }
        break

      case 'directory-created':
        // 目录创建 - 刷新文件树
        if (data.path) {
          fileStore.handleDirectoryCreated(data.path, data.name)
        }
        break

      case 'task':
        // 任务状态变化
        if (data.taskId) {
          taskStore.updateTask(data.taskId, data)
          llmStore.setGenerating(data.status === 'running')

          // 开始新任务时，启动 AI 消息
          if (data.status === 'running' && data.taskId) {
            chatStore.startAIMessage(data.taskId)
          }
        }
        break

      case 'queue':
        // 队列变化
        if (data.queue) {
          taskStore.updateQueue(data.queue)
        }
        break

      case 'llm-status':
        // LLM 状态变化
        if (typeof data.connected === 'boolean') {
          llmStore.isConnected = data.connected
        }
        break

      case 'thinking':
        // AI 思考中
        llmStore.setThinking(data.thinking ?? true)
        if (data.content) {
          chatStore.updateThinking(data.content)
        }
        break

      case 'error':
        // 错误
        if (data.message) {
          notification.error(data.message)
        }
        break

      case 'done':
        // 任务完成
        chatStore.finishAIMessage()
        llmStore.setGenerating(false)
        llmStore.setThinking(false)
        if (data.message) {
          notification.success(data.message)
        }
        break
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect() {
    if (this.manualClose || this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        this._lastError.value = 'SSE 重连次数已达上限'
      }
      return
    }

    this._isReconnecting.value = true
    this.reconnectAttempts++

    console.log(`${this.reconnectDelay}ms 后尝试第 ${this.reconnectAttempts} 次重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.disconnect()
      this.connect()
    }, this.reconnectDelay)

    // 指数退避
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000)
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.manualClose = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    this._isConnected.value = false
    this._isReconnecting.value = false
  }

  /**
   * 订阅事件
   */
  on(type: SSEEventType, callback: (data: any) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    this.listeners.get(type)!.add(callback)

    // 返回取消订阅函数
    return () => {
      this.listeners.get(type)?.delete(callback)
    }
  }

  /**
   * 发送事件（内部使用）
   */
  private emit(type: SSEEventType, data: any) {
    const callbacks = this.listeners.get(type)
    if (callbacks) {
      callbacks.forEach((cb) => cb(data))
    }
  }

  /**
   * 移除所有监听器
   */
  removeAllListeners() {
    this.listeners.clear()
  }
}

// 导出单例
export const sseService = new SSEService()

// 导出 composable
export function useSSE() {
  return {
    isConnected: sseService.isConnected,
    isReconnecting: sseService.isReconnecting,
    lastError: sseService.lastError,
    connect: () => sseService.connect(),
    disconnect: () => sseService.disconnect(),
    on: (type: SSEEventType, callback: (data: any) => void) => sseService.on(type, callback),
  }
}
