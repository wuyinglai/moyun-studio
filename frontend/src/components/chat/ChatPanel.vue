<template>
  <div class="chat-panel">
    <div class="chat-messages" ref="messagesContainer">
      <ChatMessages :messages="messages" :is-thinking="!!currentThinking" @send-suggestion="handleSuggestion" />
    </div>
    <div class="chat-input-area">
      <ChatInput v-model="inputText" @send="sendMessage" :disabled="isStreaming" />
      <div class="chat-actions">
        <button v-if="isStreaming" class="btn-cancel" @click="cancelStream">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2"/>
          </svg>
          取消生成
        </button>
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

watch(
  () => messages.value.length,
  async () => { await nextTick(); scrollToBottom() }
)

watch(isStreaming, async () => {
  await nextTick(); scrollToBottom()
})

function handleSuggestion(text: string) {
  inputText.value = text
  sendMessage()
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return

  if (!llmStore.isConnected) {
    notification.warning('请先连接 LLM')
    return
  }

  inputText.value = ''
  try {
    await chatStore.sendMessage(
      text,
      projectStore.currentProject?.id,
      fileStore.currentFile?.path,
    )
  } catch {
    notification.error('发送消息失败')
  }
}

function cancelStream() {
  chatStore.cancelStream()
}

async function handleAIContinue() {
  const projectId = projectStore.currentProject?.id
  const filePath = fileStore.currentFile?.path
  if (!projectId || !filePath) {
    notification.warning('请先打开项目和文件')
    return
  }
  try {
    await chatStore.continueWriting(projectId, filePath)
  } catch {
    notification.error('AI 续写失败')
  }
}

async function handleAIRewrite() {
  const projectId = projectStore.currentProject?.id
  const filePath = fileStore.currentFile?.path
  if (!projectId || !filePath) {
    notification.warning('请先打开项目和文件')
    return
  }
  try {
    await chatStore.rewriteContent(projectId, filePath)
  } catch {
    notification.error('AI 重写失败')
  }
}

onMounted(() => {
  window.addEventListener('chat:request-generate', handleAIContinue)
  window.addEventListener('chat:request-rewrite', handleAIRewrite)
})

onBeforeUnmount(() => {
  window.removeEventListener('chat:request-generate', handleAIContinue)
  window.removeEventListener('chat:request-rewrite', handleAIRewrite)
})
</script>

<style scoped lang="scss">
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--ink-deep);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

.chat-input-area {
  border-top: 1px solid var(--border-ink);
  padding: 12px 16px;
  background: var(--ink-dark);
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.btn-cancel {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(192, 57, 43, 0.12);
  color: var(--vermillion-light);
  border: 1px solid rgba(192, 57, 43, 0.2);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all var(--transition-fast);

  &:hover {
    background: rgba(192, 57, 43, 0.2);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }

  svg {
    flex-shrink: 0;
  }
}
</style>
