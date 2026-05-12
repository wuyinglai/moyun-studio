/**
 * useChat - 聊天 composable
 * 提供聊天消息发送、流式接收逻辑
 */
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useProjectStore } from '@/stores/project'
import api from '@/services/api'

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
      chatStore.addMessage({
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: Date.now(),
      })

      const response = await api.post<{ reply: string }>('/chat', {
        project_id: projectStore.currentProject.id,
        message: content,
      })

      chatStore.addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        content: response?.reply || '',
        timestamp: Date.now(),
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
        timestamp: Date.now(),
      })

      await api.post('/chat/stream', {
        project_id: projectStore.currentProject?.id,
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
