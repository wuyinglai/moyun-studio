<template>
  <div class="chat-message" :class="`role-${message.role}`">
    <!-- 头像 -->
    <div class="message-avatar">
      <i :class="avatarIcon"></i>
    </div>

    <div class="message-body">
      <!-- 角色名 -->
      <div class="message-meta">
        <span class="message-role">{{ roleLabel }}</span>
        <span class="message-time">{{ formatTime(message.timestamp) }}</span>
      </div>

      <!-- 内容 -->
      <div class="message-content">
        <template v-if="message.role === 'user'">
          {{ message.content }}
        </template>
        <template v-else>
          <div class="ai-content" v-html="renderedContent"></div>
        </template>
      </div>

      <!-- Thinking 内容 -->
      <div v-if="message.thinking" class="message-thinking">
        <span class="thinking-label">AI 思考过程：</span>
        <div class="thinking-content">{{ message.thinking }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types/chat'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  message: ChatMessage
}>()

const avatarIcon = computed(() => {
  return props.message.role === 'user'
    ? 'fa-solid fa-user'
    : 'fa-solid fa-robot'
})

const roleLabel = computed(() => {
  return props.message.role === 'user' ? '用户' : 'AI'
})

const renderedContent = computed(() => {
  return renderMarkdown(props.message.content)
})

function formatTime(timestamp: number): string {
  const d = new Date(timestamp)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped lang="scss">
.chat-message {
  display: flex;
  gap: 12px;
  max-width: 100%;
  padding: 12px 0;
  animation: messageSlideIn 0.3s ease;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.role-user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.role-user .message-avatar {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: white;
}

.role-ai .message-avatar {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.message-body {
  flex: 1;
  min-width: 0;
  max-width: 85%;
}

.role-user .message-body {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.role-user .message-meta {
  flex-direction: row-reverse;
}

.message-role {
  color: var(--text-muted);
  font-weight: 500;
}

.message-time {
  color: var(--text-muted);
  font-size: 11px;
  opacity: 0.7;
}

.message-content {
  padding: 14px 18px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.role-user .message-content {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: white;
  border-bottom-right-radius: 4px;
}

.role-ai .message-content {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}

.ai-content :deep(p:first-child) { margin-top: 0; }
.ai-content :deep(p:last-child) { margin-bottom: 0; }
.ai-content :deep(code) {
  background: rgba(107, 140, 255, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  color: var(--accent-primary);
}
.ai-content :deep(pre) {
  background: var(--bg-primary);
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid var(--border-color);
}
.ai-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: var(--text-primary);
}
.ai-content :deep(a) {
  color: var(--accent-primary);
  text-decoration: none;
  &:hover {
    text-decoration: underline;
  }
}

.message-thinking {
  margin-top: 8px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 10px;
  font-size: 12px;
  border: 1px dashed var(--border-color);
}

.thinking-label {
  color: var(--text-muted);
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
}

.thinking-content {
  color: var(--text-secondary);
  white-space: pre-wrap;
  font-family: var(--font-family-mono);
  opacity: 0.9;
}
</style>
