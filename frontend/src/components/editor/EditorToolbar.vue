<template>
  <div class="editor-toolbar">
    <a-space>
      <a-button size="small" @click="handleBack" :disabled="!canGoBack">
        <template #icon><i class="fa-solid fa-rotate-left"></i></template>
        后退
      </a-button>
      <a-button size="small" @click="handleForward" :disabled="!canGoForward">
        <template #icon><i class="fa-solid fa-rotate-right"></i></template>
        前进
      </a-button>
      <a-divider type="vertical" />
      <a-button v-if="isGenerating" danger size="small" @click="handleStop">
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
        <a-divider type="vertical" />
        <a-button size="small" @click="handleTokenCount">
          <template #icon><i class="fa-solid fa-calculator"></i></template>
          Token
        </a-button>
        <a-button size="small" @click="handleCompare">
          <template #icon><i class="fa-solid fa-code-compare"></i></template>
          对比
        </a-button>
        <a-button size="small" @click="handleFeedback">
          <template #icon><i class="fa-solid fa-comment"></i></template>
          反馈
        </a-button>
        <a-button size="small" @click="handleRevisionLog">
          <template #icon><i class="fa-solid fa-clock-rotate-left"></i></template>
          修改日志
        </a-button>
        <a-divider type="vertical" />
        <a-button size="small" @click="handleBatchGenerate">
          <template #icon><i class="fa-solid fa-wand-magic-sparkles"></i></template>
          批量生成
        </a-button>
        <a-button size="small" @click="handleQualityReview">
          <template #icon><i class="fa-solid fa-check-circle"></i></template>
          质量审查
        </a-button>
        <a-button size="small" @click="handleExtract">
          <template #icon><i class="fa-solid fa-brain"></i></template>
          提取
        </a-button>
      </template>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button as AButton, Space as ASpace, Divider as ADivider } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'
import { useHistoryStore } from '@/stores/history'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import { useUIStore } from '@/stores/ui'

const chatStore = useChatStore()
const historyStore = useHistoryStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()
const uiStore = useUIStore()

const isGenerating = computed(() => chatStore.isStreaming)

// M0302-4: 后退 — 恢复到上一个版本快照
function handleBack() {
  const path = editorStore.currentFilePath
  if (!path) return
  const content = historyStore.goBack(path)
  if (content !== null) {
    editorStore.setContent(content)
    notification.info('已恢复到上一个版本')
  } else {
    notification.warning('没有更早的版本')
  }
}

// M0302-3: 前进 — 恢复下一个版本快照
function handleForward() {
  const path = editorStore.currentFilePath
  if (!path) return
  const content = historyStore.goForward(path)
  if (content !== null) {
    editorStore.setContent(content)
    notification.info('已恢复到下一个版本')
  } else {
    notification.warning('没有更新的版本')
  }
}

const canGoBack = computed(() => {
  return historyStore.canGoBack(editorStore.currentFilePath || undefined)
})

const canGoForward = computed(() => {
  return historyStore.canGoForward(editorStore.currentFilePath || undefined)
})

function handleRegenerate() {
  window.dispatchEvent(new CustomEvent('chat:request-rewrite'))
}

function handleGenerateNext() {
  window.dispatchEvent(new CustomEvent('chat:request-generate'))
}

function handleStop() {
  chatStore.cancelStream()
}

function handleTokenCount() {
  uiStore.openTokenCount()
}

function handleCompare() {
  uiStore.openCompare()
}

function handleFeedback() {
  uiStore.openFeedback()
}

function handleRevisionLog() {
  uiStore.openRevisionLog()
}

function handleBatchGenerate() {
  uiStore.openBatchGenerate()
}

function handleQualityReview() {
  uiStore.openQualityReview()
}

function handleExtract() {
  uiStore.openExtract()
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
