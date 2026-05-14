<template>
  <div class="chat-input">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        :placeholder="placeholder || '输入消息...'"
        :disabled="disabled"
        @keydown="handleKeydown"
        @input="autoResize"
        rows="1"
      ></textarea>

      <div class="input-actions">
        <span class="char-count" v-if="showCharCount">{{ charCount }}</span>
        <button
          class="send-btn"
          :disabled="!canSend"
          @click="handleSend"
          title="发送 (Enter)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="input-hint">
      <span><kbd>Enter</kbd> 发送</span>
      <span><kbd>Shift</kbd> + <kbd>Enter</kbd> 换行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

defineProps<{
  placeholder?: string
  disabled?: boolean
  showCharCount?: boolean
  maxLength?: number
}>()

const emit = defineEmits<{
  (e: 'send', content: string): void
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const inputText = ref('')

const canSend = computed(() => inputText.value.trim().length > 0)
const charCount = computed(() => inputText.value.length)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSend() {
  if (!canSend.value) return
  const content = inputText.value.trim()
  emit('send', content)
  inputText.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}

function autoResize() {
  if (!textareaRef.value) return
  textareaRef.value.style.height = 'auto'
  textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 200) + 'px'
}

function focus() {
  textareaRef.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped lang="scss">
.chat-input {
  padding: 0;
  background: transparent;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--ink-mid);
  border: 1px solid var(--border-ink);
  border-radius: var(--radius-lg);
  padding: 10px 14px;
  transition: all var(--transition-normal);

  &:focus-within {
    border-color: var(--gold-primary);
    box-shadow: 0 0 0 3px rgba(201, 169, 110, 0.08), 0 4px 14px rgba(0, 0, 0, 0.15);
  }
}

textarea {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
  max-height: 200px;
  overflow-y: auto;
  font-family: var(--font-body);

  &::placeholder {
    color: var(--text-faint);
  }

  &:disabled {
    opacity: 0.5;
  }
}

/* ── 右侧操作区 ── */
.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.char-count {
  font-size: 11px;
  color: var(--text-faint);
  font-weight: 500;
}

/* ── 发送按钮 ── */
.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
  color: var(--ink-deepest);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  border: none;
  cursor: pointer;
  flex-shrink: 0;

  &:hover:not(:disabled) {
    transform: scale(1.08);
    box-shadow: 0 4px 12px rgba(201, 169, 110, 0.3);
  }

  &:active:not(:disabled) {
    transform: scale(1.03);
  }

  &:disabled {
    background: var(--ink-light);
    color: var(--text-faint);
    cursor: not-allowed;
  }
}

/* ── 快捷键提示 ── */
.input-hint {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-faint);
  justify-content: center;
}

.input-hint kbd {
  background: var(--ink-mid);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
  border: 1px solid var(--border-ink);
  font-family: var(--font-mono);
}
</style>
