<template>
  <div class="prompt-panel">
    <!-- 管线选择器 + 运行按钮 -->
    <div class="pipeline-selector">
      <a-select
        v-model:value="selectedPipeline"
        style="flex: 1; min-width: 0;"
        size="small"
        @change="onPipelineChange"
      >
        <a-select-option v-for="p in storePipelines" :key="p.name" :value="p.name">
          {{ p.label }}
        </a-select-option>
      </a-select>
      <a-button
        type="primary"
        size="small"
        :loading="isPipelineRunning"
        @click="runCurrentPipeline"
      >
        ▶ 运行
      </a-button>
    </div>

    <!-- 步骤标签 -->
    <div class="step-tabs" v-if="storeSteps.length > 0">
      <button
        v-for="(step, index) in storeSteps"
        :key="step.id"
        class="step-tab"
        :class="{ active: index === currentStepIndex }"
        @click="onStepChange(index)"
      >
        {{ step.label }}
      </button>
    </div>

    <!-- 生成状态提示 -->
    <div v-if="isPipelineRunning" class="generation-status">
      <i class="fa-solid fa-spinner fa-spin"></i>
      <span>AI 正在生成...</span>
    </div>

    <!-- Prompt 编辑区 -->
    <div class="editor-section">
      <div class="editor-label">当前步骤 Prompt（可直接编辑）</div>
      <a-textarea
        v-model:value="localPrompt"
        placeholder="选择管线步骤查看 Prompt..."
        :auto-size="{ minRows: 8, maxRows: 16 }"
        @input="handlePromptInput"
        class="prompt-editor"
      />
      <div class="editor-hint">
        提示：使用 <code>[文件名.md]</code> 引用文件，<code>{{ '{{变量名}}' }}</code> 使用系统变量
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileGeneration } from '@/composables/useFileGeneration'

const pipelineStore = usePipelineStore()
const rightPanelStore = useRightPanelStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const fileGen = useFileGeneration()

const localPrompt = ref('')
let saveTimeout: ReturnType<typeof setTimeout> | null = null

const storePipelines = computed(() => pipelineStore.pipelines)
const storeSteps = computed(() => pipelineStore.currentDetail?.steps || [])
const currentStepIndex = computed(() => pipelineStore.currentStepIndex)
const isPipelineRunning = computed(() => rightPanelStore.isPipelineRunning)
const selectedPipeline = computed({
  get: () => pipelineStore.currentPipelineName,
  set: (val: string) => pipelineStore.selectPipeline(val),
})

onMounted(() => {
  if (pipelineStore.pipelines.length === 0) {
    pipelineStore.fetchPipelines()
  }
  if (pipelineStore.currentPipelineName && !pipelineStore.currentDetail) {
    pipelineStore.fetchPipelineDetail(pipelineStore.currentPipelineName)
  }
})

watch(
  () => pipelineStore.currentPromptContent,
  (val) => {
    localPrompt.value = val || ''
  },
  { immediate: true }
)

function onPipelineChange(name: string) {
  pipelineStore.selectPipeline(name)
}

function onStepChange(index: number) {
  pipelineStore.selectStep(index)
}

function handlePromptInput() {
  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    const step = pipelineStore.currentStep
    if (step) {
      pipelineStore.saveStepPrompt(step.id, localPrompt.value)
    }
  }, 500)
}

async function runCurrentPipeline() {
  if (!projectStore.currentProject || !editorStore.currentFilePath) return
  if (isPipelineRunning.value) return

  rightPanelStore.setPipelineRunning(true)
  try {
    await fileGen.runPipeline(
      projectStore.currentProject.id,
      editorStore.currentFilePath,
      pipelineStore.currentPipelineName,
    )
  } catch (e: any) {
    console.warn('管线运行失败:', e)
  } finally {
    rightPanelStore.setPipelineRunning(false)
  }
}
</script>

<style scoped lang="scss">
.prompt-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 12px;
}

.pipeline-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.step-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.step-tab {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }

  &.active {
    background: var(--accent-primary);
    color: white;
    border-color: var(--accent-primary);
  }
}

.generation-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-primary);
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--accent-primary);
}

.editor-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.editor-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.prompt-editor {
  flex: 1;
  width: 100%;
}

.editor-hint {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;

  code {
    background: var(--bg-primary);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 11px;
  }
}
</style>
