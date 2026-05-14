<template>
  <div class="chat-message" :class="`role-${message.role}`">
    <!-- 头像 -->
    <div class="message-avatar">
      <span v-if="message.role === 'user'" class="avatar-char">你</span>
      <span v-else class="avatar-char">墨</span>
    </div>

    <div class="message-body">
      <!-- 角色名 + 时间 -->
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
        <span class="thinking-label">AI 思考过程</span>
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

const roleLabel = computed(() => {
  return props.message.role === 'user' ? '你' : '墨韵'
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
  gap: 10px;
  max-width: 100%;
  padding: 8px 0;
  animation: message-in 0.3s ease;
}

/* ── 用户消息右对齐 ── */
.role-user {
  flex-direction: row-reverse;

  .message-body {
    align-items: flex-end;
  }

  .message-meta {
    flex-direction: row-reverse;
  }

  .message-content {
    background: linear-gradient(135deg, rgba(201, 169, 110, 0.12), rgba(201, 169, 110, 0.04));
    color: var(--text-warm-white);
    border: 1px solid rgba(201, 169, 110, 0.15);
    border-bottom-right-radius: 4px;
  }

  .message-avatar {
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
    .avatar-char { color: var(--ink-deepest); }
  }

  .message-role { color: var(--gold-primary); }
}

/* ── AI 消息 ── */
.role-ai {
  .message-content {
    background: var(--ink-mid);
    color: var(--text-ink);
    border: 1px solid var(--border-ink);
    border-bottom-left-radius: 4px;
  }

  .message-avatar {
    background: var(--ink-light);
    border: 1px solid var(--border-ink);
    .avatar-char { color: var(--gold-primary); }
  }

  .message-role { color: var(--text-muted-ink); }
}

/* ── 头像 ── */
.message-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);

  .avatar-char {
    font-family: var(--font-kai);
    font-size: 14px;
    font-weight: 700;
  }
}

/* ── 消息体 ── */
.message-body {
  flex: 1;
  min-width: 0;
  max-width: 85%;
  display: flex;
  flex-direction: column;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  padding: 0 4px;
}

.message-role {
  font-size: 12px;
  font-weight: 600;
}

.message-time {
  font-size: 11px;
  color: var(--text-faint);
}

.message-content {
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

/* ── AI Markdown 内容 ── */
.ai-content {
  :deep(p:first-child) { margin-top: 0; }
  :deep(p:last-child) { margin-bottom: 0; }
  :deep(p) { margin: 0.6em 0; }

  :deep(code) {
    background: rgba(201, 169, 110, 0.1);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.9em;
    color: var(--gold-primary);
    font-family: var(--font-mono);
  }

  :deep(pre) {
    background: var(--ink-deep);
    border-radius: var(--radius-md);
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;
    border: 1px solid var(--border-ink);

    code {
      background: transparent;
      padding: 0;
      color: var(--text-ink);
    }
  }

  :deep(a) {
    color: var(--gold-primary);
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }

  :deep(blockquote) {
    border-left: 2px solid var(--gold-primary);
    padding-left: 12px;
    margin: 8px 0;
    color: var(--text-muted-ink);
    font-style: italic;
  }

  :deep(ul), :deep(ol) {
    padding-left: 20px;
    margin: 6px 0;
  }

  :deep(li) {
    margin: 3px 0;
  }

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    color: var(--text-warm-white);
    margin: 12px 0 6px;
    font-family: var(--font-display);
  }

  :deep(h1) { font-size: 1.3em; }
  :deep(h2) { font-size: 1.15em; }
  :deep(h3) { font-size: 1.05em; }

  :deep(hr) {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
    opacity: 0.15;
    margin: 12px 0;
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
    font-size: 13px;
  }

  :deep(th), :deep(td) {
    border: 1px solid var(--border-ink);
    padding: 6px 10px;
    text-align: left;
  }

  :deep(th) {
    background: var(--ink-light);
    color: var(--text-ink);
    font-weight: 600;
  }
}

/* ── Thinking 区域 ── */
.message-thinking {
  margin-top: 8px;
  padding: 10px 14px;
  background: var(--ink-deep);
  border-radius: var(--radius-md);
  font-size: 12px;
  border: 1px dashed var(--border-ink);
}

.thinking-label {
  color: var(--text-muted-ink);
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.thinking-content {
  color: var(--text-muted-ink);
  white-space: pre-wrap;
  font-family: var(--font-mono);
  font-size: 12px;
  opacity: 0.85;
  line-height: 1.6;
}
</style>
