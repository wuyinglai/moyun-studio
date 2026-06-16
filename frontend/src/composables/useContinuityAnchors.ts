import { computed, ref } from 'vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type {
  ContinuityAnchor,
  ContinuityAnchorsDocument,
  ContinuityAnchorPriority,
  ContinuityAnchorScope,
  ContinuityAnchorStatus,
  ContinuityAnchorType,
} from '@/shared/api/types'

const anchors = ref<ContinuityAnchor[]>([])
const loading = ref(false)
const error = ref('')
const loadedProjectId = ref('')

function emptyDocument(): ContinuityAnchorsDocument {
  return { version: 1, anchors: [] }
}

function nowIso(): string {
  return new Date().toISOString()
}

function makeAnchorId(): string {
  return `anchor-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}

async function persist(projectId: string, nextAnchors: ContinuityAnchor[]) {
  const document: ContinuityAnchorsDocument = {
    version: 1,
    anchors: nextAnchors,
  }
  const saved = await api.put<ContinuityAnchorsDocument>(
    API_ROUTES.continuityAnchors(projectId),
    document,
  )
  anchors.value = saved.anchors || []
  loadedProjectId.value = projectId
  return saved
}

export function useContinuityAnchors() {
  const activeAnchors = computed(() => anchors.value.filter(anchor => anchor.status === 'active'))
  const activeCount = computed(() => activeAnchors.value.length)

  async function load(projectId: string, force = false) {
    if (!projectId) {
      anchors.value = []
      loadedProjectId.value = ''
      return emptyDocument()
    }
    if (!force && loadedProjectId.value === projectId) {
      return { version: 1, anchors: anchors.value }
    }
    loading.value = true
    error.value = ''
    try {
      const document = await api.get<ContinuityAnchorsDocument>(
        API_ROUTES.continuityAnchors(projectId),
      )
      anchors.value = document.anchors || []
      loadedProjectId.value = projectId
      return document
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : String(err || '')
      anchors.value = []
      loadedProjectId.value = projectId
      return emptyDocument()
    } finally {
      loading.value = false
    }
  }

  async function addAnchor(projectId: string, draft: {
    title: string
    content: string
    type?: ContinuityAnchorType
    scope?: ContinuityAnchorScope
    priority?: ContinuityAnchorPriority
  }) {
    const title = draft.title.trim()
    const content = draft.content.trim()
    if (!projectId || !title || !content) return null
    if (loadedProjectId.value !== projectId) {
      await load(projectId, true)
    }
    const next: ContinuityAnchor = {
      id: makeAnchorId(),
      type: draft.type || 'character_state',
      title,
      content,
      scope: draft.scope || 'global',
      status: 'active',
      priority: draft.priority || 'normal',
      source: 'user',
      updated_at: nowIso(),
    }
    await persist(projectId, [...anchors.value, next])
    return next
  }

  async function updateAnchor(projectId: string, id: string, patch: Partial<ContinuityAnchor>) {
    if (!projectId || !id) return
    if (loadedProjectId.value !== projectId) {
      await load(projectId, true)
    }
    const next = anchors.value.map(anchor => (
      anchor.id === id
        ? { ...anchor, ...patch, updated_at: nowIso() }
        : anchor
    ))
    await persist(projectId, next)
  }

  async function archiveAnchor(projectId: string, id: string) {
    await updateAnchor(projectId, id, { status: 'archived' as ContinuityAnchorStatus })
  }

  return {
    anchors,
    activeAnchors,
    activeCount,
    loading,
    error,
    load,
    addAnchor,
    archiveAnchor,
    updateAnchor,
  }
}
