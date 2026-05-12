import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useLLMStore } from './llm'
import { useTaskStore } from './task'

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: number
  thinking?: string
}

export type GenerationMode = 'continue' | 'rewrite' | 'chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const currentThinking = ref('')
  const currentAIMessageId = ref<string | null>(null)
  const currentTaskId = ref<string | null>(null)
  const generationMode = ref<GenerationMode>('chat')
  let streamController: AbortController | null = null

  function addMessage(role: 'user' | 'ai', content: string) {
    messages.value.push({
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
      role,
      content,
      timestamp: Date.now(),
    })
  }

  /**
   * SSE 事件：开始 AI 消息流
   */
  function startAIMessage(taskId?: string) {
    const llmStore = useLLMStore()
    llmStore.setGenerating(true)
    isStreaming.value = true
    currentAIMessageId.value = `msg-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`
    currentTaskId.value = taskId || null
    messages.value.push({
      id: currentAIMessageId.value,
      role: 'ai',
      content: '',
      timestamp: Date.now(),
    })
  }

  /**
   * SSE 事件：追加 AI 消息内容
   */
  function appendAIMessage(content: string) {
    if (currentAIMessageId.value) {
      const msg = messages.value.find((m) => m.id === currentAIMessageId.value)
      if (msg) {
        msg.content += content
      }
    }
  }

  /**
   * SSE 事件：完成 AI 消息流
   */
  function finishAIMessage() {
    const llmStore = useLLMStore()
    llmStore.setGenerating(false)
    isStreaming.value = false
    currentThinking.value = ''
    currentAIMessageId.value = null
    currentTaskId.value = null
  }

  /**
   * SSE 事件：更新思考内容
   */
  function updateThinking(content: string) {
    currentThinking.value = content
    if (currentAIMessageId.value) {
      const msg = messages.value.find((m) => m.id === currentAIMessageId.value)
      if (msg) {
        msg.thinking = content
      }
    }
  }

  /**
   * 发送聊天消息
   */
  async function sendMessage(content: string) {
    const llmStore = useLLMStore()
    generationMode.value = 'chat'
    llmStore.setGenerating(true)
    isStreaming.value = true
    addMessage('user', content)

    streamController = new AbortController()
    startAIMessage()

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
        signal: streamController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        appendAIMessage(chunk)
      }
    } finally {
      finishAIMessage()
      streamController = null
    }
  }

  /**
   * 续写当前文件（写下一部分）
   */
  async function continueWriting(projectId: string, filePath: string, prompt?: string) {
    const taskStore = useTaskStore()
    generationMode.value = 'continue'

    // 添加任务
    const taskId = `task-${Date.now()}`
    taskStore.addTask(taskId, `续写: ${filePath.split('/').pop()}`)
    taskStore.startTask(taskId)

    streamController = new AbortController()
    startAIMessage(taskId)

    try {
      const response = await fetch('/api/generate/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, path: filePath, prompt }),
        signal: streamController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        appendAIMessage(chunk)
      }

      taskStore.completeTask(taskId)
    } catch (e) {
      taskStore.failTask(taskId)
      throw e
    } finally {
      finishAIMessage()
      streamController = null
    }
  }

  /**
   * 重写当前文件
   */
  async function rewriteContent(projectId: string, filePath: string, prompt?: string) {
    const taskStore = useTaskStore()
    generationMode.value = 'rewrite'

    const taskId = `task-${Date.now()}`
    taskStore.addTask(taskId, `重写: ${filePath.split('/').pop()}`)
    taskStore.startTask(taskId)

    streamController = new AbortController()
    startAIMessage(taskId)

    try {
      const response = await fetch('/api/generate/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, path: filePath, prompt }),
        signal: streamController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        appendAIMessage(chunk)
      }

      taskStore.completeTask(taskId)
    } catch (e) {
      taskStore.failTask(taskId)
      throw e
    } finally {
      finishAIMessage()
      streamController = null
    }
  }

  /**
   * 停止生成
   */
  function cancelStream() {
    streamController?.abort()
    if (currentTaskId.value) {
      const taskStore = useTaskStore()
      taskStore.cancelTask(currentTaskId.value)
    }
    finishAIMessage()
  }

  /**
   * 清空消息历史
   */
  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    isStreaming,
    currentThinking,
    generationMode,
    addMessage,
    sendMessage,
    continueWriting,
    rewriteContent,
    cancelStream,
    clearMessages,
    startAIMessage,
    appendAIMessage,
    finishAIMessage,
    updateThinking,
  }
})
