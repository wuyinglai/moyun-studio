<template>
  <div class="prompt-panel">
    <!-- 编辑工具栏 -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">当前 Prompt</span>
      </div>
      <div class="toolbar-row">
        <a-button-group>
          <a-button size="small" @click="goBack" :disabled="!canGoBack">
            <template #icon><i class="fa-solid fa-chevron-left"></i></template>
            后退
          </a-button>
          <a-button size="small" @click="goForward" :disabled="!canGoForward">
            <template #icon><i class="fa-solid fa-chevron-right"></i></template>
            前进
          </a-button>
        </a-button-group>
      </div>
      <a-textarea
        v-model:value="localPrompt"
        placeholder="在此输入您的 Prompt..."
        :auto-size="{ minRows: 10, maxRows: 20 }"
        @input="handleInput"
        class="prompt-editor"
      />
      <div class="save-status" :class="{ saving: isSaving }">
        {{ isSaving ? '保存中...' : '已保存' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Button as AButton, ButtonGroup as AButtonGroup } from 'ant-design-vue'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'

const rightPanelStore = useRightPanelStore()
const notification = useNotificationStore()
const chatStore = useChatStore()

const localPrompt = ref('')
const isSaving = ref(false)
let saveTimeout: ReturnType<typeof setTimeout> | null = null

const currentHistoryIndex = computed(() => rightPanelStore.currentHistoryIndex)
const canGoBack = computed(() => currentHistoryIndex.value < rightPanelStore.promptHistory.length - 1)
const canGoForward = computed(() => currentHistoryIndex.value > 0 || currentHistoryIndex.value === -1)

watch(
  () => rightPanelStore.promptContent,
  (newVal) => {
    localPrompt.value = newVal
  },
  { immediate: true }
)

function handleInput() {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }
  isSaving.value = true
  saveTimeout = setTimeout(() => {
    savePrompt()
  }, 500)
}

function savePrompt() {
  rightPanelStore.updatePrompt(localPrompt.value)
  isSaving.value = false
}

function goBack() {
  rightPanelStore.goPromptHistoryBack()
  localPrompt.value = rightPanelStore.promptContent
}

function goForward() {
  rightPanelStore.goPromptHistoryForward()
  localPrompt.value = rightPanelStore.promptContent
}

async function sendToAI() {
  if (!localPrompt.value) {
    notification.warning('暂无 Prompt 内容')
    return
  }
  try {
    await chatStore.sendMessage(localPrompt.value)
  } catch (e) {
    notification.error('发送失败')
  }
}
</script>

<style scoped lang="scss">
.prompt-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-section {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}

.prompt-editor {
  width: 100%;
  flex: 1;
}

.save-status {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;

  &.saving {
    color: var(--accent-warning);
  }
}

.prompt-panel :deep(.ant-btn) {
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
