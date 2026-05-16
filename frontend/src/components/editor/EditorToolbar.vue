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
      <a-button v-if="showStopButton" danger size="small" @click="handleStop">
        <template #icon><i class="fa-solid fa-stop"></i></template>
        停止
      </a-button>
      <a-button v-if="showNextButton" size="small" type="primary" @click="handleGenerateNext">
        📄 写下一部分
      </a-button>
      <template v-if="!isGenerating">
        <a-button v-if="isChapterFile" size="small" type="primary" ghost @click="runPipeline('polish')">
          ✏️ 润色
        </a-button>
        <a-button v-if="isChapterFile" size="small" type="primary" ghost @click="runPipeline('rewrite')">
          📦 精修
        </a-button>
        <a-button v-if="isChapterFile" size="small" type="primary" ghost @click="runPipeline('extract')">
          🌟 提取
        </a-button>
        <a-divider v-if="isChapterFile" type="vertical" />
        <a-button v-if="!isSystemFile" size="small" @click="handleRegenerate" title="用原参数重新生成">
          🔄 重新生成
        </a-button>
        <a-dropdown v-if="!isSystemFile">
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
        <a-divider v-if="!isSystemFile" type="vertical" />
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
import { computed, ref } from 'vue'
import { Button as AButton, Space as ASpace, Divider as ADivider, Dropdown as ADropdown, Menu as AMenu, MenuItem as AMenuItem, MenuDivider as AMenuDivider, Modal } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'
import { useHistoryStore } from '@/stores/history'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import { useLLMStore } from '@/stores/llm'
import { useUIStore } from '@/stores/ui'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { usePipelineStore } from '@/stores/pipeline'
import { useTaskStore } from '@/stores/task'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { useWorkflowGuide } from '@/composables/useWorkflowGuide'
import { useMarkdownPreview } from '@/composables/useMarkdownPreview'
import { useTaskQueue, cancelQueuedTask } from '@/composables/useTaskQueue'
import { useFileMetaStore } from '@/stores/fileMeta'
import { guessPromptType } from '@/utils/promptTypes'

const chatStore = useChatStore()
const historyStore = useHistoryStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()
const llmStore = useLLMStore()
const uiStore = useUIStore()
const rightPanelStore = useRightPanelStore()
const projectStore = useProjectStore()
const pipelineStore = usePipelineStore()
const fileGen = useFileGeneration()
const guide = useWorkflowGuide()
const taskQueue = useTaskQueue()
const { isPreviewMode, togglePreview } = useMarkdownPreview()

// L2 自动连续生成状态
const _l2StopRequested = ref(false)
const _l2AutoRunning = ref(false)

function getAutoMode(): string {
  return localStorage.getItem('moyun-auto-mode') || 'L1'
}

/** 项目生成链（文件名 → 对应 pipeline） */
const PROJECT_CHAIN: Array<{ path: string; pipeline: string }> = [
  { path: 'blueprint.md', pipeline: 'blueprint' },
  { path: 'outline.md', pipeline: 'outline' },
  { path: 'materials/worldbuilding.md', pipeline: 'worldbuilding' },
  { path: 'characters/main.md', pipeline: 'character' },
]

/** 根据当前文件路径推导下一个文件和 pipeline */
function getNextInChain(currentPath: string): { path: string; pipeline: string } | null {
  // 章节文件（sec-NNN.md）→ 用已有的 getNextSectionPath + generate pipeline
  const secMatch = currentPath.match(/^(.*\/)(sec-)(\d+)(\.md)$/)
  if (secMatch) {
    const nextPath = getNextSectionPath(currentPath)
    if (nextPath) return { path: nextPath, pipeline: 'generate' }
    return null
  }

  // 在项目链中 → 找下一个
  const idx = PROJECT_CHAIN.findIndex(item => currentPath.endsWith(item.path))
  if (idx >= 0 && idx < PROJECT_CHAIN.length - 1) {
    return PROJECT_CHAIN[idx + 1]
  }

  // 在链中且是最后一项 → 过渡到第一章
  if (idx === PROJECT_CHAIN.length - 1) {
    return { path: 'chapters/vol-01/ch-001/sec-001.md', pipeline: 'generate' }
  }

  // 不在链中也不是章节 → 从链头开始
  if (!secMatch && !PROJECT_CHAIN.some(i => currentPath.endsWith(i.path))) {
    return PROJECT_CHAIN[0]
  }

  return null
}

const isGenerating = computed(() =>
  chatStore.isStreaming || fileGen.isGenerating.value || taskQueue.isProcessing.value || guide.isRunning.value,
)

/** 有任务在等待 L1 确认，或者工作流已暂停 */
const isWaitingForConfirm = computed(() => {
  return guide.isPaused.value || useTaskStore().tasks.some(t => t.status === 'waiting')
})

/** 显示停止按钮：正在流式输出、管线执行中、或 L2 自动推进中 */
const showStopButton = computed(() =>
  isGenerating.value || _l2AutoRunning.value
)

/** 显示"写下一部分"：有项目打开且非系统文件时始终可见 */
const showNextButton = computed(() =>
  !isSystemFile.value && !!projectStore.currentProject
)

const customPipelines = computed(() =>
  pipelineStore.pipelines.filter(p => p.source === 'custom')
)

/** 当前文件是否为正文章节（sec-*.md） */
const isChapterFile = computed(() => {
  const path = editorStore.currentFilePath || ''
  return /\/sec-\d+\.md$/.test(path)
})

/** 当前文件是否为系统维护文件（不应触发任何生成操作） */
const isSystemFile = computed(() => {
  const path = editorStore.currentFilePath || ''
  return /style-guide\.md$|story-state\.md$|recent-context\.md$|\.json$/.test(path)
})

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
  // L2 自动推进中 → 标记停止，当前文件生成完毕后停
  if (getAutoMode() === 'L2' && (_l2AutoRunning.value || fileGen.isGenerating.value)) {
    _l2StopRequested.value = true
    fileGen.cancelGeneration()
    notification.info('将在当前步骤完成后停止')
    return
  }

  chatStore.cancelStream()
  fileGen.cancelGeneration()

  const taskStore = useTaskStore()

  // L1 等待中 + 工作流运行中 -> 等效于确认当前任务并继续
  const waitingTask = taskStore.tasks.find(t => t.status === 'waiting')
  if (waitingTask && guide.isRunning.value) {
    handleGenerateNext()
    return
  }

  // 只取消当前正在运行的任务（其余排队任务保留）
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
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    uiStore.openSettings()
    return
  }

  rightPanelStore.setPipelineTab('quick')

  const labelMap: Record<string, string> = {
    polish: '润色',
    generate: '生成',
    rewrite: '精修',
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
  try {
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    uiStore.openSettings()
    return
  }

  // 停止可能仍在运行的工作流引导，避免并发冲突
  if (guide.isRunning.value) {
    guide.stopNow()
  }

  const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
  const filePath = editorStore.currentFilePath
  if (!projectId || !filePath) {
    notification.warning('请先打开一个文件')
    return
  }

  // 从当前文件路径推导下一个文件和 pipeline
  const next = getNextInChain(filePath)
  if (!next) {
    notification.warning('已无下一个可生成的文件')
    return
  }

  // 打开下一个文件
  const fileStore = useFileStore()
  const node = { name: next.path.split('/').pop() || '', path: next.path, type: 'file' as const }
  fileStore.openFile(node)
  editorStore.setCurrentFile(next.path)

  // 同步更新 workflow guide 步骤状态
  syncGuideStep(next.path, 'running')

  // 运行对应 pipeline
  await fileGen.runPipeline(projectId, next.path, next.pipeline)

  // pipeline 完成 → 更新 guide 步骤状态为 done
  syncGuideStep(next.path, 'done')

  // L2: 完成后自动推进下一节
  if (getAutoMode() === 'L2') {
    if (_l2StopRequested.value) {
      _l2StopRequested.value = false
      _l2AutoRunning.value = false
      notification.info('已停止自动生成')
    } else {
      _l2AutoRunning.value = true
      setTimeout(() => handleGenerateNext(), 800)
    }
  }
  } catch (e: any) {
    // L2 取消时不弹错误
    if (getAutoMode() === 'L2' && _l2StopRequested.value) {
      _l2StopRequested.value = false
      _l2AutoRunning.value = false
      notification.info('已停止自动生成')
      return
    }
    console.error('[ERR] handleGenerateNext:', e.message || e)
  }
}

/** 根据当前生成的路径，更新 workflow guide 对应步骤的状态 */
const GUIDE_STEP_MAP: Record<string, number> = {
  'blueprint.md': 0,
  'outline.md': 1,
  'worldbuilding.md': 2,
  'characters/main.md': 3,
}

function syncGuideStep(path: string, status: 'running' | 'done') {
  if (path.match(/sec-\d+\.md$/)) {
    if (guide.steps.value[4]) guide.steps.value[4].status = status as any
    return
  }
  for (const [key, idx] of Object.entries(GUIDE_STEP_MAP)) {
    if (path.endsWith(key) && guide.steps.value[idx]) {
      guide.steps.value[idx].status = status as any
      return
    }
  }
}

/** 从当前文件路径推导下一个章节文件路径 */
function getNextSectionPath(currentPath: string): string | null {
  // 匹配 chapters/vol-NN/ch-NNN/sec-NNN.md
  const match = currentPath.match(/^(.*\/)(sec-)(\d+)(\.md)$/)
  if (!match) return null
  const [, prefix, base, num, ext] = match
  const secNum = Number(num)

  // 从项目目标字数计算章节参数（与 expandLoopStep 算法一致）
  const projectStore = useProjectStore()
  const tgt = projectStore.currentProject?.target_word_count || 50000
  const sections = Math.max(1, Math.floor(tgt / 1800))
  const SECTIONS_PER_CHAPTER = 4
  const CHAPTERS_PER_VOLUME = Math.ceil(sections / 4)

  // 如果当前 section < 每章上限，直接递增
  if (secNum < SECTIONS_PER_CHAPTER) {
    const nextNum = String(secNum + 1).padStart(num.length, '0')
    return `${prefix}${base}${nextNum}${ext}`
  }

  // 已达到章节上限，尝试进入下一章
  const chMatch = prefix.match(/^(.*\/ch-)(\d+)(\/)$/)
  if (!chMatch) return null
  const [, chPrefix, chNum, chSuffix] = chMatch
  const ch = Number(chNum)

  if (ch < CHAPTERS_PER_VOLUME) {
    // 同一卷内下一章
    const nextCh = String(ch + 1).padStart(chNum.length, '0')
    return `${chPrefix}${nextCh}${chSuffix}sec-001.md`
  }

  // 已到卷末，进入下一卷
  const volMatch = chPrefix.match(/^(.*\/vol-)(\d+)(\/)$/)
  if (!volMatch) return null
  const [, volPrefix, volNum, volSuffix] = volMatch
  const nextVol = String(Number(volNum) + 1).padStart(volNum.length, '0')
  return `${volPrefix}${nextVol}${volSuffix}ch-001/sec-001.md`
}

async function handleRegenerate() {
  const filePath = editorStore.currentFilePath
  const projectId = projectStore.currentProject?.id
  if (!filePath || !projectId) {
    notification.warning('请先打开一个文件')
    return
  }
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    uiStore.openSettings()
    return
  }

  // 1. 查找已保存的生成元数据
  const meta = useFileMetaStore().getMeta(projectId, filePath)

  let promptType: string
  let extraVars: Record<string, string>

  if (meta) {
    promptType = meta.promptType
    extraVars = { ...meta.extraVars }
  } else {
    // 无元数据时从文件路径推测
    const guessed = guessPromptType(filePath)
    if (!guessed) {
      notification.warning('无法确定该文件的生成方式')
      return
    }
    promptType = guessed
    extraVars = {}
  }

  // 2. 确认覆盖
  const confirmed = await new Promise<boolean>((resolve) => {
    Modal.confirm({
      title: '重新生成',
      content: `将清空 "${filePath.split('/').pop()}" 的内容并重新生成，确定吗？`,
      okText: '确定',
      cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
  if (!confirmed) return

  // 3. 清空文件
  editorStore.loadContent(filePath, '')
  try {
    await fileStore.saveFile(projectId, filePath, '')
  } catch {
    notification.error('清空文件失败')
    return
  }

  // 4. 重新生成（user_prompt 已在 extraVars 中）
  const userPrompt = extraVars.user_prompt || ''
  delete extraVars.user_prompt
  try {
    await fileGen.generateToFile(projectId, filePath, userPrompt, extraVars, promptType)
    notification.success('已重新生成')
  } catch (e: any) {
    notification.error(e.message || '重新生成失败')
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
