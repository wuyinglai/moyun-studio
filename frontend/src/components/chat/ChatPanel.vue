<template>
  <div class="chat-panel">
    <div class="chat-messages" ref="messagesContainer">
      <ChatMessages :messages="messages" :is-thinking="!!currentThinking" />
    </div>
    <div class="chat-input-area">
      <ChatInput v-model="inputText" @send="sendMessage" :disabled="isStreaming" />
      <div class="chat-actions">
        <button v-if="isStreaming" class="btn-cancel" @click="cancelStream">取消生成</button>
        <button class="btn-clear" @click="clearMessages">清空</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import ChatMessages from './ChatMessages.vue'
import ChatInput from './ChatInput.vue'

const chatStore = useChatStore()
const llmStore = useLLMStore()
const notification = useNotificationStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()

const messagesContainer = ref<HTMLElement | null>(null)
const inputText = ref('')

const messages = computed(() => chatStore.messages)
const isStreaming = computed(() => chatStore.isStreaming)
const currentThinking = computed(() => chatStore.currentThinking)

// 自动滚动到底部
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

watch(isStreaming, async () => {
  await nextTick()
  scrollToBottom()
})

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 发送消息
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return

  if (!llmStore.isConnected) {
    notification.warning('请先连接 LLM')
    return
  }

  inputText.value = ''
  await chatStore.sendMessage(text)
}

// 取消生成
function cancelStream() {
  chatStore.cancelStream()
}

// 清空消息
function clearMessages() {
  chatStore.clearMessages()
}

// 监听编辑器发起的 AI 生成请求
async function handleAIRequest() {
  const projectId = projectStore.currentProject?.id
  const filePath = fileStore.currentFile?.path
  if (!projectId || !filePath) {
    notification.warning('请先打开项目和文件')
    return
  }
  try {
    await chatStore.continueWriting(projectId, filePath)
  } catch {
    notification.error('AI 生成失败')
  }
}

onMounted(() => {
  window.addEventListener('chat:request-generate', handleAIRequest)
})

onBeforeUnmount(() => {
  window.removeEventListener('chat:request-generate', handleAIRequest)
})
</script>

<style scoped lang="scss">
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
}

.chat-input-area {
  border-top: 1px solid var(--border-color);
  padding: 12px;
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.btn-cancel {
  padding: 4px 12px;
  background: var(--accent-error);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.btn-clear {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
}
</style>
