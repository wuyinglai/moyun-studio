<template>
  <div class="pipeline-editor">
    <!-- 管线选择器 -->
    <div class="editor-header">
      <a-select
        v-model:value="selectedPipelineName"
        style="flex: 1; min-width: 0;"
        size="small"
        @change="(val: any) => onPipelineSelect(String(val))"
      >
        <a-select-option
          v-for="p in pipelineStore.pipelines"
          :key="p.name"
          :value="p.name"
        >
          {{ p.label }}
        </a-select-option>
      </a-select>
      <a-button
        size="small"
        @click="showNewPipelineDialog"
      >
        + 新建
      </a-button>
    </div>

    <!-- 步骤列表 -->
    <div class="step-list-section">
      <div class="section-label">
        步骤列表
      </div>
      <div
        ref="stepListRef"
        class="step-list"
      >
        <div
          v-for="(step, index) in localSteps"
          :key="step.id"
          class="step-item"
          :class="{ active: editingStepIndex === index }"
          @click="editingStepIndex = index"
        >
          <span class="step-drag">⠿</span>
          <span class="step-label">{{ step.label }}</span>
          <span class="step-id">{{ step.id }}</span>
          <a-button
            type="text"
            size="small"
            class="step-remove"
            @click.stop="removeStep(index)"
          >
            ✕
          </a-button>
        </div>
      </div>
      <a-button
        type="dashed"
        block
        size="small"
        class="add-step-btn"
        @click="addStep"
      >
        + 添加步骤
      </a-button>
    </div>

    <!-- Prompt 编辑区 -->
    <div
      v-if="editingStep"
      class="prompt-section"
    >
      <div class="section-label">
        <span>步骤 Prompt</span>
        <span
          v-if="isBrowsingHistory"
          class="browsing-badge"
        >浏览历史</span>
      </div>
      <a-textarea
        v-model:value="editingPrompt"
        :auto-size="{ minRows: 8, maxRows: 16 }"
        class="prompt-editor"
        :class="{ readonly: isBrowsingHistory }"
        :readonly="isBrowsingHistory"
        :placeholder="isBrowsingHistory ? '浏览历史版本...' : '在此编辑步骤的 Prompt 模板...'"
        @input="handlePromptInput"
      />
      <div class="editor-actions">
        <a-button
          size="small"
          :disabled="!canGoBackHistory"
          title="上一个版本"
          @click="goBackHistory"
        >
          <i class="fa-solid fa-chevron-left" /> 后退
        </a-button>
        <a-button
          size="small"
          :disabled="!canGoForwardHistory"
          title="下一个版本"
          @click="goForwardHistory"
        >
          前进 <i class="fa-solid fa-chevron-right" />
        </a-button>
        <span
          v-if="historyTotal > 0"
          class="history-pos"
        >{{ historyCurrent }}/{{ historyTotal }}</span>
        <a-button
          v-if="isBrowsingHistory"
          type="primary"
          size="small"
          @click="saveHistoryVersion"
        >
          <i class="fa-solid fa-check" /> 保存此版本
        </a-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-else
      class="empty-state"
    >
      <p>选择一个管线步骤开始编辑</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Button as AButton, Select as ASelect, SelectOption as ASelectOption } from 'ant-design-vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useHistoryStore } from '@/stores/history'
import { useNotificationStore } from '@/stores/notification'
import Sortable from 'sortablejs'

const pipelineStore = usePipelineStore()
const historyStore = useHistoryStore()
const notification = useNotificationStore()

const selectedPipelineName = ref('polish')
const editingStepIndex = ref(0)
const localSteps = ref<{ id: string; label: string; prompt_content: string; fallback: string | null }[]>([])
const editingPrompt = ref('')
const lastSnapshotContent = ref('')
const stepListRef = ref<HTMLElement | null>(null)
let sortableInstance: any = null
let snapshotTimer: ReturnType<typeof setTimeout> | null = null
let saveTimer: ReturnType<typeof setTimeout> | null = null

const historyKey = computed(() => {
  const step = editingStep.value
  if (!step || !selectedPipelineName.value) return ''
  return `pipeline/${selectedPipelineName.value}/${step.id}`
})

const isBrowsingHistory = computed(() => historyKey.value ? historyStore.isBrowsing : false)
const canGoBackHistory = computed(() => historyStore.canGoBack(historyKey.value))
const canGoForwardHistory = computed(() => historyStore.canGoForward(historyKey.value))
const historyTotal = computed(() => historyKey.value ? historyStore.getHistory(historyKey.value).length : 0)
const historyCurrent = computed(() => {
  if (!historyKey.value) return 0
  const idx = historyStore.getCurrentIndex(historyKey.value)
  return idx + 1
})

const editingStep = computed(() => {
  if (editingStepIndex.value < 0 || editingStepIndex.value >= localSteps.value.length) return null
  return localSteps.value[editingStepIndex.value]
})

function initSortable() {
  destroySortable()
  if (!stepListRef.value) return
  sortableInstance = Sortable.create(stepListRef.value, {
    handle: '.step-drag',
    animation: 150,
    easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    ghostClass: 'step-dragging',
    onEnd: (evt: any) => {
      const { oldIndex, newIndex } = evt
      if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) return
      const item = localSteps.value.splice(oldIndex, 1)[0]
      localSteps.value.splice(newIndex, 0, item)
      editingStepIndex.value = newIndex
    },
  })
}

function destroySortable() {
  if (sortableInstance) {
    sortableInstance.destroy()
    sortableInstance = null
  }
}

onMounted(() => {
  if (pipelineStore.pipelines.length === 0) pipelineStore.fetchPipelines()
  if (pipelineStore.currentDetail) loadFromStore()
  nextTick(() => initSortable())
})

onUnmounted(() => {
  destroySortable()
  if (snapshotTimer) clearTimeout(snapshotTimer)
  if (saveTimer) clearTimeout(saveTimer)
})

watch(() => pipelineStore.currentDetail, (d) => { if (d) { loadFromStore(); nextTick(() => initSortable()) } })

function loadFromStore() {
  if (!pipelineStore.currentDetail) return
  localSteps.value = pipelineStore.currentDetail.steps.map(s => ({ ...s }))
  selectedPipelineName.value = pipelineStore.currentDetail.name
  editingStepIndex.value = 0
  syncEditingPrompt()
}

function syncEditingPrompt() {
  const step = editingStep.value
  editingPrompt.value = step?.prompt_content || ''
  lastSnapshotContent.value = editingPrompt.value
  resetSnapshotTimer()
}

watch(editingStep, () => syncEditingPrompt())

function handlePromptInput() {
  if (isBrowsingHistory.value) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => doSave(), 300)
  resetSnapshotTimer()
}

async function doSave() {
  if (!editingStep.value) return
  editingStep.value.prompt_content = editingPrompt.value
  await pipelineStore.saveStepPrompt(editingStep.value.id, editingPrompt.value)
}

function resetSnapshotTimer() {
  if (snapshotTimer) clearTimeout(snapshotTimer)
  snapshotTimer = setTimeout(checkSnapshot, 10000)
}

function checkSnapshot() {
  const key = historyKey.value
  if (!key) return
  const current = editingPrompt.value
  if (current && current !== lastSnapshotContent.value) {
    historyStore.pushHistory(key, current)
    lastSnapshotContent.value = current
  }
  resetSnapshotTimer()
}

function goBackHistory() {
  const key = historyKey.value
  if (!key) return
  const content = historyStore.goBack(key)
  if (content !== null) editingPrompt.value = content
}

function goForwardHistory() {
  const key = historyKey.value
  if (!key) return
  const content = historyStore.goForward(key)
  if (content !== null) editingPrompt.value = content
}

function saveHistoryVersion() {
  const key = historyKey.value
  if (!key) return
  historyStore.saveCurrentVersion(key)
  if (editingStep.value) {
    editingStep.value.prompt_content = editingPrompt.value
    pipelineStore.saveStepPrompt(editingStep.value.id, editingPrompt.value)
  }
  notification.success('已保存此版本')
}

async function onPipelineSelect(name: string) {
  await pipelineStore.selectPipeline(name)
}

async function showNewPipelineDialog() {
  const name = window.prompt('请输入新管线标识，例如 custom-polish')
  if (!name) return
  const safeName = name.trim()
  if (!safeName) return
  const label = window.prompt('请输入新管线名称', safeName) || safeName
  await pipelineStore.createCustomPipeline(safeName, label.trim() || safeName, [{
    id: 'step-1',
    label: '第一步',
    prompt_content: '# 第一步\n\n请处理以下文本：\n\n{{ file_content }}\n',
  }])
  await pipelineStore.selectPipeline(safeName)
  notification.success('已创建自定义管线')
}

function removeStep(index: number) {
  if (localSteps.value.length <= 1) return
  localSteps.value.splice(index, 1)
  if (editingStepIndex.value >= localSteps.value.length) editingStepIndex.value = localSteps.value.length - 1
}

function addStep() {
  localSteps.value.push({
    id: `step-${Date.now()}`,
    label: '新步骤',
    prompt_content: '# 新步骤\n\n请对以下文本进行处理：\n\n## 原文\n{{ file_content }}\n\n## 要求\n请输入具体要求...\n',
    fallback: null,
  })
  editingStepIndex.value = localSteps.value.length - 1
}
</script>
<style scoped lang="scss">
.pipeline-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 12px;
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.step-list-section {
  margin-bottom: 12px;
}

.section-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 6px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-primary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;

  &:hover {
    border-color: var(--border-color);
    background: var(--bg-card);
  }

  &.active {
    border-color: var(--accent-primary);
    background: var(--bg-hover);
  }
}

.step-drag {
  cursor: grab;
  color: var(--text-muted);
  font-size: 14px;
  user-select: none;
  touch-action: none;
}

.step-dragging {
  opacity: 0.5;
  border-color: var(--accent-primary) !important;
  background: var(--bg-hover) !important;
}

.step-label {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}

.step-id {
  font-size: 11px;
  color: var(--text-muted);
  font-family: monospace;
}

.step-remove {
  opacity: 0.5;
  &:hover { opacity: 1; }
}

.add-step-btn {
  font-size: 12px;
}

.prompt-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.prompt-editor {
  flex: 1;
  width: 100%;
  min-height: 120px;

  &.readonly {
    opacity: 0.7;
    cursor: default;
  }
}

.browsing-badge {
  font-size: 10px;
  color: var(--gold-primary);
  background: rgba(201, 169, 110, 0.1);
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
}

.history-pos {
  font-size: 11px;
  color: var(--text-muted);
  align-self: center;
}

.editor-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
