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
        <a-button size="small" type="primary" ghost @click="runPipeline('generate')">
          📝 生成
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
import { useFileStore } from '@/stores/file'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { useWorkflowGuide } from '@/composables/useWorkflowGuide'
import { useMarkdownPreview } from '@/composables/useMarkdownPreview'
import { useTaskQueue, cancelQueuedTask } from '@/composables/useTaskQueue'

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

function handleGenerateNext() {
  // 工作流暂停时：恢复执行下一步
  if (guide.isPaused.value) {
    const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
    const filePath = editorStore.currentFilePath
    if (projectId && filePath) {
      guide.resume(projectId, filePath)
    }
    return
  }

  if (!projectStore.currentProject || !editorStore.currentFilePath) {
    notification.warning('请先打开一个文件')
    return
  }

  const currentPath = editorStore.currentFilePath
  const dir = currentPath.substring(0, currentPath.lastIndexOf('/') + 1)
  const currentName = currentPath.split('/').pop() || ''

  // 尝试递增文件名中的数字（如 chapter-1.md → chapter-2.md）
  const match = currentName.match(/^(.*?)(\d+)(\.[^.]+)$/)
  let newName: string
  if (match) {
    const prefix = match[1]
    const num = parseInt(match[2], 10)
    const ext = match[3]
    newName = `${prefix}${num + 1}${ext}`
  } else {
    const dotIndex = currentName.lastIndexOf('.')
    const ext = dotIndex >= 0 ? currentName.slice(dotIndex) : ''
    const base = dotIndex >= 0 ? currentName.slice(0, dotIndex) : currentName
    newName = `${base}-2${ext}`
  }

  const newPath = dir + newName
  createAndGenerateFile(newPath)
}

async function createAndGenerateFile(filePath: string) {
  if (!projectStore.currentProject) return

  const fileStore = useFileStore()
  try {
    await fileStore.createFile(projectStore.currentProject.id, filePath, '')

    const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
    fileStore.openFile(node)
    editorStore.setCurrentFile(filePath)

    rightPanelStore.setPipelineTab('quick')

    const fileName = filePath.split('/').pop() || ''
    await taskQueue.enqueue(
      async () => {
        await fileGen.runPipeline(
          projectStore.currentProject!.id,
          filePath,
          'generate',
        )
      },
      `生成新文件: ${fileName}`,
    )

    // 不再需要 setTimeout(500) 从磁盘刷新
    // 生成内容已通过 generationEmitter → useSSE → editorStore.appendContentToFile 实时更新
  } catch (e: any) {
    notification.error('创建文件失败: ' + (e.message || ''))
  }
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
