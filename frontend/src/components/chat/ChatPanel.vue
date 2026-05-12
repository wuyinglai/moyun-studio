<template>
  <div class="chat-panel">
    <div class="chat-messages" ref="messagesContainer">
      <ChatMessages :messages="messages" :is-thinking="!!currentThinking" />
    </div>
    <div class="chat-input-area">
      <ChatInput v-model="inputText" @send="sendMessage" :disabled="isStreaming" />
      <div class="chat-actions">
        <button v-if="isStreaming" class="btn-cancel" @click="cancelStream">取消生成</button>
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
  try {
    await chatStore.sendMessage(text)
  } catch {
    notification.error('发送消息失败')
  }
}

// 取消生成
function cancelStream() {
  chatStore.cancelStream()
}

// 监听编辑器发起的 AI 续写请求
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

// 监听编辑器发起的 AI 重写请求
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
  background: var(--bg-primary);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chat-input-area {
  border-top: 1px solid var(--border-color);
  padding: 16px;
  background: var(--bg-card);
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.btn-cancel {
  padding: 8px 16px;
  background: var(--accent-error);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;

  &:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
}

.btn-clear {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
    border-color: var(--accent-primary);
  }
}
</style>
