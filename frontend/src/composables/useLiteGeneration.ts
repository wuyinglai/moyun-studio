import { ref, type Ref } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore, type FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import {
  createLiteProject,
  fetchLiteIdeas,
  fetchLiteNextOptions,
  streamLiteNext,
  type LiteIdeaCard,
  type LiteWriteAction,
  type LiteNextOptionCard,
  type LiteWritingPrefs,
} from '@/services/liteService'
import { consumeOrFetch } from '@/composables/useLitePrefetch'

type FlowRunUpdater = {
  startLiteWriteFlow: (payload: { sourcePath?: string; targetPath?: string; isCandidate?: boolean }) => void
  markNodeRunning: (nodeId: string) => void
  markNodeSuccess: (nodeId: string, outputs?: any[]) => void
  markNodeError: (nodeId: string, error: string) => void
  markNodeSkipped: (nodeId: string) => void
  resetFlow: () => void
}

export function useLiteGeneration(deps: {
  content: Ref<string>
  currentFilePath: Ref<string>
  chapterStatus: Ref<Record<string, 'done' | 'blank' | 'draft'>>
  textareaRef: Ref<HTMLTextAreaElement | null>
  scrollTextareaToBottom: () => Promise<void>
  dirty: Ref<boolean>
  prefs: LiteWritingPrefs
  chapterFiles: Ref<FileNode[]>
  openChapter: (path: string, options?: { skipOptions?: boolean }) => Promise<void>
  flow?: FlowRunUpdater
}) {
  const projectStore = useProjectStore()
  const fileStore = useFileStore()
  const editorStore = useEditorStore()
  const notification = useNotificationStore()

  // Generation state
  const generating = ref(false)
  const generationAbortController = ref<AbortController | null>(null)
  const lastGenerationCard = ref<LiteNextOptionCard | null>(null)
  const autoScrollDuringGeneration = ref(true)
  const streamingFilePath = ref('')
  const streamingBuffers = ref<Record<string, string>>({})
  const pendingTargetLabel = ref('')
  const qualitySummary = ref('')
  const engineSummary = ref<Record<string, string>>({})
  const chapterMilestone = ref<{ vol: number; ch: number; summary: string; nextGoal: string } | null>(null)
  const loadingOptions = ref(false)
  const optionError = ref('')
  const optionRequestId = ref(0)
  const workPhase = ref('')
  const workDetail = ref('')
  const nextCards = ref<LiteNextOptionCard[]>([])
  const nextTargetFile = ref('')
  const ideaCards = ref<LiteIdeaCard[]>([])
  const loadingIdeas = ref(false)
  const creating = ref(false)

  // Helper functions
  function setWorkStatus(title: string, detail: string) {
    workPhase.value = title
    workDetail.value = detail
  }

  function clearWorkStatus() {
    workPhase.value = ''
    workDetail.value = ''
  }

  function isAbortError(e: unknown) {
    return e instanceof DOMException && e.name === 'AbortError'
  }

  function appendDraftContent(base: string, addition: string) {
    if (!base.trim()) return addition
    if (!addition.trim()) return base
    return `${base.replace(/\s+$/, '')}\n\n${addition.replace(/^\s+/, '')}`
  }

  function stripLeadingMarkdownHeading(text: string) {
    return text.replace(/^\s*#{1,6}\s+[^\n\r]*(\r?\n)+/, '')
  }

  function extractNextChapterGoal(plan: string | null | undefined) {
    const fallback = '下一章会把本章留下的压力继续推高。'
    if (!plan) return fallback
    const line = plan
      .split(/\r?\n/)
      .map(item => item.replace(/^#+\s*/, '').replace(/^[-*]\s*/, '').trim())
      .find(item => item && !item.includes('章规划格式'))
    return line ? line.slice(0, 80) : fallback
  }

  function parseSectionPath(path: string) {
    const vol = Number(path.match(/vol-(\d+)/)?.[1] || 0)
    const ch = Number(path.match(/ch-(\d+)/)?.[1] || 0)
    const sec = Number(path.match(/sec-(\d+)/)?.[1] || 0)
    return { vol, ch, sec }
  }

  function formatChapterLabel(path: string) {
    const vol = path.match(/vol-(\d+)/)?.[1]
    const ch = path.match(/ch-(\d+)/)?.[1]
    const sec = path.match(/sec-(\d+)/)?.[1]
    if (!vol && !ch && !sec) return path.split('/').pop()?.replace('.md', '') || path
    const parts = []
    if (vol) parts.push(`第${Number(vol)}卷`)
    if (ch) parts.push(`第${Number(ch)}章`)
    if (sec) parts.push(`第${Number(sec)}场景`)
    return parts.join(' ')
  }

  function isChapterStart(path: string) {
    return parseSectionPath(path).sec === 1
  }

  function buildChapterMilestone(result: { file_path: string; chapter_plan?: string | null }, card: LiteNextOptionCard) {
    const { vol, ch } = parseSectionPath(result.file_path)
    if (!vol || !ch) return null
    return {
      vol,
      ch,
      summary: `第${ch}章完成：${card.title}，${card.payoff}`,
      nextGoal: `下一章目标：${extractNextChapterGoal(result.chapter_plan)}`,
    }
  }

  function isBlankChapter(text: string) {
    const body = text
      .split('\n')
      .map(line => line.trim())
      .filter(line => line && !line.startsWith('#'))
      .join('')
    return body.length < 20
  }

  function normalizeChapterHeading(path: string, text: string) {
    const lines = text.split(/\r?\n/)
    const first = lines[0] || ''
    if (!first.trim().startsWith('#')) return text
    const expectedPrefix = `# ${formatChapterLabel(path)}`
    if (first.startsWith(expectedPrefix)) return text
    const title = first
      .replace(/^#+\s*/, '')
      .replace(/第\d+卷/g, '')
      .replace(/第\d+章/g, '')
      .replace(/第\d+场景/g, '')
      .replace(/第\d+节/g, '')
      .replace(/\s*-\s*/g, ' ')
      .trim() || projectStore.currentProject?.name || ''
    lines[0] = title ? `${expectedPrefix} ${title}` : expectedPrefix
    return lines.join('\n')
  }

  function candidateActionText(action: LiteWriteAction) {
    if (action === 'rewrite') return '重写当前场景'
    if (action === 'more_exciting') return '让当前场景更爽'
    if (action === 'more_reasonable') return '让当前场景更合理'
    return '候选稿'
  }

  // Core generation
  async function runGeneration(
    card: LiteNextOptionCard,
    action: LiteWriteAction,
    targetFile: string | null,
    outputFile: string | null = null,
    candidateDraft: Ref<{ sourcePath: string; path: string; action: LiteWriteAction; title: string; content: string; candidateId?: string | null } | null>,
  ) {
    const projectId = projectStore.currentProject?.id
    if (!projectId || generating.value) return
    let isCandidate = Boolean(outputFile && outputFile !== targetFile)
    const candidateLabel = candidateActionText(action)
    const sourcePath = targetFile || nextTargetFile.value || deps.currentFilePath.value || ''
    generating.value = true
    const abortController = new AbortController()
    generationAbortController.value = abortController
    lastGenerationCard.value = card
    autoScrollDuringGeneration.value = true
    let generatedFilePath = outputFile || sourcePath
    let streamHeadingPrefix = ''
    const continueBaseContent = action === 'continue' && generatedFilePath ? (streamingBuffers.value[generatedFilePath] || deps.content.value) : ''
    pendingTargetLabel.value = formatChapterLabel(sourcePath)
    setWorkStatus(
      isCandidate ? `正在生成${candidateLabel}候选稿` : `正在写${pendingTargetLabel.value}`,
      isCandidate ? '正在准备当前场景、用户要求和故事状态，候选稿不会覆盖原文。' : '正在准备前文、故事引擎、近期上下文和本场景爽点卡。',
    )
    qualitySummary.value = isCandidate
      ? `正在生成${candidateActionText(action)}候选稿，原文不会被覆盖。`
      : `正在写${pendingTargetLabel.value}，已生成的内容会自动保留。`

    // 启动流程可视化
    if (deps.flow) {
      deps.flow.startLiteWriteFlow({
        sourcePath,
        targetPath: nextTargetFile.value,
        isCandidate,
      })
    }

    try {
      await streamLiteNext(projectId, targetFile || nextTargetFile.value || deps.currentFilePath.value || null, card, deps.prefs, action, {
        onMeta: (meta) => {
          isCandidate = Boolean(meta.is_candidate)
          generatedFilePath = meta.file_path
          streamingFilePath.value = meta.file_path
          const displayPath = meta.source_file || meta.file_path
          setWorkStatus(
            meta.is_candidate ? `正在生成${candidateLabel}候选稿` : `正在写${formatChapterLabel(displayPath)}`,
            'AI 已开始响应，正文会流式出现在编辑器里。',
          )
          const headingPrefix = `# ${formatChapterLabel(displayPath)} ${card.title}\n\n`
          streamHeadingPrefix = headingPrefix
          const placeholder = action === 'continue'
            ? continueBaseContent
            : `${headingPrefix}AI 正在起笔，请稍等...`
          streamingBuffers.value[meta.file_path] = action === 'continue' ? continueBaseContent : headingPrefix
          deps.chapterStatus.value[meta.file_path] = 'blank'
          deps.currentFilePath.value = meta.file_path
          pendingTargetLabel.value = formatChapterLabel(displayPath)
          if (meta.is_candidate && meta.source_file) {
            candidateDraft.value = {
              sourcePath: meta.source_file,
              path: meta.file_path,
              action,
              title: card.title,
              content: placeholder,
              candidateId: meta.candidate_id || null,
            }
          }
          deps.content.value = placeholder
          deps.dirty.value = false
          fileStore.openFile({ name: meta.file_path.split('/').pop() || '', path: meta.file_path, type: 'file' })
          editorStore.setCurrentFile(meta.file_path)
          editorStore.loadContent(meta.file_path, placeholder)
          void deps.scrollTextareaToBottom()

          // 更新流程状态：推导路径成功，开始读取记忆
          if (deps.flow) {
            deps.flow.markNodeSuccess('infer_next_path', [
              { id: 'target-file', label: '目标场景', kind: 'file', path: meta.file_path },
            ])
            deps.flow.markNodeRunning('read_story_memory')
          }
        },
        onStatus: (message) => {
          if (message.includes('更新故事状态')) {
            setWorkStatus('正在更新故事状态', '正在写入故事引擎、近期上下文和场景记忆，保证后续连续性。')
          } else if (message.includes('审稿')) {
            setWorkStatus('正在质量审稿', '正在检查逻辑、爽点兑现和连续性。')
          }
          qualitySummary.value = message === 'AI 正在写正文...'
            ? `正在写${pendingTargetLabel.value}，已生成的内容会自动保留。`
            : message

          // 更新流程状态：根据状态文本推断
          if (deps.flow) {
            if (message.includes('AI 正在写正文') || message.includes('正在生成')) {
              // LLM 正在运行
              deps.flow.markNodeSuccess('read_story_memory')
              deps.flow.markNodeRunning('build_prompt')
              deps.flow.markNodeSuccess('build_prompt')
              deps.flow.markNodeRunning('call_llm')
            } else if (message.includes('审稿') || message.includes('质量')) {
              // 质量检查
              deps.flow.markNodeSuccess('call_llm')
              deps.flow.markNodeRunning('quality_check')
            } else if (message.includes('更新故事状态')) {
              // 更新记忆
              deps.flow.markNodeSuccess('quality_check')
              deps.flow.markNodeRunning('update_memory')
            }
          }
        },
        onDelta: (delta) => {
          if (!generatedFilePath) return
          setWorkStatus(
            isCandidate ? `正在生成${candidateLabel}候选稿` : `正在写${pendingTargetLabel.value}`,
            'AI 正在输出正文，已生成内容会自动保留。',
          )
          const currentBuffer = streamingBuffers.value[generatedFilePath] || ''
          const safeDelta = action !== 'continue' && currentBuffer === streamHeadingPrefix
            ? stripLeadingMarkdownHeading(delta)
            : delta
          const nextContent = action === 'continue' && currentBuffer === continueBaseContent
            ? appendDraftContent(currentBuffer, safeDelta)
            : currentBuffer + safeDelta
          streamingBuffers.value[generatedFilePath] = nextContent
          editorStore.loadContent(generatedFilePath, nextContent)
          if (deps.currentFilePath.value === generatedFilePath) {
            deps.content.value = nextContent
            void deps.scrollTextareaToBottom()
          }
          if (!isBlankChapter(nextContent)) {
            deps.chapterStatus.value[generatedFilePath] = 'done'
          }
        },
        onReplace: (nextContent) => {
          if (!generatedFilePath) return
          streamingBuffers.value[generatedFilePath] = nextContent
          if (candidateDraft.value?.path === generatedFilePath) {
            candidateDraft.value.content = nextContent
          }
          deps.chapterStatus.value[generatedFilePath] = isBlankChapter(nextContent) ? 'blank' : 'done'
          editorStore.loadContent(generatedFilePath, nextContent)
          if (deps.currentFilePath.value === generatedFilePath) {
            deps.content.value = nextContent
            void deps.scrollTextareaToBottom()
          }
        },
        onDone: (result) => {
          setWorkStatus(
            isCandidate ? '候选稿已生成' : '场景已写入',
            isCandidate ? '候选稿已保存，可以采用或放弃。' : '正文已经保存，正在准备后续爽点卡。',
          )
          generatedFilePath = result.file_path
          streamingBuffers.value[result.file_path] = result.content
          if (candidateDraft.value?.path === result.file_path) {
            candidateDraft.value.content = result.content
            if (!candidateDraft.value.candidateId && result.candidate_id) {
              candidateDraft.value.candidateId = result.candidate_id
            }
          }
          deps.chapterStatus.value[result.file_path] = isBlankChapter(result.content) ? 'blank' : 'done'
          qualitySummary.value = result.quality_summary
          engineSummary.value = result.story_engine_summary
          if (result.chapter_plan) {
            chapterMilestone.value = buildChapterMilestone(result, card)
            notification.success(`第${parseSectionPath(result.file_path).ch}章完成，下一章已准备`)
          } else if (action !== 'continue') {
            chapterMilestone.value = null
          }
          deps.dirty.value = false
          fileStore.openFile({ name: result.file_path.split('/').pop() || '', path: result.file_path, type: 'file' })
          editorStore.loadContent(result.file_path, result.content)
          if (deps.currentFilePath.value === result.file_path) {
            deps.content.value = result.content
            editorStore.setCurrentFile(result.file_path)
            void deps.scrollTextareaToBottom()
          }

          // 完成流程可视化
          if (deps.flow) {
            deps.flow.markNodeSuccess('call_llm')
            deps.flow.markNodeSuccess('quality_check', [
              { id: 'quality-result', label: '质量检查结果', kind: 'text', preview: result.quality_summary },
            ])
            deps.flow.markNodeSuccess('save_or_candidate', [
              { id: 'output-file', label: '生成结果', kind: 'file', path: result.file_path },
            ])
            deps.flow.markNodeSuccess('update_memory')
            deps.flow.markNodeSuccess('refresh_ui')
          }
        },
      }, { signal: abortController.signal }, outputFile)
      generating.value = false
      generationAbortController.value = null
      streamingFilePath.value = ''
      pendingTargetLabel.value = ''
      await fileStore.loadTree(projectId)
      if (!isCandidate) {
        setWorkStatus('正在刷新下一场景方向', '正在根据最新正文生成下一场景爽点卡。')
        await refreshOptions(generatedFilePath || deps.currentFilePath.value || null)
        notification.success('场景已生成')
      } else {
        notification.success('候选稿已生成')
      }
    } catch (e: unknown) {
      if (isAbortError(e)) {
        const draft = generatedFilePath ? (streamingBuffers.value[generatedFilePath] || '') : ''
        if (generatedFilePath) {
          deps.chapterStatus.value[generatedFilePath] = draft.trim() ? 'draft' : 'blank'
        }
        deps.dirty.value = Boolean(draft)
        qualitySummary.value = draft
          ? `已停止生成，${pendingTargetLabel.value}的草稿已保留，满意可以保存。`
          : `已停止生成${pendingTargetLabel.value}。`
        notification.success('已停止生成')
      } else {
        const errorMsg = (e instanceof Error ? e.message : '') || '生成失败'
        notification.error(errorMsg)

        // 标记流程错误
        if (deps.flow) {
          deps.flow.markNodeError('call_llm', errorMsg)
        }
      }
    } finally {
      generating.value = false
      generationAbortController.value = null
      streamingFilePath.value = ''
      pendingTargetLabel.value = ''
      if (!loadingOptions.value) clearWorkStatus()
    }
  }

  function stopGeneration() {
    generationAbortController.value?.abort()
  }

  async function continueDraft(
    candidateDraft: Ref<{ sourcePath: string; path: string; action: LiteWriteAction; title: string; content: string; candidateId?: string | null } | null>,
  ) {
    if (generating.value || !deps.currentFilePath.value || !lastGenerationCard.value) return
    streamingBuffers.value[deps.currentFilePath.value] = deps.content.value
    await runGeneration(lastGenerationCard.value, 'continue', deps.currentFilePath.value, null, candidateDraft)
  }

  async function refreshOptions(baseFile = deps.currentFilePath.value || null, overridePrefs?: LiteWritingPrefs) {
    const projectId = projectStore.currentProject?.id
    if (!projectId) return
    const requestId = ++optionRequestId.value
    loadingOptions.value = true
    optionError.value = ''
    nextCards.value = []
    setWorkStatus('正在生成爽点卡', '正在读取前文、故事引擎和近期上下文，给下一场景准备 3 个方向。')
    try {
      const data = await fetchLiteNextOptions(projectId, baseFile, overridePrefs || deps.prefs)
      if (requestId !== optionRequestId.value) return
      setWorkStatus('爽点卡已生成', '下一场景方向已经准备好，可以选择一张卡继续写。')
      // Use splice to trigger Vue reactivity properly
      const newCards = data?.cards ? [...data.cards] : []
      nextCards.value.splice(0, nextCards.value.length, ...newCards)
      nextTargetFile.value = data?.next_file || ''
      if (!data?.cards?.length) {
        optionError.value = '这次没有生成出爽点卡，点"刷新"再试一次。'
        nextTargetFile.value = ''
      }
    } catch {
      if (requestId !== optionRequestId.value) return
      optionError.value = '爽点卡生成失败，点"刷新"重试。'
      nextTargetFile.value = ''
    } finally {
      if (requestId === optionRequestId.value) {
        loadingOptions.value = false
        clearWorkStatus()
      }
    }
  }

  async function loadIdeas(force: boolean) {
    loadingIdeas.value = true
    try {
      if (force) {
        try {
          ideaCards.value = await consumeOrFetch()
        } catch {
          ideaCards.value = await fetchLiteIdeas(String(Date.now()))
        }
      } else {
        ideaCards.value = await consumeOrFetch()
      }
    } finally {
      loadingIdeas.value = false
    }
  }

  async function startProject(card: LiteIdeaCard, router: { push: (path: string) => Promise<unknown> }, candidateDraft: Ref<{ sourcePath: string; path: string; action: LiteWriteAction; title: string; content: string; candidateId?: string | null } | null>) {
    creating.value = true
    try {
      const created = await createLiteProject(card, deps.prefs)
      await projectStore.openProject(created.project_id)
      await fileStore.loadTree(created.project_id)
      await router.push(`/project/${created.project_id}/lite`)
      await deps.openChapter(created.first_file, { skipOptions: true })
      engineSummary.value = {
        protagonist_goal: '主角：证明自己，摆脱羞辱，获得真正能改变命运的力量。',
        current_conflict: card.core_conflict,
        foreshadowing: card.one_liner,
        stage_goal: '当前 5 章目标：完成开局压迫到第一次漂亮反击。',
      }
      const openingCard: LiteNextOptionCard = {
        id: `opening-${card.id}`,
        title: card.title,
        beat: `第一章围绕"${card.one_liner}"展开，写出压迫、反击前奏和主角钩子。`,
        scene: '开局冲突现场',
        protagonist_desire: card.protagonist_hook,
        obstacle: card.core_conflict,
        payoff: card.selling_point,
        hook: '让更大的冲突在结尾露出苗头',
        advancement: '完成开局压迫和第一次行动选择，为下一场景留出明确冲突。',
      }
      nextTargetFile.value = created.first_file
      nextCards.value = []
      await runGeneration(openingCard, 'write', created.first_file, null, candidateDraft)
    } catch (e: unknown) {
      notification.error((e instanceof Error ? e.message : '') || '创建爽文项目失败')
    } finally {
      creating.value = false
    }
  }

  function buildOpeningCardFromProject(): LiteNextOptionCard {
    const project = projectStore.currentProject
    return {
      id: 'opening-current-project',
      title: project?.name || '开局第一章',
      beat: `第一章围绕"${project?.name || '开局冲突'}"展开，写出人物欲望、压迫感和第一个钩子。`,
      scene: project?.background || '开局冲突现场',
      protagonist_desire: '主角要摆脱被动处境，拿到第一份可见收益。',
      obstacle: project?.background || '旧秩序和当面施压的人挡在前面。',
      payoff: project?.theme || '完成开局爽点兑现',
      hook: '让更大的冲突在结尾露出苗头',
      advancement: '把主角目标、压迫来源和下一场景冲突接力点建立起来。',
    }
  }

  async function findResumeChapter(projectId: string) {
    let lastWritten = deps.chapterFiles.value[0] || null
    let hasWritten = false
    let firstBlank: FileNode | null = null
    for (const node of deps.chapterFiles.value) {
      const data = await fileStore.readFile(projectId, node.path)
      const blank = isBlankChapter(data.content || '')
      deps.chapterStatus.value[node.path] = blank ? 'blank' : 'done'
      if (blank && !firstBlank) {
        firstBlank = node
      }
      if (blank) continue
      hasWritten = true
      lastWritten = node
    }
    if (firstBlank) return { node: firstBlank, hasWritten }
    return { node: lastWritten, hasWritten }
  }

  async function openProject(projectId: string, candidateDraft: Ref<{ sourcePath: string; path: string; action: LiteWriteAction; title: string; content: string; candidateId?: string | null } | null>) {
    await projectStore.openProject(projectId)
    await fileStore.loadTree(projectId)
    const { node: resume, hasWritten } = await findResumeChapter(projectId)
    const hasActiveScene = deps.chapterFiles.value.some((node) => node.path === deps.currentFilePath.value)
    if (resume && !hasActiveScene) {
      await deps.openChapter(resume.path, { skipOptions: !hasWritten })
    }
    if (resume && !hasWritten && !creating.value && isBlankChapter(deps.content.value)) {
      const openingCard = buildOpeningCardFromProject()
      nextTargetFile.value = resume.path
      nextCards.value = []
      await runGeneration(openingCard, 'write', resume.path, null, candidateDraft)
    } else if (!resume) {
      await refreshOptions()
    }
  }

  async function generateWithCard(card: LiteNextOptionCard, candidateDraft: Ref<{ sourcePath: string; path: string; action: LiteWriteAction; title: string; content: string; candidateId?: string | null } | null>) {
    if (generating.value) return
    await runGeneration(card, 'write', nextTargetFile.value || null, null, candidateDraft)
  }

  return {
    // State
    generating,
    streamingFilePath,
    streamingBuffers,
    pendingTargetLabel,
    qualitySummary,
    engineSummary,
    chapterMilestone,
    loadingOptions,
    optionError,
    nextCards,
    nextTargetFile,
    ideaCards,
    loadingIdeas,
    creating,
    workPhase,
    workDetail,
    lastGenerationCard,
    autoScrollDuringGeneration,
    // Helpers
    formatChapterLabel,
    parseSectionPath,
    isChapterStart,
    isBlankChapter,
    normalizeChapterHeading,
    candidateActionText,
    setWorkStatus,
    clearWorkStatus,
    // Actions
    runGeneration,
    stopGeneration,
    continueDraft,
    refreshOptions,
    loadIdeas,
    startProject,
    buildOpeningCardFromProject,
    findResumeChapter,
    openProject,
    generateWithCard,
  }
}
