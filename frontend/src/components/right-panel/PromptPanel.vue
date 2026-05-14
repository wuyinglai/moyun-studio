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
        <a-select-option key="_free" value="_free">📝 自由编辑</a-select-option>
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
        ▶ {{ isFreeMode ? '发送' : '运行' }}
      </a-button>
    </div>

    <!-- 步骤标签（仅管线模式） -->
    <div class="step-tabs" v-if="!isFreeMode && storeSteps.length > 0">
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
    <div v-else-if="fileGen.currentPrompt.value" class="generation-status generation-done">
      <i class="fa-solid fa-check"></i>
      <span>上次生成完成，prompt 已填入下方编辑框</span>
    </div>

    <!-- Prompt 编辑区 -->
    <div class="editor-section">
      <div class="editor-label">{{ isFreeMode ? '提示词（自由编辑）' : '当前步骤 Prompt（可直接编辑）' }}</div>
      <a-textarea
        v-model:value="localPrompt"
        :placeholder="isFreeMode ? '输入提示词，点击发送...' : '选择管线步骤查看 Prompt...'"
        :auto-size="{ minRows: 8, maxRows: 16 }"
        @input="handlePromptInput"
        class="prompt-editor"
      />
      <!-- @{path} 引用文件列表 -->
      <div v-if="fileRefs.length > 0" class="file-refs">
        <div class="file-refs-label">引用文件</div>
        <div class="file-refs-list">
          <a
            v-for="ref in fileRefs"
            :key="ref.path"
            class="file-ref-chip"
            @click="openReferencedFile(ref.path)"
            title="点击打开该文件"
          >
            <i class="fa-solid fa-file-lines"></i>
            {{ ref.path }}
          </a>
        </div>
      </div>
      <div class="editor-hint">
        提示：使用 <code>@{文件路径}</code> 引用文件，<code>{{ varHint }}</code> 使用系统变量
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
import { useNotificationStore } from '@/stores/notification'
import { useFileStore } from '@/stores/file'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { useTaskQueue } from '@/composables/useTaskQueue'

const pipelineStore = usePipelineStore()
const rightPanelStore = useRightPanelStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()
const fileStore = useFileStore()
const fileGen = useFileGeneration()
const taskQueue = useTaskQueue()

const localPrompt = ref('')
const varHint = '{{变量名}}'
const isFreeMode = ref(true)
let saveTimeout: ReturnType<typeof setTimeout> | null = null

// 从 prompt 文本中提取 @{path} 引用
const fileRefs = computed(() => {
  const refs: { path: string }[] = []
  const pattern = /@\{([^}]+)\}/g
  let match: RegExpExecArray | null
  while ((match = pattern.exec(localPrompt.value)) !== null) {
    const path = match[1].trim()
    if (path && !refs.some(r => r.path === path)) {
      refs.push({ path })
    }
  }
  return refs
})

const storePipelines = computed(() => pipelineStore.pipelines)
const storeSteps = computed(() => pipelineStore.currentDetail?.steps || [])
const currentStepIndex = computed(() => pipelineStore.currentStepIndex)
const isPipelineRunning = computed(() => rightPanelStore.isPipelineRunning)

const selectedPipeline = ref('_free')

onMounted(() => {
  if (pipelineStore.pipelines.length === 0) {
    pipelineStore.fetchPipelines()
  }
  // 初始显示右侧面板保存的 prompt（切换文件时自动更新）
  localPrompt.value = rightPanelStore.promptContent || ''
})

// 切换文件时，右侧面板 promptContent 由 App.vue 更新，此处同步到编辑器
watch(
  () => rightPanelStore.promptContent,
  (val) => {
    if (isFreeMode.value) {
      localPrompt.value = val || ''
    }
  },
)

// 管线步骤切换时，显示该步骤的 prompt 模板
watch(
  () => pipelineStore.currentStep,
  (step) => {
    if (!isFreeMode.value && step?.prompt_content) {
      localPrompt.value = step.prompt_content
    }
  },
  { deep: true },
)

// 管线运行时，将每次生成的 prompt 实时显示到编辑框
watch(
  () => fileGen.currentPrompt.value,
  (val) => {
    if (val && isPipelineRunning.value) {
      localPrompt.value = val
      rightPanelStore.updatePrompt(val)
    }
  },
)

function onPipelineChange(name: string) {
  selectedPipeline.value = name
  if (name === '_free') {
    isFreeMode.value = true
    localPrompt.value = rightPanelStore.promptContent || ''
  } else {
    isFreeMode.value = false
    pipelineStore.selectPipeline(name)
  }
}

function onStepChange(index: number) {
  pipelineStore.selectStep(index)
}

function openReferencedFile(path: string) {
  const name = path.split('/').pop() || path
  const node = { name, path, type: 'file' as const }
  fileStore.openFile(node)
  editorStore.setCurrentFile(path)
  notification.info(`已打开: ${path}`)
}

function handlePromptInput() {
  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    if (isFreeMode.value) {
      rightPanelStore.updatePrompt(localPrompt.value)
    } else {
      const step = pipelineStore.currentStep
      if (step) {
        pipelineStore.saveStepPrompt(step.id, localPrompt.value)
      }
    }
  }, 500)
}

async function runCurrentPipeline() {
  if (!projectStore.currentProject || !editorStore.currentFilePath) {
    notification.warning('请先打开一个文件')
    return
  }
  if (isPipelineRunning.value) return

  rightPanelStore.setPipelineRunning(true)
  const fileName = editorStore.currentFilePath.split('/').pop() || ''
  const pipelineName = isFreeMode.value ? 'polish' : selectedPipeline.value

  try {
    await taskQueue.enqueue(
      async () => {
        await fileGen.runPipeline(
          projectStore.currentProject!.id,
          editorStore.currentFilePath!,
          pipelineName,
        )
      },
      `${pipelineName}: ${fileName}`,
    )
  } catch (e: any) {
    notification.error('管线运行失败: ' + (e.message || '未知错误'))
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

.generation-done {
  color: var(--text-secondary);
  font-size: 12px;
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

.file-refs {
  margin-top: 6px;
}

.file-refs-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.file-refs-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.file-ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  font-size: 11px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--accent-primary);
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
  }

  i {
    font-size: 10px;
  }
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
