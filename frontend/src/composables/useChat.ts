/**
 * useChat - 聊天 composable
 * 提供聊天消息发送、流式接收逻辑
 */
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useProjectStore } from '@/stores/project'
import api from '@/services/api'
import type { ChatMessage } from '@/types/chat'

export function useChat() {
  const chatStore = useChatStore()
  const projectStore = useProjectStore()
  const isSending = ref(false)

  /**
   * 发送消息（普通对话，非流式）
   */
  async function sendMessage(content: string): Promise<void> {
    if (!projectStore.currentProject) return
    isSending.value = true

    try {
      // 添加用户消息
      chatStore.addMessage({
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      })

      // 发送请求
      const response = await api.post<{ reply: string }>('/chat', {
        project_id: projectStore.currentProject.id,
        message: content,
      })

      // 添加 AI 回复
      chatStore.addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response?.reply || '',
        timestamp: new Date().toISOString(),
      })
    } finally {
      isSending.value = false
    }
  }

  /**
   * 发送消息（流式，通过 SSE 接收）
   */
  async function sendMessageStream(content: string): Promise<void> {
    if (!projectStore.currentProject) return
    isSending.value = true

    try {
      chatStore.addMessage({
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      })

      // SSE 流式请求（由 useSSE.ts 处理响应）
      await api.post('/chat/stream', {
        project_id: projectStore.currentProject.id,
        message: content,
      })
    } finally {
      isSending.value = false
    }
  }

  /**
   * 清空聊天记录
   */
  function clearMessages() {
    chatStore.clearMessages()
  }

  return {
    isSending,
    sendMessage,
    sendMessageStream,
    clearMessages,
  }
}
