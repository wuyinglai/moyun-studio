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

const props = withDefaults(
  defineProps<{
    placeholder?: string
    disabled?: boolean
    showCharCount?: boolean
    maxLength?: number
  }>(),
  {
    placeholder: '输入消息，按 Enter 发送...',
    disabled: false,
    showCharCount: false,
    maxLength: 4000,
  }
)

const emit = defineEmits<{
  (e: 'send', content: string): void
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const inputText = ref('')

const canSend = computed(() => inputText.value.trim().length > 0 && !props.disabled)

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
  if (content.length > props.maxLength) {
    return // 可以加提示
  }
  emit('send', content)
  inputText.value = ''
  // 重置 textarea 高度
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

<style scoped>
.chat-input {
  padding: 8px 12px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: var(--accent-primary);
}

textarea {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  max-height: 200px;
  overflow-y: auto;
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
  gap: 6px;
  flex-shrink: 0;
}

.char-count {
  font-size: 11px;
  color: var(--text-muted);
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--accent-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: scale(1.05);
}

.send-btn:disabled {
  background: var(--border-color);
  color: var(--text-muted);
  cursor: not-allowed;
}

.input-hint {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.input-hint kbd {
  background: var(--bg-card);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
  border: 1px solid var(--border-color);
}
</style>
