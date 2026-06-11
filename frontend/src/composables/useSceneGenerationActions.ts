import { computed, ref } from 'vue'
import { Modal } from 'ant-design-vue'
import { useChatStore } from '@/stores/chat'
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
import { useWorkflowGuide, type StepStatus } from '@/composables/useWorkflowGuide'
import { useTaskQueue, cancelQueuedTask } from '@/composables/useTaskQueue'
import { useFileMetaStore } from '@/stores/fileMeta'
import { guessPromptType, getPipelineForFile } from '@/utils/promptTypes'
import { isSceneFile as isSceneFilePath, getNextScenePath, buildScenePath } from '@/modules/scene/scenePath'
import { API_ROUTES, API_BASE } from '@/shared/api/routes'

/** 项目生成链（文件名 → 对应 pipeline） */
const PROJECT_CHAIN: Array<{ path: string; pipeline: string }> = [
  { path: 'style-guide.md', pipeline: 'style-guide' },
  { path: 'blueprint.md', pipeline: 'blueprint' },
  { path: 'outline.md', pipeline: 'outline' },
  { path: 'materials/worldbuilding.md', pipeline: 'worldbuilding' },
  { path: 'characters/main.md', pipeline: 'character' },
]

const GUIDE_STEP_MAP: Record<string, number> = {
  'style-guide.md': 1,
  'blueprint.md': 2,
  'outline.md': 3,
  'worldbuilding.md': 4,
  'characters/main.md': 5,
}

export function useSceneGenerationActions() {
  const chatStore = useChatStore()
  const editorStore = useEditorStore()
  const notification = useNotificationStore()
  const llmStore = useLLMStore()
  const uiStore = useUIStore()
  const rightPanelStore = useRightPanelStore()
  const projectStore = useProjectStore()
  const fileStore = useFileStore()
  const pipelineStore = usePipelineStore()
  const fileGen = useFileGeneration()
  const guide = useWorkflowGuide()
  const taskQueue = useTaskQueue()

  // L2 自动连续生成状态
  const _l2StopRequested = ref(false)
  const _l2AutoRunning = ref(false)
  // @ts-expect-error TS6133 — used in L2 auto chain via closure
  let _chainIndex = -1
  let _nextConfirmQueued: string | null = null

  function getAutoMode(): string {
    try {
      return localStorage.getItem('moyun-auto-mode') || 'L1'
    } catch {
      return 'L1'
    }
  }

  function getNextInChain(currentPath: string): { path: string; pipeline: string } | null {
    if (isSceneFilePath(currentPath)) {
      _chainIndex = -1
      const nextPath = getNextScenePath(currentPath)
      if (nextPath) return { path: nextPath, pipeline: 'generate' }
      return null
    }
    const idx = PROJECT_CHAIN.findIndex(item => currentPath.endsWith(item.path))
    if (idx >= 0 && idx < PROJECT_CHAIN.length - 1) {
      _chainIndex = idx + 1
      return PROJECT_CHAIN[idx + 1]
    }
    if (idx === PROJECT_CHAIN.length - 1) {
      _chainIndex = -1
      return { path: buildScenePath(1, 1, 1), pipeline: 'generate' }
    }
    if (!isSceneFilePath(currentPath) && !PROJECT_CHAIN.some(i => currentPath.endsWith(i.path))) {
      _chainIndex = 0
      return PROJECT_CHAIN[0]
    }
    return null
  }

  const isGenerating = computed(() =>
    chatStore.isStreaming || fileGen.isGenerating.value || taskQueue.isProcessing.value || guide.isRunning.value,
  )

  const showStopButton = computed(() =>
    isGenerating.value || _l2AutoRunning.value
  )

  const showNextButton = computed(() => {
    const path = editorStore.currentFilePath || ''
    const isSystemFile = /style-guide\.md$|story-state\.md$|recent-context\.md$|\.json$/.test(path)
    return !isSystemFile && !!projectStore.currentProject
  })

  function syncGuideStep(path: string, status: 'running' | 'done') {
    if (isSceneFilePath(path)) {
      if (guide.steps.value[6]) guide.steps.value[6].status = status as StepStatus
      if (status === 'running') {
        for (let i = 0; i < 6; i++) {
          if (guide.steps.value[i]) guide.steps.value[i].status = 'done' as StepStatus
        }
      }
      return
    }
    for (const [key, idx] of Object.entries(GUIDE_STEP_MAP)) {
      if (path.endsWith(key) && guide.steps.value[idx]) {
        guide.steps.value[idx].status = status as StepStatus
        if (status === 'running') {
          for (let i = 0; i < idx; i++) {
            if (guide.steps.value[i]) guide.steps.value[i].status = 'done' as StepStatus
          }
        }
        return
      }
    }
  }

  async function loadFilePrompt(projectId: string, filePath: string) {
    const pipelineName = getPipelineForFile(filePath)
    if (pipelineName) {
      try {
        await pipelineStore.fetchPipelineDetail(pipelineName)
        const step = pipelineStore.currentDetail?.steps?.[0]
        if (step?.prompt_content) {
          editorStore.setFilePrompt(filePath, step.prompt_content)
          rightPanelStore.updatePrompt(step.prompt_content)
          return
        }
      } catch {
        // fallback to guessPromptType
      }
    }
    const promptType = guessPromptType(filePath)
    if (promptType) {
      fetch(API_BASE + API_ROUTES.prompts(promptType) + `?project_id=${projectId}`)
        .then(r => r.json())
        .then(json => {
          if (json?.data?.content) {
            editorStore.setFilePrompt(filePath, json.data.content)
            rightPanelStore.updatePrompt(json.data.content)
          }
        })
        .catch((err: unknown) => { console.error('Prompt 加载失败:', err instanceof Error ? err.message : err) })
    }
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

      // 提前读取右侧面板中用户手工修改的 prompt（queue check 和正常流程都需要）
      const customPrompt = rightPanelStore.promptContent
      const extraVars: Record<string, unknown> = {}
      if (customPrompt && customPrompt.length > 50) {
        extraVars.user_prompt = customPrompt
      }
      const currentContent = editorStore.getContent(filePath)
      if (currentContent && currentContent.trim().length > 0) {
        extraVars.previous_text = currentContent
        extraVars.current_scene_text = currentContent
      }

      // L1 auto-advance 已打开但未生成的文件 → 本次点击触发生成
      if (_nextConfirmQueued) {
        const queued = _nextConfirmQueued
        _nextConfirmQueued = null
        if (queued === filePath) {
          const chainItem = PROJECT_CHAIN.find(item => item.path === filePath)
          if (chainItem) {
            loadFilePrompt(projectId, filePath)
            syncGuideStep(filePath, 'running')
            await fileGen.runPipeline(projectId, filePath, chainItem.pipeline, extraVars, 'write_scene')
            syncGuideStep(filePath, 'done')
          }
          return
        }
      }

      // 从当前文件路径推导下一个文件和 pipeline
      const next = getNextInChain(filePath)
      if (!next) {
        notification.warning('已无下一个可生成的文件')
        return
      }

      // 所有场景文件统一走 candidate 流程，不直接覆盖正文；项目素材文件（outline/blueprint 等）可直接写入
      const isSceneFile = /chapters[\\/]vol-\d+[\\/]ch-\d+[\\/]sec-\d+\.md$/.test(next.path)
      const nextOutputMode: 'candidate' | 'write_scene' = isSceneFile ? 'candidate' : 'write_scene'
      if (isSceneFile) {
        rightPanelStore.setActiveTab('candidate')
      }

      // 检查管线的 confirm 标记（第一步是否需用户确认）
      await pipelineStore.fetchPipelineDetail(next.pipeline)
      const needConfirm = pipelineStore.currentDetail?.steps?.[0]?.confirm !== false

      if (needConfirm) {
        // confirm=true：打开文件到编辑器供流式输出
        const node = { name: next.path.split('/').pop() || '', path: next.path, type: 'file' as const }
        fileStore.openFile(node)
        editorStore.setCurrentFile(next.path)

        // 加载新文件的 prompt 到右侧面板
        loadFilePrompt(projectId, next.path)
      }

      // 同步更新 workflow guide 步骤状态
      syncGuideStep(next.path, 'running')

      // 运行对应 pipeline（场景文件强制走 candidate 模式，禁止直接覆盖正文）
      await fileGen.runPipeline(projectId, next.path, next.pipeline, extraVars, nextOutputMode)

      // pipeline 完成 → 更新 guide 步骤状态为 done
      syncGuideStep(next.path, 'done')

      // confirm=false：后台静默完成，自动继续下一步
      if (!needConfirm) {
        // 用 _chainIndex 直接推进到链中下一项（不依赖 editorStore.currentFilePath）
        const nextIdx = PROJECT_CHAIN.findIndex(item => item.path === next.path)
        if (nextIdx >= 0 && nextIdx < PROJECT_CHAIN.length - 1) {
          const nextNext = PROJECT_CHAIN[nextIdx + 1]
          // 打开下一文件（confirm=true 的正常流程）
          const node2 = { name: nextNext.path.split('/').pop() || '', path: nextNext.path, type: 'file' as const }
          fileStore.openFile(node2)
          editorStore.setCurrentFile(nextNext.path)
          loadFilePrompt(projectId, nextNext.path)

          if (getAutoMode() === 'L1') {
            // L1: 打开文件但不运行 pipeline，标记为排队等待用户确认
            _nextConfirmQueued = nextNext.path
            notification.info(`已打开 ${nextNext.path}，点击「写下一场景」开始生成`)
            return
          }

          // L2: 运行 pipeline 后继续推进
          syncGuideStep(nextNext.path, 'running')
          await fileGen.runPipeline(projectId, nextNext.path, nextNext.pipeline, extraVars, 'write_scene')
          syncGuideStep(nextNext.path, 'done')
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
          // L1: 不继续（已在上面 return）
        }
        return
      }

      // L2: 完成后自动推进下一场景
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
    } catch (e: unknown) {
      // L2 取消时不弹错误
      if (getAutoMode() === 'L2' && _l2StopRequested.value) {
        _l2StopRequested.value = false
        _l2AutoRunning.value = false
        notification.info('已停止自动生成')
        return
      }
      console.error('[ERR] handleGenerateNext:', e instanceof Error ? e.message : String(e))
    }
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
    const candidateOnly = name === 'polish' || name === 'rewrite'
    if (candidateOnly) {
      rightPanelStore.setActiveTab('candidate')
    }

    // 提取管线输出到 materials/extracted/，不覆盖当前场景
    const filePath = editorStore.currentFilePath!
    const targetFile = name === 'extract'
      ? `materials/extracted/${filePath.replace(/^.*?chapters\//, '').replace(/\//g, '-')}`
      : filePath

    const labelMap: Record<string, string> = {
      polish: '润色',
      generate: '生成',
      rewrite: '精修',
      extract: '提取',
    }
    const fileName = filePath.split('/').pop() || ''
    const pipelineLabel = labelMap[name] || name

    await taskQueue.enqueue(
      async () => {
        await fileGen.runPipeline(
          projectStore.currentProject!.id,
          targetFile,
          name,
          undefined,
          candidateOnly ? 'candidate' : name === 'extract' ? 'write_scene' : 'write_scene',
        )
        if (candidateOnly) {
          notification.success('已生成候选稿，采用后才会覆盖当前场景。')
        }
      },
      `${pipelineLabel}: ${fileName}`,
    )
  }

  function handleCustomPipeline(info: { key: string | number }) {
    runPipeline(String(info.key))
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
      extraVars = promptType === 'generate/title' && projectStore.currentProject
        ? {
            genre: projectStore.currentProject.genre || '',
            tone: projectStore.currentProject.tone || '',
            theme: projectStore.currentProject.theme || '',
            setting: projectStore.currentProject.background || '',
            writing_style: projectStore.currentProject.writing_style || '',
          }
        : {}
    }

    if (/书名与创意\.md$/i.test(filePath) && projectStore.currentProject) {
      promptType = 'generate/title'
      extraVars = {
        ...extraVars,
        genre: projectStore.currentProject.genre || extraVars.genre || '',
        tone: projectStore.currentProject.tone || extraVars.tone || '',
        theme: projectStore.currentProject.theme || extraVars.theme || '',
        setting: projectStore.currentProject.background || extraVars.setting || '',
        writing_style: projectStore.currentProject.writing_style || extraVars.writing_style || '',
      }
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
      const pipelineName = getPipelineForFile(filePath)
      if (pipelineName && pipelineName !== 'title') {
        const pipelineExtraVars: Record<string, unknown> = { ...extraVars }
        if (userPrompt) {
          pipelineExtraVars.user_prompt = userPrompt
        }
        await fileGen.runPipeline(projectId, filePath, pipelineName, pipelineExtraVars, 'write_scene')
      } else {
        await fileGen.generateToFile(projectId, filePath, userPrompt, extraVars, promptType)
      }
      notification.success('已重新生成')
    } catch (e: unknown) {
      notification.error((e instanceof Error ? e.message : '') || '重新生成失败')
    }
  }

  function handleStop() {
    // 清除任何 L1 排队中的文件
    _nextConfirmQueued = null

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

    // 只取消当前正在运行的任务（其余排队任务保留）
    const running = taskStore.tasks.find(t => t.status === 'running')
    if (running) {
      cancelQueuedTask(running.id)
    }
    // 工作流模式：停止当前步骤，等待"写下一场景"继续
    if (guide.isRunning.value) {
      guide.stopAfterCurrent()
      notification.info('已停止当前步骤，点"写下一场景"继续')
      return
    }
    // 强制重置任务队列处理状态（防止 pipeline 异常断开后卡死）
    taskQueue.isProcessing.value = false
    notification.info('已停止当前任务')
  }

  /**
   * 统一场景动作入口：所有场景生成/修改操作都经过此函数。
   * action 决定语义和策略：
   *   write_next_scene    → 写入下一个场景（目标不存在或为空时直接写入，已有内容时生成候选稿）
   *   write_current_scene → 生成当前场景（目标为空时直接写入，已有内容时生成候选稿）
   *   rewrite_current_scene → 重写当前场景（必须候选稿）
   *   polish_current_scene  → 润色当前场景（必须候选稿）
   */
  async function runSceneAction(params: {
    action: 'write_next_scene' | 'write_current_scene' | 'rewrite_current_scene' | 'polish_current_scene'
    sourcePath: string
    targetPath: string
    projectId: string
    extraVars?: Record<string, unknown>
  }) {
    const { action, sourcePath, targetPath, projectId, extraVars = {} } = params

    // 读取当前场景正文作为 continuity source，确保后端能提取锚点并检测连续性。
    // 必须在打开 targetPath 之前读取，否则编辑器切换到目标文件后 sourcePath 内容可能不可取。
    const currentContent = editorStore.getContent(sourcePath)
    if (currentContent && currentContent.trim().length > 0) {
      extraVars.previous_text = currentContent
      extraVars.current_scene_text = currentContent
    }

    // 所有场景生成动作统一走 candidate 流程，不直接覆盖正文。
    // pipelineName 保持区分（polish/rewrite/generate），但 outputMode 统一为 candidate。
    const pipelineName = action === 'polish_current_scene'
      ? 'polish'
      : action === 'rewrite_current_scene'
        ? 'rewrite'
        : 'generate'
    const outputMode: 'candidate' = 'candidate'

    // 生成完成后切换到候选稿面板，让用户明确知道"待采纳"
    rightPanelStore.setActiveTab('candidate')

    // 打开目标文件到编辑器
    const node = { name: targetPath.split('/').pop() || '', path: targetPath, type: 'file' as const }
    fileStore.openFile(node)
    editorStore.setCurrentFile(targetPath)

    // 加载 prompt
    loadFilePrompt(projectId, targetPath)

    // 同步 guide 步骤
    syncGuideStep(targetPath, 'running')

    // 执行 pipeline，传入 action 供后端识别
    await fileGen.runPipeline(
      projectId,
      targetPath,
      pipelineName,
      { ...extraVars, _action: action },
      outputMode,
    )

    syncGuideStep(targetPath, 'done')

    // 所有结果均为候选稿
    notification.success('已生成候选稿，采用后才会覆盖当前场景。')
  }

  /** 写下一场景：推导下一个 sec 文件并生成 */
  async function writeNextScene() {
    if (!llmStore.isConnected) {
      notification.warning('请先配置 LLM 连接')
      uiStore.openSettings()
      return
    }
    const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
    const filePath = editorStore.currentFilePath
    if (!projectId || !filePath) {
      notification.warning('请先打开一个文件')
      return
    }

    const customPrompt = rightPanelStore.promptContent
    const extraVars: Record<string, unknown> = {}
    if (customPrompt && customPrompt.length > 50) {
      extraVars.user_prompt = customPrompt
    }

    const next = getNextInChain(filePath)
    if (!next) {
      notification.warning('已无下一个可生成的文件')
      return
    }

    await runSceneAction({
      action: 'write_next_scene',
      sourcePath: filePath,
      targetPath: next.path,
      projectId,
      extraVars,
    })
  }

  /** 生成当前场景：当前 sec 为空时直接写入，已有内容时生成候选稿 */
  async function writeCurrentScene() {
    if (!llmStore.isConnected) {
      notification.warning('请先配置 LLM 连接')
      uiStore.openSettings()
      return
    }
    const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
    const filePath = editorStore.currentFilePath
    if (!projectId || !filePath) {
      notification.warning('请先打开一个文件')
      return
    }

    const customPrompt = rightPanelStore.promptContent
    const extraVars: Record<string, unknown> = {}
    if (customPrompt && customPrompt.length > 50) {
      extraVars.user_prompt = customPrompt
    }

    await runSceneAction({
      action: 'write_current_scene',
      sourcePath: filePath,
      targetPath: filePath,
      projectId,
      extraVars,
    })
  }

  /** 重写当前场景：必须生成候选稿，不直接覆盖 */
  async function rewriteCurrentScene() {
    if (!llmStore.isConnected) {
      notification.warning('请先配置 LLM 连接')
      uiStore.openSettings()
      return
    }
    const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
    const filePath = editorStore.currentFilePath
    if (!projectId || !filePath) {
      notification.warning('请先打开一个文件')
      return
    }

    await runSceneAction({
      action: 'rewrite_current_scene',
      sourcePath: filePath,
      targetPath: filePath,
      projectId,
    })
  }

  /** 润色当前场景：必须生成候选稿，不直接覆盖 */
  async function polishCurrentScene() {
    if (!llmStore.isConnected) {
      notification.warning('请先配置 LLM 连接')
      uiStore.openSettings()
      return
    }
    const projectId = projectStore.currentProject?.id || projectStore.currentProject?.project_id
    const filePath = editorStore.currentFilePath
    if (!projectId || !filePath) {
      notification.warning('请先打开一个文件')
      return
    }

    await runSceneAction({
      action: 'polish_current_scene',
      sourcePath: filePath,
      targetPath: filePath,
      projectId,
    })
  }

  return {
    isGenerating,
    showStopButton,
    showNextButton,
    handleGenerateNext,
    runPipeline,
    handleCustomPipeline,
    handleRegenerate,
    handleStop,
    // 统一动作入口
    runSceneAction,
    writeNextScene,
    writeCurrentScene,
    rewriteCurrentScene,
    polishCurrentScene,
  }
}
