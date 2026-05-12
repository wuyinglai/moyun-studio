<template>
  <div class="editor-toolbar">
    <a-space>
      <a-button size="small" @click="handleUndo" :disabled="!canUndo">
        <template #icon><i class="fa-solid fa-rotate-left"></i></template>
        后退
      </a-button>
      <a-button size="small" @click="handleRedo" :disabled="!canRedo">
        <template #icon><i class="fa-solid fa-rotate-right"></i></template>
        前进
      </a-button>
      <a-divider type="vertical" />
      <a-button v-if="isGenerating" type="danger" size="small" @click="handleStop">
        <template #icon><i class="fa-solid fa-stop"></i></template>
        停止
      </a-button>
      <template v-else>
        <a-button size="small" @click="handleRegenerate">
          <template #icon><i class="fa-solid fa-redo"></i></template>
          重写
        </a-button>
        <a-button size="small" @click="handleGenerateNext">
          <template #icon><i class="fa-solid fa-forward"></i></template>
          生成下一个文件
        </a-button>
      </template>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Button as AButton, Space as ASpace, Divider as ADivider } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

const canUndo = ref(false)
const canRedo = ref(false)
const isGenerating = computed(() => chatStore.isStreaming)

function handleUndo() {
  document.execCommand('undo')
}

function handleRedo() {
  document.execCommand('redo')
}

function handleRegenerate() {
  window.dispatchEvent(new CustomEvent('chat:request-regenerate'))
}

function handleGenerateNext() {
  window.dispatchEvent(new CustomEvent('chat:request-next'))
}

function handleStop() {
  chatStore.cancelStream()
}
</script>

<style scoped lang="scss">
.editor-toolbar {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.editor-toolbar :deep(.ant-btn) {
  color: var(--text-primary);
  background: transparent;
  border: 1px solid var(--border-color);
  
  &:hover:not(:disabled) {
    color: var(--accent-primary);
    border-color: var(--accent-primary);
    background: var(--bg-hover);
  }
  
  &:disabled {
    color: var(--text-muted);
    opacity: 0.5;
  }
}
</style>
