<template>
  <div class="prompt-panel">
    <!-- 工作流任务引导 -->
    <div class="wf-guide">
      <div class="wf-guide-header">
        <span class="wf-guide-title" v-if="workflowLabel">{{ workflowLabel }}</span>
        <span class="wf-guide-title" v-else>创作任务</span>
        <button class="wf-refresh" @click="reloadWorkflow" title="刷新工作流">
          <i class="fa-solid fa-rotate"></i>
        </button>
      </div>

      <!-- 加载失败 -->
      <div v-if="wfError" class="wf-error">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>{{ wfError }}</span>
        <button class="wf-retry" @click="reloadWorkflow">重试</button>
      </div>

      <!-- 引导说明（工作流未启动时） -->
      <div v-if="!guide.isRunning.value && guide.steps.value.length > 0 && !wfError" class="wf-guidance">
        <i class="fa-solid fa-circle-info"></i>
        <span>点击「开始创作」，AI 将按以下步骤自动生成小说</span>
      </div>

      <!-- 步骤列表 -->
      <div v-if="!wfError" class="wf-steps">
        <div
          v-for="(step, idx) in guide.steps.value"
          :key="step.id"
          class="wf-step"
          :class="[step.status]"
          :title="stepTooltip(step)"
        >
          <span class="wf-step-icon">{{ stepIcon(step.status) }}</span>
          <span class="wf-step-label">{{ step.label }}</span>
          <span class="wf-step-badge">{{ step.type === 'loop' ? '循环' : '' }}</span>
          <div class="wf-step-action">
            <!-- 运行中 -->
            <span v-if="step.status === 'running'" class="wf-spinner">
              <i class="fa-solid fa-spinner fa-spin"></i>
            </span>
            <!-- 等待中（L1）— 显示状态，确认按钮移到了顶部工具栏 -->
            <span v-else-if="step.status === 'waiting'" class="wf-waiting-badge">
              等待确认
            </span>
            <!-- 可执行的步骤 -->
            <button
              v-else-if="step.status === 'pending' && !guide.isRunning.value"
              class="wf-btn-run-step"
              @click="handleRunStep(idx)"
            >
              <i class="fa-solid fa-play"></i> 执行
            </button>
          </div>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="wf-actions" v-if="!wfError">
        <button
          v-if="!guide.isRunning.value"
          class="wf-btn-start"
          @click="handleStartWorkflow"
          :disabled="!canStart"
        >
          <i class="fa-solid fa-play"></i> 开始创作
        </button>
        <button
          v-if="guide.isRunning.value"
          class="wf-btn-stop"
          @click="handleStopWorkflow"
        >
          <i class="fa-solid fa-stop"></i> 停止
        </button>
        <button
          v-if="!guide.isRunning.value && hasDoneSteps"
          class="wf-btn-reset"
          @click="handleReset"
        >
          <i class="fa-solid fa-rotate-left"></i> 重置
        </button>
      </div>

      <!-- 进度条 -->
      <div class="wf-progress" v-if="guide.steps.value.length > 0 && !wfError">
        <div class="wf-progress-bar">
          <div class="wf-progress-fill" :style="{ width: guide.progress.value.percent + '%' }"></div>
        </div>
        <span class="wf-progress-text">{{ guide.progress.value.done }}/{{ guide.progress.value.total }}</span>
      </div>

      <!-- 暂停状态提示 -->
      <div v-if="guide.isPaused.value" class="wf-pause-msg">
        <i class="fa-solid fa-circle-pause"></i>
        <span v-if="hasWaitingStep">{{ l1PauseText }}</span>
        <span v-else>{{ l2PauseText }}</span>
      </div>
    </div>

    <!-- 生成状态提示 -->
    <div v-if="guide.isRunning.value" class="generation-status">
      <i class="fa-solid fa-spinner fa-spin"></i>
      <span>AI 正在生成...</span>
    </div>
    <div v-else-if="fileGen.currentPrompt.value" class="generation-status generation-done">
      <i class="fa-solid fa-check"></i>
      <span>上次生成完成，prompt 已填入下方编辑框</span>
    </div>

    <!-- Prompt 历史导航 M0402-4 -->
    <div class="history-nav" v-if="promptHistory.length > 0">
      <button class="history-btn" :disabled="!canGoBack" @click="goBack" title="上一个版本">
        <i class="fa-solid fa-chevron-left"></i>
      </button>
      <span class="history-indicator">{{ historyPos }}</span>
      <button class="history-btn" :disabled="!canGoForward" @click="goForward" title="下一个版本">
        <i class="fa-solid fa-chevron-right"></i>
      </button>
      <button class="history-btn history-clear" @click="clearHistory" title="清空历史">
        <i class="fa-solid fa-trash-can"></i>
      </button>
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
import { useRightPanelStore } from '@/stores/rightPanel'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import { useFileStore } from '@/stores/file'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { useWorkflowGuide } from '@/composables/useWorkflowGuide'
import { useLLMStore } from '@/stores/llm'

const rightPanelStore = useRightPanelStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()
const fileStore = useFileStore()
const fileGen = useFileGeneration()
const guide = useWorkflowGuide()
const llmStore = useLLMStore()

const localPrompt = ref('')
const varHint = '{{变量名}}'
const isFreeMode = ref(true)
let saveTimeout: ReturnType<typeof setTimeout> | null = null

// 工作流状态
const workflowLabel = computed(() => guide.workflowLabel.value)
const wfError = computed(() => guide.error.value)
const canStart = computed(() => !!projectStore.currentProject && !!editorStore.currentFilePath)
const hasDoneSteps = computed(() => guide.steps.value.some(s => s.status === 'done' || s.status === 'waiting'))
const hasWaitingStep = computed(() => guide.steps.value.some(s => s.status === 'waiting'))
const l1PauseText = '已完成！点击顶部工具栏「写下一部分」继续'
const l2PauseText = '已停止，可点击顶部工具栏「写下一部分」恢复'

function stepTooltip(step: { label: string; pipeline?: string; type: string }): string {
  if (step.type === 'pipeline' && step.pipeline) {
    return `${step.label} — 执行管线: ${step.pipeline}`
  }
  return step.label
}

async function reloadWorkflow() {
  await guide.reset()
  await guide.loadWorkflow()
}

function stepIcon(status: string): string {
  switch (status) {
    case 'running': return '◌'
    case 'done': return '✅'
    case 'waiting': return '⏸'
    default: return '□'
  }
}

/** 一键开始 */
async function handleStartWorkflow() {
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    return
  }
  const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
  const filePath = editorStore.currentFilePath
  if (!projectId || !filePath) {
    notification.warning('请先打开一个文件和项目')
    return
  }
  await guide.start(projectId, filePath)
}

/** 单步执行 */
async function handleRunStep(idx: number) {
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    return
  }
  const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
  const filePath = editorStore.currentFilePath
  if (!projectId || !filePath) {
    notification.warning('请先打开一个文件和项目')
    return
  }

  guide.reset()
  guide.currentStepIndex.value = idx
  await guide.start(projectId, filePath)
}

function handleStopWorkflow() {
  guide.stopAfterCurrent()
}

function handleReset() {
  guide.reset()
}

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

const isPipelineRunning = computed(() => rightPanelStore.isPipelineRunning)

// 历史导航
const promptHistory = computed(() => rightPanelStore.promptHistory)
const currentHistoryIndex = computed(() => rightPanelStore.currentHistoryIndex)
const canGoBack = computed(() => currentHistoryIndex.value < promptHistory.value.length - 1)
const canGoForward = computed(() => currentHistoryIndex.value > -1)
const historyPos = computed(() => {
  if (promptHistory.value.length === 0) return ''
  const current = currentHistoryIndex.value === -1 ? promptHistory.value.length : promptHistory.value.length - 1 - currentHistoryIndex.value
  return `${current} / ${promptHistory.value.length}`
})

function goBack() {
  rightPanelStore.goPromptHistoryBack()
  localPrompt.value = rightPanelStore.promptContent
}

function goForward() {
  rightPanelStore.goPromptHistoryForward()
  localPrompt.value = rightPanelStore.promptContent
}

function clearHistory() {
  rightPanelStore.clearHistory()
}

onMounted(() => {
  // 加载工作流定义
  guide.loadWorkflow()

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

// 管线运行时，将每次生成的 prompt 实时显示到编辑框
watch(
  () => fileGen.currentPrompt.value,
  (val) => {
    if (val && (guide.isRunning.value || isPipelineRunning.value)) {
      localPrompt.value = val
      rightPanelStore.updatePrompt(val)
    }
  },
)

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
    rightPanelStore.updatePrompt(localPrompt.value)
  }, 500)
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

// ── 工作流任务引导 ─────────────────────────────

.wf-guide {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 10px 12px;
  margin-bottom: 12px;
}

.wf-guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.wf-guide-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.wf-refresh {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-btn);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 10px;
  transition: all 0.15s;

  &:hover {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }
}

.wf-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--accent-error);
  padding: 6px 0;

  .wf-retry {
    margin-left: auto;
    padding: 2px 8px;
    font-size: 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-btn);
    color: var(--accent-primary);
    cursor: pointer;
  }
}

.wf-guidance {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: rgba(107, 140, 255, 0.1);
  border: 1px solid rgba(107, 140, 255, 0.25);
  border-radius: var(--radius-sm);
  font-size: 11px;
  line-height: 1.5;
  color: var(--accent-primary);

  i {
    margin-top: 1px;
    flex-shrink: 0;
  }
}

.wf-steps {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.wf-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  transition: background 0.15s;

  &.running {
    background: rgba(107, 140, 255, 0.08);
  }

  &.done {
    opacity: 0.7;
  }

  &.waiting {
    background: rgba(245, 158, 11, 0.08);
    opacity: 1;
  }
}

.wf-step-icon {
  width: 18px;
  text-align: center;
  font-size: 12px;
  flex-shrink: 0;
}

.wf-step-label {
  flex: 1;
  color: var(--text-primary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-step-badge {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-muted);
}

.wf-step-action {
  flex-shrink: 0;
  min-width: 60px;
  text-align: right;
}

.wf-spinner {
  color: var(--accent-primary);
  font-size: 11px;
}

.wf-btn-run-step {
  padding: 2px 8px;
  font-size: 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-btn);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }
}

.wf-btn-confirm {
  padding: 2px 8px;
  font-size: 10px;
  background: var(--accent-warning);
  border: none;
  border-radius: var(--radius-btn);
  color: white;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;

  &:hover {
    opacity: 0.85;
  }
}

.wf-waiting-badge {
  font-size: 10px;
  color: var(--accent-warning);
  padding: 2px 6px;
  border: 1px solid var(--accent-warning);
  border-radius: var(--radius-btn);
}

.wf-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.wf-btn-start {
  flex: 1;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: white;
  border: none;
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition: opacity 0.15s;

  &:hover:not(:disabled) {
    opacity: 0.9;
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.wf-btn-stop {
  flex: 1;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  background: var(--accent-error);
  color: white;
  border: none;
  border-radius: var(--radius-btn);
  cursor: pointer;

  &:hover {
    opacity: 0.9;
  }
}

.wf-btn-reset {
  padding: 6px 10px;
  font-size: 11px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-btn);
  color: var(--text-muted);
  cursor: pointer;

  &:hover {
    border-color: var(--text-muted);
    color: var(--text-secondary);
  }
}

.wf-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.wf-progress-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-primary);
  border-radius: 2px;
  overflow: hidden;
}

.wf-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  transition: width 0.3s ease;
  border-radius: 2px;
}

.wf-progress-text {
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.wf-pause-msg {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 8px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--accent-warning);
  background: rgba(245, 158, 11, 0.08);
  border-radius: var(--radius-sm);

  i {
    margin-top: 1px;
    flex-shrink: 0;
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

.history-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding: 4px 0;
}

.history-btn {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-btn);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }

  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
}

.history-clear:hover:not(:disabled) {
  border-color: var(--accent-error);
  color: var(--accent-error);
}

.history-indicator {
  font-size: 11px;
  color: var(--text-muted);
  min-width: 40px;
  text-align: center;
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
