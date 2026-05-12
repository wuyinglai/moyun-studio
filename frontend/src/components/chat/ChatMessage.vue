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

<style scoped>
.chat-message {
  display: flex;
  gap: 10px;
  max-width: 100%;
}

.role-user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.role-user .message-avatar {
  background: var(--accent-primary);
  color: white;
}

.role-ai .message-avatar {
  background: var(--bg-card);
  color: var(--text-secondary);
}

.message-body {
  flex: 1;
  min-width: 0;
  max-width: 80%;
}

.role-user .message-body {
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}

.role-user .message-meta {
  flex-direction: row-reverse;
}

.message-role {
  color: var(--text-muted);
}

.message-time {
  color: var(--text-muted);
  font-size: 11px;
}

.message-content {
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.role-user .message-content {
  background: var(--accent-primary);
  color: white;
  border-bottom-right-radius: 4px;
}

.role-ai .message-content {
  background: var(--bg-card);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.ai-content :deep(p:first-child) { margin-top: 0; }
.ai-content :deep(p:last-child) { margin-bottom: 0; }
.ai-content :deep(code) {
  background: rgba(255,255,255,0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.message-thinking {
  margin-top: 6px;
  padding: 6px 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: 12px;
}

.thinking-label {
  color: var(--text-muted);
  display: block;
  margin-bottom: 4px;
}

.thinking-content {
  color: var(--text-secondary);
  white-space: pre-wrap;
}
</style>
