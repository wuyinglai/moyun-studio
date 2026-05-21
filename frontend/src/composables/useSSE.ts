/**
 * SSE 事件系统 - 实时接收后端推送
 * 事件类型：
 * - generation: AI 生成内容（通过 generationEmitter 统一处理，不再通过 EventSource）
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
 * - sse.heartbeat: 心跳（不触发业务逻辑）
 */

import { ref, readonly } from 'vue'
import { generationEmitter } from './useFileGeneration'
import { useDiffSummary } from './useDiffSummary'
import { useEditorStore } from '@/stores/editor'
import { useFileStore } from '@/stores/file'
import { useProjectStore } from '@/stores/project'
import { useTaskStore } from '@/stores/task'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'
import type {
  SSEEventType,
  SSEEventData,
  GenerationEvent,
} from '@/types/sse'

export type { SSEEventType, SSEEventData, GenerationEvent }

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'

const MAX_RECONNECT_ATTEMPTS = 10
const INITIAL_RECONNECT_DELAY = 3000   // 3 秒首次重连
const MAX_RECONNECT_DELAY = 10000      // 最大 10 秒退避
const HEARTBEAT_TIMEOUT = 45000        // 45 秒无 heartbeat 视为断线（3 倍 heartbeat 间隔）

class SSEService {
  private eventSource: EventSource | null = null
  private reconnectAttempts = 0
  private reconnectDelay = INITIAL_RECONNECT_DELAY
  private isConnecting = false
  private manualClose = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null

  // 状态
  private _isConnected = ref(false)
  private _isReconnecting = ref(false)
  private _lastError = ref<string | null>(null)
  private _connectionStatus = ref<ConnectionStatus>('disconnected')
  private _lastHeartbeatAt = ref<number | null>(null)

  // 事件监听器
  private listeners = new Map<SSEEventType, Set<(data: any) => void>>()

  // 只读状态
  public isConnected = readonly(this._isConnected)
  public isReconnecting = readonly(this._isReconnecting)
  public lastError = readonly(this._lastError)
  public connectionStatus = readonly(this._connectionStatus)
  public lastHeartbeatAt = readonly(this._lastHeartbeatAt)

  /**
   * 连接到 SSE
   */
  connect() {
    if (this.isConnecting || this.eventSource) {
      return
    }

    this.manualClose = false
    this.isConnecting = true
    this._connectionStatus.value = 'connecting'
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
        this._connectionStatus.value = 'connected'
        this.emit('connected', { timestamp: Date.now() })
        this._startHeartbeatWatchdog()
      }

      this.eventSource.onerror = () => {
        this._isConnected.value = false
        this.isConnecting = false
        this._lastError.value = 'SSE 连接错误'
        this._connectionStatus.value = 'error'
        this._stopHeartbeatWatchdog()

        // 自动重连
        if (!this.manualClose) {
          this.scheduleReconnect()
        }
      }

      // 监听 EventSource 事件（非 generation）
      this.setupEventListeners()

      // 订阅 generationEmitter - generation 事件统一通过 fetch+ReadableStream 处理
      this.setupGenerationEmitterListener()
    } catch (error) {
      this.isConnecting = false
      this._lastError.value = 'SSE 连接失败'
      this._connectionStatus.value = 'error'
      console.error('SSE 连接失败:', error)
    }
  }

  /**
   * 启动 heartbeat 看门狗
   * 超过 HEARTBEAT_TIMEOUT 无 heartbeat 或正常事件，标记为断线
   */
  private _startHeartbeatWatchdog() {
    this._stopHeartbeatWatchdog()
    this._lastHeartbeatAt.value = Date.now()

    const check = () => {
      const last = this._lastHeartbeatAt.value
      if (last && Date.now() - last > HEARTBEAT_TIMEOUT) {
        // 超时未收到 heartbeat，标记断线
        if (this._connectionStatus.value === 'connected') {
          this._connectionStatus.value = 'disconnected'
          this._isConnected.value = false
          console.warn('SSE heartbeat 超时，连接可能断开')
          // 触发重连
          if (!this.manualClose) {
            this.scheduleReconnect()
          }
        }
      }
    }

    // 每 5 秒检查一次
    this.heartbeatTimer = setInterval(check, 5000)
  }

  private _stopHeartbeatWatchdog() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 记录收到事件（更新 heartbeat 时间戳）
   */
  private _touchHeartbeat() {
    this._lastHeartbeatAt.value = Date.now()
    if (this._connectionStatus.value !== 'connected') {
      this._connectionStatus.value = 'connected'
      this._isConnected.value = true
    }
  }

  /**
   * 订阅 generationEmitter - 处理来自 useFileGeneration 的 generation 事件
   * 这样 generation 事件只通过一条通路（fetch+ReadableStream → generationEmitter → handleEvent）
   */
  private setupGenerationEmitterListener() {
    const handler = (event: CustomEvent) => {
      // generationEmitter 发出的事件格式: { delta, task_id, ... }
      // 通过 handleEvent 统一处理，但标记为 'generation' 类型
      this.handleEvent('generation', event.detail)
    }
    generationEmitter.addEventListener('generation', handler as EventListener)
    // 存储 handler 以便后续移除
    ;(this as any)._generationHandler = handler

    // 监听 fetch stream 中的非 generation 事件，确保候选稿和完成状态能驱动 UI。
    const streamEventTypes = ['step_done', 'candidate_created', 'candidate-created', 'diff_summary', 'done', 'error']
    const streamHandler = (event: CustomEvent) => {
      const rawType = event.type
      const normalized = rawType === 'candidate_created' ? 'candidate-created' : rawType
      this.handleEvent(normalized as SSEEventType, event.detail)
      this.emit(normalized as SSEEventType, event.detail)
    }
    streamEventTypes.forEach((type) => {
      generationEmitter.addEventListener(type, streamHandler as EventListener)
    })
    ;(this as any)._streamHandler = streamHandler
    ;(this as any)._streamEventTypes = streamEventTypes
  }

  /**
   * 设置 EventSource 事件监听
   * 注意：generation 事件不再通过 EventSource 接收，统一由 generationEmitter 处理
   */
  private setupEventListeners() {
    if (!this.eventSource) return

    const eventTypes: SSEEventType[] = [
      'file-created',
      'file-updated',
      'file-renamed',
      'file-deleted',
      'directory-created',
      'task',
      'queue',
      'llm-status',
      'thinking',
      'error',
      'done',
      'diff_summary',
      'candidate-created',
      'candidate-adopted',
      'pipeline-started',
      'pipeline-step-started',
      'pipeline-step-completed',
      'pipeline-step-failed',
      'task-waiting-for-user',
      'task-completed',
      'memory-updated',
      'sse.heartbeat',
    ]

    eventTypes.forEach((type) => {
      this.eventSource!.addEventListener(type, (event: MessageEvent) => {
        if (!event.data) {
          return
        }
        try {
          const data = JSON.parse(event.data)

          // heartbeat 特殊处理：只更新状态，不触发业务逻辑
          if (type === 'sse.heartbeat') {
            this._touchHeartbeat()
            return
          }

          // 其他事件也更新 heartbeat 时间戳
          this._touchHeartbeat()

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
   * 按 project_id 过滤：只处理当前项目的事件
   */
  private async handleEvent(type: SSEEventType, data: any) {
    const editorStore = useEditorStore()
    const fileStore = useFileStore()
    const taskStore = useTaskStore()
    const llmStore = useLLMStore()
    const notification = useNotificationStore()
    const chatStore = useChatStore()
    const projectStore = useProjectStore()

    // heartbeat 不走业务逻辑
    if (type === 'sse.heartbeat') {
      return
    }

    // 按 project_id 过滤：只处理当前项目的事件
    const currentProjectId = projectStore.currentProject?.id
    if (data.project_id && currentProjectId && data.project_id !== currentProjectId) {
      return
    }

    switch (type) {
      case 'generation':
        // AI 生成内容 - 更新编辑器和聊天
        if (data.delta) {
          chatStore.appendAIMessage(data.delta)
          if (data._candidateOnly) {
            break
          } else if (data._targetFilePath) {
            editorStore.appendContentToFile(data._targetFilePath, data.delta)
          } else {
            editorStore.appendContent(data.delta)
          }
        } else if (data.content) {
          if (data._candidateOnly) {
            chatStore.appendAIMessage(data.content)
            break
          } else if (data._targetFilePath) {
            editorStore.appendContentToFile(data._targetFilePath, data.content)
          } else {
            editorStore.appendContent(data.content)
          }
          chatStore.appendAIMessage(data.content)
        }
        break

      case 'file-created':
      case 'candidate-created':
        // 新文件创建 - 刷新文件树
      {
        const path = data.path || data.candidate_path || data.source_path
        if (path) {
          fileStore.handleFileCreated(path, data.name)
          if (!path.startsWith('backup/snapshots/')) {
            taskStore.addLog('success', `已创建文件: ${data.name || path}`)
            notification.success(type === 'candidate-created' ? '候选稿已生成' : `已创建文件: ${data.name || path}`)
          }
        }
      }
        break

      case 'file-updated':
      case 'candidate-adopted':
      case 'memory-updated':
        // 文件更新 - 更新编辑器内容（不包含完整正文 content）
        if (data.path) {
          const projectId = currentProjectId
          const cleanPath = projectId && data.path.startsWith(projectId + '/')
            ? data.path.slice(projectId.length + 1)
            : data.path
          // file.updated 事件不发送完整正文，前端需要时再 read_file
          // 只在有 content 时更新编辑器
          if (data.content) {
            editorStore.updateContent(cleanPath, data.content)
          }
          taskStore.addLog('info', `文件已更新: ${cleanPath}`)
        }
        break

      case 'file-renamed':
        // 文件重命名 - 本地更新文件树
        if (data.oldPath && data.newPath) {
          fileStore.handleFileRenamed(data.oldPath, data.newPath)
          taskStore.addLog('info', `文件重命名: ${data.oldPath} → ${data.newPath}`)
        }
        break

      case 'file-deleted':
        // 文件删除
        if (data.path) {
          taskStore.addLog('info', `文件已删除: ${data.path}`)
        }
        break

      case 'directory-created':
        // 目录创建 - 刷新文件树
        if (data.path) {
          fileStore.handleDirectoryCreated(data.path, data.name)
          taskStore.addLog('success', `已创建目录: ${data.name || data.path}`)
        }
        break

      case 'task':
      case 'pipeline-started':
      case 'pipeline-step-started':
      case 'pipeline-step-completed':
      case 'task-completed':
      case 'task-waiting-for-user':
        // 任务状态变化（兼容旧 taskId 和新 task_id）
      {
        const taskId = data.task_id || data.taskId
        if (taskId) {
          taskStore.updateTask(taskId, data)
          llmStore.setGenerating(data.status === 'running')

          if (data.status === 'running') {
            taskStore.addLog('info', `任务开始: ${data.name || taskId}`)
            chatStore.startAIMessage(taskId)
          } else if (data.status === 'done' || data.status === 'completed') {
            taskStore.addLog('success', `任务完成: ${data.name || taskId}`)
          } else if (data.status === 'failed') {
            taskStore.addLog('error', `任务失败: ${data.name || taskId}`)
          } else if (data.status === 'waiting' || type === 'task-waiting-for-user') {
            taskStore.addLog('info', `任务等待用户确认: ${data.name || taskId}`)
          }
        }
        break
      }

      case 'pipeline-step-failed':
        // 管线步骤失败
        if (data.error) {
          taskStore.addLog('error', data.error)
          notification.error(data.error)
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
          if (data.connected) {
            taskStore.addLog('success', 'LLM 连接已建立')
          } else {
            taskStore.addLog('warning', 'LLM 连接断开')
          }
        }
        break

      case 'thinking':
        // AI 思考中 — 更新当前步骤进度
        llmStore.setThinking(data.thinking ?? true)
        if (data.label) {
          llmStore.currentStepLabel = data.label
        }
        if (data.content) {
          chatStore.updateThinking(data.content)
        }
        break

      case 'error':
        // 错误
        if (data.message) {
          taskStore.addLog('error', data.message)
          notification.error(data.message)
        }
        break

      case 'diff_summary':
        // AI 修改摘要
        if (data.summary) {
          const ds = useDiffSummary()
          ds.setSummary(data.summary, data.target_file || '')
          taskStore.addLog('info', 'AI 修改摘要已生成')
          notification.info('AI 修改摘要已生成，可查看修改分析')
        }
        break

      case 'done':
        // 任务完成
        chatStore.finishAIMessage()
        llmStore.setGenerating(false)
        llmStore.setThinking(false)
        llmStore.currentStepLabel = ''
        if (data.message) {
          taskStore.addLog('success', data.message)
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
        this._connectionStatus.value = 'error'
      }
      return
    }

    this._isReconnecting.value = true
    this._connectionStatus.value = 'reconnecting'
    this.reconnectAttempts++

    console.log(`${this.reconnectDelay}ms 后尝试第 ${this.reconnectAttempts} 次重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.disconnect()
      this.connect()
    }, this.reconnectDelay)

    // 指数退避，上限 10 秒
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY)
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.manualClose = true
    this._stopHeartbeatWatchdog()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    // 移除 generationEmitter 监听器
    const handler = (this as any)._generationHandler
    if (handler) {
      generationEmitter.removeEventListener('generation', handler as EventListener)
      delete (this as any)._generationHandler
    }
    const streamHandler = (this as any)._streamHandler
    const streamEventTypes = (this as any)._streamEventTypes || []
    if (streamHandler) {
      streamEventTypes.forEach((type: string) => {
        generationEmitter.removeEventListener(type, streamHandler as EventListener)
      })
      delete (this as any)._streamHandler
      delete (this as any)._streamEventTypes
    }
    this._isConnected.value = false
    this._isReconnecting.value = false
    this._connectionStatus.value = 'disconnected'
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
    connectionStatus: sseService.connectionStatus,
    lastHeartbeatAt: sseService.lastHeartbeatAt,
    connect: () => sseService.connect(),
    disconnect: () => sseService.disconnect(),
    on: (type: SSEEventType, callback: (data: any) => void) => sseService.on(type, callback),
  }
}
