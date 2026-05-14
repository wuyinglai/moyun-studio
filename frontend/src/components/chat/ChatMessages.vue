<template>
  <div class="chat-messages" ref="containerRef">
    <!-- 空状态 -->
    <div v-if="messages.length === 0" class="messages-empty">
      <div class="empty-icon">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      </div>
      <p class="empty-title">与 AI 对话</p>
      <p class="empty-hint">输入消息开始创作、润色或讨论情节</p>
      <div class="welcome-suggestions">
        <div class="suggestion-chip" @click="$emit('send-suggestion', '帮我续写当前章节')">
          <span class="chip-icon">✏️</span>
          <span>续写章节</span>
        </div>
        <div class="suggestion-chip" @click="$emit('send-suggestion', '帮我润色这段文字，让它更生动')">
          <span class="chip-icon">🪶</span>
          <span>润色文字</span>
        </div>
        <div class="suggestion-chip" @click="$emit('send-suggestion', '讨论一下后续情节发展')">
          <span class="chip-icon">💡</span>
          <span>讨论情节</span>
        </div>
      </div>
    </div>

    <!-- 消息列表 -->
    <TransitionGroup name="message" tag="div" class="messages-list">
      <ChatMessage
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
      />
    </TransitionGroup>

    <!-- Thinking 指示器 -->
    <div v-if="isThinking" class="thinking-indicator">
      <div class="thinking-ink">
        <span class="ink-ring"></span>
      </div>
      <span class="thinking-text">AI 正在构思...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import type { ChatMessage as ChatMessageType } from '@/types/chat'

const props = defineProps<{
  messages: ChatMessageType[]
  isThinking?: boolean
}>()

const emit = defineEmits<{
  (e: 'send-suggestion', text: string): void
}>()

const containerRef = ref<HTMLElement | null>(null)

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

watch(
  () => props.messages?.length,
  () => scrollToBottom(),
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
  gap: 8px;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ── 空状态 ── */
.messages-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted-ink);
  padding: 40px 24px;
}

.empty-icon {
  color: var(--text-faint);
  opacity: 0.3;
  margin-bottom: 4px;
}

.empty-title {
  font-size: 14px;
  color: var(--text-muted-ink);
  font-weight: 500;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-faint);
  text-align: center;
  max-width: 200px;
  line-height: 1.5;
}

.welcome-suggestions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
  width: 100%;
  max-width: 200px;
}

.suggestion-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--ink-mid);
  border: 1px solid var(--border-ink);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: 12px;
  color: var(--text-muted-ink);

  &:hover {
    background: var(--ink-hover);
    border-color: var(--gold-primary);
    color: var(--text-ink);
  }

  .chip-icon {
    font-size: 14px;
    flex-shrink: 0;
  }
}

/* ── Thinking 指示器 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  color: var(--text-muted-ink);
  font-size: 13px;
}

.thinking-ink {
  position: relative;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ink-ring {
  width: 12px;
  height: 12px;
  border: 2px solid var(--gold-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: ink-spin 0.8s linear infinite;
}

@keyframes ink-spin {
  to { transform: rotate(360deg); }
}

.thinking-text {
  font-style: italic;
  font-size: 12px;
}

/* ── 消息过渡动画 ── */
.message-enter-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.message-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
</style>
