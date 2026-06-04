import { ref, type Ref } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import type { LiteWriteAction, LiteNextOptionCard, LiteWritingPrefs } from '@/services/liteService'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { CandidateAdoptResult } from '@/shared/api/types'

export interface CandidateDraft {
  sourcePath: string
  path: string
  action: LiteWriteAction
  title: string
  content: string
  candidateId?: string | null
}

export function useLiteCandidateActions(deps: {
  content: Ref<string>
  currentFilePath: Ref<string>
  chapterStatus: Ref<Record<string, 'done' | 'blank' | 'draft'>>
  streamingBuffers: Ref<Record<string, string>>
  generating: Ref<boolean>
  saving: Ref<boolean>
  dirty: Ref<boolean>
  prefs: LiteWritingPrefs
  formatChapterLabel: (path: string) => string
  isBlankChapter: (text: string) => boolean
  normalizeChapterHeading: (path: string, text: string) => string
  refreshOptions: (baseFile?: string | null) => Promise<void>
  setWorkStatus: (title: string, detail: string) => void
  clearWorkStatus: () => void
  runGeneration: (card: LiteNextOptionCard, action: LiteWriteAction, targetFile: string | null, outputFile: string | null, candidateDraft: Ref<CandidateDraft | null>) => Promise<void>
  openChapter: (path: string, options?: { skipOptions?: boolean }) => Promise<void>
  loadingOptions: Ref<boolean>
  clearFallbackPauseStatus?: () => void
}) {
  const projectStore = useProjectStore()
  const fileStore = useFileStore()
  const editorStore = useEditorStore()
  const notification = useNotificationStore()

  const candidateDraft = ref<CandidateDraft | null>(null)
  const chatRevisionInput = ref('')
  const chatRevisionNote = ref('')

  async function acceptCandidate() {
    const draft = candidateDraft.value
    const projectId = projectStore.currentProject?.id
    if (!draft || !projectId || !draft.candidateId) return
    deps.saving.value = true
    deps.setWorkStatus('正在采用候选稿', '正在通过统一候选稿接口覆盖原场景。')
    try {
      const result = await api.post<CandidateAdoptResult>(
        API_ROUTES.candidateAdopt(projectId, draft.candidateId),
      )
      if (result?.conflict || result?.success === false) {
        notification.error(result?.message || '源文件已被其他操作修改，请重新生成候选稿后再采用。')
        return
      }
      candidateDraft.value = null
      delete deps.streamingBuffers.value[draft.path]
      deps.currentFilePath.value = draft.sourcePath
      deps.content.value = deps.normalizeChapterHeading(draft.sourcePath, deps.content.value)
      deps.chapterStatus.value[draft.sourcePath] = deps.isBlankChapter(deps.content.value) ? 'blank' : 'done'
      deps.dirty.value = false
      fileStore.openFile({ name: draft.sourcePath.split('/').pop() || '', path: draft.sourcePath, type: 'file' })
      editorStore.setCurrentFile(draft.sourcePath)
      editorStore.loadContent(draft.sourcePath, deps.content.value)
      await fileStore.loadTree(projectId)
      deps.setWorkStatus('正在刷新下一场景方向', '正在根据采用后的正文重新生成下一场景爽点卡。')
      await deps.refreshOptions(draft.sourcePath)
      if (deps.clearFallbackPauseStatus) deps.clearFallbackPauseStatus()
      notification.success('已采用候选稿并替换原文')
    } catch (error: unknown) {
      const status = (error as { response?: { status?: number } }).response?.status
      if (status === 409) {
        notification.error('源文件已被其他操作修改，请重新生成候选稿后再采用。')
      } else {
        notification.error((error instanceof Error ? error.message : '') || '采用候选稿失败')
      }
    } finally {
      deps.saving.value = false
      if (!deps.loadingOptions.value) deps.clearWorkStatus()
    }
  }

  async function discardCandidate() {
    const draft = candidateDraft.value
    const projectId = projectStore.currentProject?.id
    if (!draft || !projectId) return
    try {
      if (draft.candidateId) {
        await api.delete(API_ROUTES.candidateDetail(projectId, draft.candidateId))
      }
    } catch {
      // 候选稿已经不存在时也允许回到原文。
    }
    candidateDraft.value = null
    delete deps.streamingBuffers.value[draft.path]
    await deps.openChapter(draft.sourcePath, { skipOptions: true })
    if (deps.clearFallbackPauseStatus) deps.clearFallbackPauseStatus()
    notification.success('已放弃候选稿')
  }

  async function rewriteCurrent(
    nextCards: LiteNextOptionCard[],
    currentFilePath: string,
  ) {
    if (deps.generating.value) return
    const card = nextCards[0]
    if (card && currentFilePath) {
      await deps.runGeneration(card, 'rewrite', currentFilePath, null, candidateDraft)
    }
  }

  async function improveCurrent(
    action: 'more_exciting' | 'more_reasonable',
    nextCards: LiteNextOptionCard[],
    currentFilePath: string,
  ) {
    if (deps.generating.value) return
    const card = nextCards[0]
    if (card && currentFilePath) {
      await deps.runGeneration(card, action, currentFilePath, null, candidateDraft)
    }
  }

  async function runChatRevision(
    currentFilePath: string,
  ) {
    const instruction = chatRevisionInput.value.trim()
    if (!instruction || deps.generating.value) return
    const sourcePath = candidateDraft.value?.sourcePath || currentFilePath
    if (!sourcePath) return
    const label = deps.formatChapterLabel(sourcePath)
    const card: LiteNextOptionCard = {
      id: `chat-revision-${Date.now()}`,
      title: '聊天改稿',
      beat: `根据用户聊天指令改写当前场景：${instruction}`,
      scene: `保留${label}的主要剧情，只调整用户指出的问题。`,
      protagonist_desire: '保持人物核心欲望不变，让行动更贴合用户修改方向。',
      obstacle: '不能破坏前文逻辑、人物动机、场景钩子和既有设定。',
      payoff: `完成用户要求：${instruction}`,
      hook: '保留或加强本场景结尾钩子。',
      advancement: '生成一版可采用的候选稿，供用户确认后替换原文。',
    }
    chatRevisionNote.value = `正在根据"${instruction}"生成候选稿。`
    await deps.runGeneration(card, 'rewrite', sourcePath, null, candidateDraft)
    chatRevisionNote.value = '候选稿已生成，可以在编辑器中查看并决定是否采用。'
  }

  return {
    candidateDraft,
    chatRevisionInput,
    chatRevisionNote,
    acceptCandidate,
    discardCandidate,
    rewriteCurrent,
    improveCurrent,
    runChatRevision,
  }
}
