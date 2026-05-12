<template>
  <div class="chat-messages" ref="containerRef">
    <div v-if="messages.length === 0" class="messages-empty">
      <i class="fa-solid fa-comments"></i>
      <p>开始一段对话吧</p>
    </div>

    <TransitionGroup name="message" tag="div" class="messages-list">
      <ChatMessage
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
      />
    </TransitionGroup>

    <!-- Thinking 指示器 -->
    <div v-if="isThinking" class="thinking-indicator">
      <div class="thinking-dots">
        <span></span><span></span><span></span>
      </div>
      <span class="thinking-text">AI 正在思考...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import type { ChatMessage as ChatMessageType } from '@/types/chat'

defineProps<{
  messages: ChatMessageType[]
  isThinking?: boolean
}>()

const containerRef = ref<HTMLElement | null>(null)

/** 滚动到底部 */
function scrollToBottom(smooth = true) {
  nextTick(() => {
    if (containerRef.value) {
      containerRef.value.scrollTo({
        top: containerRef.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      })
    }
  })
}

// 新消息时自动滚动
watch(
  () => arguments[0]?.messages?.length,
  () => scrollToBottom()
)

defineExpose({ scrollToBottom })
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.messages-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
  opacity: 0.6;
}

.messages-empty i {
  font-size: 32px;
}

.messages-empty p {
  font-size: 13px;
}

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.thinking-dots {
  display: flex;
  gap: 4px;
}

.thinking-dots span {
  width: 6px;
  height: 6px;
  background: var(--accent-primary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 消息进入动画 */
.message-enter-active {
  transition: all 0.3s ease;
}
.message-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
</style>
