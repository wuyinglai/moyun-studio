<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { marked } from 'marked'

const chatStore = useChatStore()
const llmStore = useLLMStore()
const notification = useNotificationStore()

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

// 格式化时间
function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 简单的 Markdown 渲染
function renderMarkdown(text: string): string {
  if (!text) return ''
  try {
    return marked.parse(text) as string
  } catch {
    return text
  }
}

// 编辑器应直接调用 chatStore.continueWriting(projectId, filePath)
// 不再使用 window 事件通信

onMounted(() => {
  // 初始化
})

onBeforeUnmount(() => {
  // 清理
})
</script>
