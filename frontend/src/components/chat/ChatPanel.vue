<template>
  <div class="chat-panel">
    <!-- 未打开项目: 空状态 -->
    <div
      v-if="!projectStore.currentProject"
      class="chat-empty"
    >
      <div class="empty-icon">
        <svg
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <span class="empty-text">未打开项目</span>
      <span class="empty-hint">打开一个项目后即可开始 AI 对话</span>
    </div>
    <template v-else>
      <div
        ref="messagesContainer"
        class="chat-messages"
      >
        <ChatMessages
          :messages="messages"
          :is-thinking="!!currentThinking"
          @send-suggestion="handleSuggestion"
        />
      </div>
      <div class="chat-input-area">
        <ChatInput
          v-model="inputText"
          :disabled="isStreaming"
          @send="sendMessage"
        />
        <div class="chat-actions">
          <button
            v-if="isStreaming"
            class="btn-cancel"
            @click="cancelStream"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <rect
                x="6"
                y="6"
                width="12"
                height="12"
                rx="2"
              />
            </svg>
            取消生成
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useGenerationStore } from '@/stores/generation'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { getPipelineForFile } from '@/utils/promptTypes'
import ChatMessages from './ChatMessages.vue'
import ChatInput from './ChatInput.vue'

const chatStore = useChatStore()
const generationStore = useGenerationStore()
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
  // T4.1.3: 根据建议内容进行 intent 分流
  if (text.includes('续写') || text.includes('帮我续写')) {
    // 触发生成事件（调用 generationStore）
    window.dispatchEvent(new Event('chat:request-generate'))
  } else if (text.includes('润色') || text.includes('重写') || text.includes('帮我润色')) {
    // 触发重写事件（调用 generationStore）
    window.dispatchEvent(new Event('chat:request-rewrite'))
  } else {
    // 普通聊天
    inputText.value = text
    sendMessage()
  }
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
  // 管线映射文件走专用管线，不走 generate/continuation
  const pipelineName = getPipelineForFile(filePath)
  if (pipelineName && pipelineName !== 'title') {
    const fileGen = useFileGeneration()
    try {
      await fileGen.runPipeline(projectId, filePath, pipelineName, {}, 'write_scene')
    } catch {
      notification.error('AI 生成失败')
    }
    return
  }
  try {
    await generationStore.continueWriting(projectId, filePath)
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
    await generationStore.rewriteContent(projectId, filePath)
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

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 24px;
  text-align: center;
  color: var(--text-muted-ink);

  .empty-icon {
    opacity: 0.3;
    margin-bottom: 4px;
  }

  .empty-text {
    font-size: 14px;
    font-weight: 500;
  }

  .empty-hint {
    font-size: 12px;
    color: var(--text-faint);
    line-height: 1.5;
    max-width: 180px;
  }
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
