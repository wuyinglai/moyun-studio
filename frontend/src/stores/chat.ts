import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useLLMStore } from './llm'
import { useTaskStore } from './task'

/**
 * 解析 SSE 响应流，逐行提取 data: JSON 中的 delta 内容
 * 注意：/api/generate 的 generation 事件已由 useSSE 通过 generationEmitter 统一处理，
 * 此函数仅用于 /api/chat 的聊天消息流
 */
async function parseSSEStreamForChat(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onDelta: (delta: string) => void,
): Promise<void> {
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // 保留未完成行

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        try {
          const parsed = JSON.parse(line.slice(6))
          if (currentEvent === 'error') {
            throw new Error(parsed.message || '聊天出错')
          }
          if (parsed.delta) {
            onDelta(parsed.delta)
          } else if (parsed.content) {
            onDelta(parsed.content)
          }
        } catch {
          // 跳过非 JSON 行
        }
      }
    }
  }
}

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
   * 发送聊天消息（走 chat 管线）
   * 注意：generation 事件由 useSSE 通过 generationEmitter 统一处理
   */
  async function sendMessage(content: string, projectId?: string, contextFile?: string) {
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
        body: JSON.stringify({
          message: content,
          project_id: projectId || '',
          context_file: contextFile || null,
        }),
        signal: streamController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      await parseSSEStreamForChat(reader, (delta) => {
        appendAIMessage(delta)
      })
      finishAIMessage()
    } catch (e) {
      finishAIMessage()
      throw e
    } finally {
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
    cancelStream,
    clearMessages,
    startAIMessage,
    appendAIMessage,
    finishAIMessage,
    updateThinking,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['messages'],
  },
})
