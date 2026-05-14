<template>
  <div class="editor-toolbar">
    <a-space>
      <a-button size="small" @click="handleBack" :disabled="!canGoBack" title="后退 (没有更早的版本)">
        <template #icon><i class="fa-solid fa-rotate-left"></i></template>
        后退
      </a-button>
      <a-button size="small" @click="handleForward" :disabled="!canGoForward" title="前进 (没有更新的版本)">
        <template #icon><i class="fa-solid fa-rotate-right"></i></template>
        前进
      </a-button>
      <a-divider type="vertical" />
      <a-button size="small" @click="togglePreview" :type="isPreviewMode ? 'primary' : 'default'">
        <template #icon><i class="fa-solid fa-eye"></i></template>
        {{ isPreviewMode ? '编辑' : '预览' }}
      </a-button>
      <a-divider type="vertical" />
      <a-button v-if="isGenerating" danger size="small" @click="handleStop">
        <template #icon><i class="fa-solid fa-stop"></i></template>
        停止
      </a-button>
      <template v-else>
        <a-button size="small" type="primary" ghost @click="runPipeline('polish')">
          ✏️ 润色
        </a-button>
        <a-button size="small" type="primary" ghost @click="runPipeline('rewrite')">
          📦 重写
        </a-button>
        <a-button size="small" type="primary" ghost @click="runPipeline('extract')">
          🌟 提取
        </a-button>
        <a-dropdown>
          <a-button size="small">➕ 自定义 <i class="fa-solid fa-chevron-down"></i></a-button>
          <template #overlay>
            <a-menu @click="handleCustomPipeline">
              <a-menu-item v-for="p in customPipelines" :key="p.name">
                {{ p.label }}
              </a-menu-item>
              <a-menu-item v-if="customPipelines.length === 0" disabled>
                暂无自定义管线
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <a-divider type="vertical" />
        <a-button size="small" type="primary" ghost @click="handleGenerateNext">
          📄 写下一部分
        </a-button>
        <a-divider type="vertical" />
        <a-dropdown>
          <a-button size="small">更多 <i class="fa-solid fa-chevron-down"></i></a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="handleTokenCount">
                <i class="fa-solid fa-calculator"></i> Token
              </a-menu-item>
              <a-menu-item @click="handleCompare">
                <i class="fa-solid fa-code-compare"></i> 对比
              </a-menu-item>
              <a-menu-item @click="handleFeedback">
                <i class="fa-solid fa-comment"></i> 反馈
              </a-menu-item>
              <a-menu-item @click="handleRevisionLog">
                <i class="fa-solid fa-clock-rotate-left"></i> 修改日志
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item @click="handleBatchGenerate">
                <i class="fa-solid fa-wand-magic-sparkles"></i> 批量生成
              </a-menu-item>
              <a-menu-item @click="handleQualityReview">
                <i class="fa-solid fa-check-circle"></i> 质量审查
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </template>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button as AButton, Space as ASpace, Divider as ADivider, Dropdown as ADropdown, Menu as AMenu, MenuItem as AMenuItem, MenuDivider as AMenuDivider } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'
import { useHistoryStore } from '@/stores/history'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import { useUIStore } from '@/stores/ui'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useProjectStore } from '@/stores/project'
import { usePipelineStore } from '@/stores/pipeline'
import { useTaskStore } from '@/stores/task'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { useWorkflowGuide } from '@/composables/useWorkflowGuide'
import { useMarkdownPreview } from '@/composables/useMarkdownPreview'
import { useTaskQueue, cancelQueuedTask, confirmTask } from '@/composables/useTaskQueue'

const chatStore = useChatStore()
const historyStore = useHistoryStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()
const uiStore = useUIStore()
const rightPanelStore = useRightPanelStore()
const projectStore = useProjectStore()
const pipelineStore = usePipelineStore()
const fileGen = useFileGeneration()
const guide = useWorkflowGuide()
const taskQueue = useTaskQueue()
const { isPreviewMode, togglePreview } = useMarkdownPreview()

const isGenerating = computed(() =>
  chatStore.isStreaming || fileGen.isGenerating.value || taskQueue.isProcessing.value || guide.isRunning.value,
)

const customPipelines = computed(() =>
  pipelineStore.pipelines.filter(p => p.source === 'custom')
)

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

function handleStop() {
  chatStore.cancelStream()
  fileGen.cancelGeneration()
  // 只取消当前正在运行的任务（其余排队任务保留）
  const taskStore = useTaskStore()
  const running = taskStore.tasks.find(t => t.status === 'running')
  if (running) {
    cancelQueuedTask(running.id)
  }
  // 工作流模式：停止当前步骤，等待"写下一部分"继续
  if (guide.isRunning.value) {
    guide.stopAfterCurrent()
    return
  }
  notification.info('已停止当前任务')
}

async function runPipeline(name: string) {
  if (!projectStore.currentProject || !editorStore.currentFilePath) {
    notification.warning('请先打开一个文件')
    return
  }

  rightPanelStore.setPipelineTab('quick')

  const labelMap: Record<string, string> = {
    polish: '润色',
    generate: '生成',
    rewrite: '重写',
    extract: '提取',
  }
  const fileName = editorStore.currentFilePath.split('/').pop() || ''
  const pipelineLabel = labelMap[name] || name

  await taskQueue.enqueue(
    async () => {
      await fileGen.runPipeline(
        projectStore.currentProject!.id,
        editorStore.currentFilePath!,
        name,
      )
    },
    `${pipelineLabel}: ${fileName}`,
  )
}

function handleCustomPipeline(info: any) {
  runPipeline(info.key as string)
}

async function handleGenerateNext() {
  // L1：确认任何等待中的任务
  const taskStore = useTaskStore()
  const waitingTask = taskStore.tasks.find((t: any) => t.status === 'waiting')
  if (waitingTask) {
    confirmTask(waitingTask.id)
    return
  }

  // 工作流暂停时：恢复执行下一步
  if (guide.isPaused.value) {
    const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
    const filePath = editorStore.currentFilePath
    if (projectId && filePath) {
      guide.resume(projectId, filePath)
    }
    return
  }

  if (!projectStore.currentProject) {
    notification.warning('请先打开一个文件')
    return
  }

  // 工作流未启动时启动它
  if (!guide.isRunning.value) {
    const projectId = projectStore.currentProject.id
    const filePath = editorStore.currentFilePath || ''
    await guide.start(projectId, filePath)
    return
  }

  // 工作流已启动但未暂停 —— 不应发生，兜底
  notification.info('工作流已在运行')
}

function handleTokenCount() { uiStore.openTokenCount() }
function handleCompare() { uiStore.openCompare() }
function handleFeedback() { uiStore.openFeedback() }
function handleRevisionLog() { uiStore.openRevisionLog() }
function handleBatchGenerate() { uiStore.openBatchGenerate() }
function handleQualityReview() { uiStore.openQualityReview() }

</script>

<style scoped lang="scss">
.editor-toolbar {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: var(--ink-mid);
  border-bottom: 1px solid var(--border-ink);
  flex-shrink: 0;
  gap: 2px;
}

.editor-toolbar :deep(.ant-btn) {
  color: var(--text-ink);
  background: transparent;
  border: 1px solid var(--border-ink);
  font-size: 12px;
  height: 30px;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover:not(:disabled) {
    color: var(--gold-primary);
    border-color: var(--gold-primary);
    background: rgba(201, 169, 110, 0.06);
  }

  &:disabled {
    color: var(--text-faint);
    opacity: 0.4;
  }

  &.ant-btn-primary {
    color: var(--ink-deepest);
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
    border-color: var(--gold-primary);

    &:hover {
      box-shadow: 0 4px 12px rgba(201, 169, 110, 0.25);
    }
  }

  &.ant-btn-dangerous {
    color: var(--vermillion-light);
    border-color: rgba(192, 57, 43, 0.3);

    &:hover {
      background: rgba(192, 57, 43, 0.1) !important;
      color: var(--vermillion-light) !important;
      border-color: var(--vermillion-light) !important;
    }
  }
}

.editor-toolbar :deep(.ant-divider-vertical) {
  border-color: var(--border-ink);
  height: 18px;
  top: 0;
  margin: 0 4px;
}

.editor-toolbar :deep(.ant-dropdown-trigger) {
  // 自定义管线按钮样式继承 ant-btn
}
</style>
