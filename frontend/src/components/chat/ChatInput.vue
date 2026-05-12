<template>
  <div class="chat-input">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        :placeholder="placeholder"
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
          title="发送（Enter）"
        >
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </div>
    </div>

    <div class="input-hint">
      <span><kbd>Enter</kbd> 发送</span>
      <span><kbd>Shift + Enter</kbd> 换行</span>
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
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 12px 14px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);

  &:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px rgba(107, 140, 255, 0.15), 0 4px 14px rgba(0, 0, 0, 0.15);
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
  font-family: var(--font-family-ch);
}

textarea::placeholder {
  color: var(--text-muted);
}

textarea:disabled {
  opacity: 0.5;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.char-count {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.send-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.2s ease;
  border: none;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(107, 140, 255, 0.3);

  &:hover:not(:disabled) {
    transform: scale(1.1);
    box-shadow: 0 4px 12px rgba(107, 140, 255, 0.4);
  }

  &:active:not(:disabled) {
    transform: scale(1.05);
  }

  &:disabled {
    background: var(--border-color);
    color: var(--text-muted);
    cursor: not-allowed;
    box-shadow: none;
  }
}

.input-hint {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--text-muted);
  justify-content: center;
}

.input-hint kbd {
  background: var(--bg-card);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  border: 1px solid var(--border-color);
  font-family: var(--font-family-mono);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style>
