<template>
  <div class="pipeline-editor">
    <!-- 管线选择器 -->
    <div class="editor-header">
      <a-select
        v-model:value="selectedPipelineName"
        style="flex: 1; min-width: 0;"
        size="small"
        @change="onPipelineSelect"
      >
        <a-select-option v-for="p in pipelineStore.pipelines" :key="p.name" :value="p.name">
          {{ p.label }}
        </a-select-option>
      </a-select>
      <a-button size="small" @click="showNewPipelineDialog">+ 新建</a-button>
    </div>

    <!-- 步骤列表 -->
    <div class="step-list-section">
      <div class="section-label">步骤列表</div>
      <div class="step-list">
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
          <a-button type="text" size="small" @click.stop="removeStep(index)" class="step-remove">✕</a-button>
        </div>
      </div>
      <a-button type="dashed" block size="small" @click="addStep" class="add-step-btn">
        + 添加步骤
      </a-button>
    </div>

    <!-- Prompt 编辑区 -->
    <div class="prompt-section" v-if="editingStep">
      <div class="section-label">步骤 Prompt</div>
      <a-textarea
        v-model:value="editingPrompt"
        :auto-size="{ minRows: 8, maxRows: 16 }"
        class="prompt-editor"
        placeholder="在此编辑步骤的 Prompt 模板..."
      />
      <div class="editor-actions">
        <a-button size="small" @click="saveCurrentStepPrompt">保存</a-button>
        <a-button type="primary" size="small" @click="saveAll">保存全部</a-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>选择一个管线步骤开始编辑</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Button as AButton, Select as ASelect, SelectOption as ASelectOption } from 'ant-design-vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useNotificationStore } from '@/stores/notification'

const pipelineStore = usePipelineStore()
const notification = useNotificationStore()

const selectedPipelineName = ref('polish')
const editingStepIndex = ref(0)
const localSteps = ref<{ id: string; label: string; prompt_content: string; fallback: string | null }[]>([])
const editingPrompt = ref('')

const editingStep = computed(() => {
  if (editingStepIndex.value < 0 || editingStepIndex.value >= localSteps.value.length) return null
  return localSteps.value[editingStepIndex.value]
})

onMounted(() => {
  if (pipelineStore.pipelines.length === 0) {
    pipelineStore.fetchPipelines()
  }
  if (pipelineStore.currentDetail) {
    loadFromStore()
  }
})

watch(() => pipelineStore.currentDetail, (detail) => {
  if (detail) loadFromStore()
})

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
}

watch(editingStep, () => {
  syncEditingPrompt()
})

async function onPipelineSelect(name: string) {
  await pipelineStore.selectPipeline(name)
  // selectPipeline fetches detail and updates currentDetail
}

function removeStep(index: number) {
  if (localSteps.value.length <= 1) return
  localSteps.value.splice(index, 1)
  if (editingStepIndex.value >= localSteps.value.length) {
    editingStepIndex.value = localSteps.value.length - 1
  }
}

function addStep() {
  const newId = `step-${Date.now()}`
  localSteps.value.push({
    id: newId,
    label: '新步骤',
    prompt_content: '# 新步骤\n\n请对以下文本进行处理：\n\n## 原文\n{{ file_content }}\n\n## 要求\n请输入具体要求...\n',
    fallback: null,
  })
  editingStepIndex.value = localSteps.value.length - 1
}

async function saveCurrentStepPrompt() {
  if (!editingStep.value) return
  const step = editingStep.value
  step.prompt_content = editingPrompt.value
  try {
    await pipelineStore.saveStepPrompt(step.id, editingPrompt.value)
    notification.success('Prompt 已保存')
  } catch {
    notification.error('保存失败')
  }
}

async function saveAll() {
  // Sync editing prompt to current step
  if (editingStep.value) {
    editingStep.value.prompt_content = editingPrompt.value
  }

  try {
    // Save all step definitions
    const stepsData = localSteps.value.map(s => ({
      id: s.id,
      label: s.label,
      prompt_content: s.prompt_content,
    }))
    await pipelineStore.saveStepPrompt(stepsData[0]?.id || '', stepsData[0]?.prompt_content || '')
    notification.success('管线已保存')
  } catch {
    notification.error('保存管线失败')
  }
}

function showNewPipelineDialog() {
  // For MVP, create a simple pipeline with default steps
  notification.info('新建管线功能即将上线')
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
