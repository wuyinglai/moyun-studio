import api from '@/services/api'
import { API_BASE, API_ROUTES } from '@/shared/api/routes'
import type {
  LiteIdeaCard as ApiLiteIdeaCard,
  LiteWritingPrefs as ApiLiteWritingPrefs,
  LiteWriteAction as ApiLiteWriteAction,
  LiteNextOptionCard as ApiLiteNextOptionCard,
} from '@/shared/api/types'

export type LiteWritingPrefs = ApiLiteWritingPrefs
export type LiteIdeaCard = ApiLiteIdeaCard
export type LiteNextOptionCard = ApiLiteNextOptionCard
export type LiteWriteAction = ApiLiteWriteAction

/** UI-only: 创建项目响应（story_engine 后端实际返回 string） */
export interface LiteProjectCreateResponse {
  project_id: string
  first_file: string
  story_engine: string | Record<string, unknown>
}

/** UI-only: 下一选项响应 */
export interface LiteNextOptionsResponse {
  cards: LiteNextOptionCard[]
  current_file: string
  next_file: string
}

/** UI-only: 写入下一场景响应 */
export interface LiteWriteNextResponse {
  file_path: string
  content: string
  quality_summary: string
  story_engine_summary: Record<string, string>
  chapter_plan?: string | null
  candidate_id?: string | null
  source_file?: string | null
  fallback_used?: boolean
}

/** UI-only: 流式回调 */
export interface LiteWriteStreamCallbacks {
  onMeta?: (data: { file_path: string; label: string; source_file?: string; is_candidate?: boolean; candidate_id?: string | null; fallback_used?: boolean }) => void
  onDelta?: (delta: string) => void
  onReplace?: (content: string) => void
  onStatus?: (message: string) => void
  onDone?: (data: LiteWriteNextResponse) => void
}

/** UI-only: 流式选项 */
export interface LiteWriteStreamOptions {
  signal?: AbortSignal
}

export function defaultLitePrefs(): LiteWritingPrefs {
  return {
    style: '热血',
    intensity: '标准',
    pace: '快节奏',
    protagonist: '张扬',
    likes: '',
    dislikes: '',
    genre_params: {},
  }
}

export async function fetchLiteIdeas(seed = '') {
  const data = await api.post<{ cards: LiteIdeaCard[] }>('/lite/ideas', { seed }, { timeout: 60000 })
  return data.cards
}

export async function createLiteProject(card: LiteIdeaCard, prefs: LiteWritingPrefs) {
  return await api.post<LiteProjectCreateResponse>('/lite/projects', { card, prefs })
}

export async function fetchLiteNextOptions(projectId: string, currentFile: string | null, prefs: LiteWritingPrefs) {
  return await api.post<LiteNextOptionsResponse>(API_ROUTES.liteNextOptions, {
    project_id: projectId,
    current_file: currentFile,
    prefs,
  })
}

export async function writeLiteNext(
  projectId: string,
  targetFile: string | null,
  selectedCard: LiteNextOptionCard,
  prefs: LiteWritingPrefs,
  action: LiteWriteAction = 'write',
  outputFile: string | null = null,
) {
  return await api.post<LiteWriteNextResponse>('/lite/write-next', {
    project_id: projectId,
    target_file: targetFile,
    output_file: outputFile,
    selected_card: selectedCard,
    prefs,
    action,
  }, {
    timeout: 300000,
  })
}

export async function streamLiteNext(
  projectId: string,
  targetFile: string | null,
  selectedCard: LiteNextOptionCard,
  prefs: LiteWritingPrefs,
  action: LiteWriteAction = 'write',
  callbacks: LiteWriteStreamCallbacks = {},
  options: LiteWriteStreamOptions = {},
  outputFile: string | null = null,
) {
  const response = await fetch(API_BASE + API_ROUTES.liteWriteNextStream, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal: options.signal,
    body: JSON.stringify({
      project_id: projectId,
      target_file: targetFile,
      output_file: outputFile,
      selected_card: selectedCard,
      prefs,
      action,
    }),
  })

  if (!response.ok || !response.body) {
    throw new Error(`生成失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const rawLine of lines) {
      const line = rawLine.trimEnd()
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6))
        if (currentEvent === 'error') {
          throw new Error(data.message || '生成失败')
        }
        if (currentEvent === 'meta') callbacks.onMeta?.(data)
        if (currentEvent === 'delta') callbacks.onDelta?.(data.delta || '')
        if (currentEvent === 'replace') callbacks.onReplace?.(data.content || '')
        if (currentEvent === 'status') callbacks.onStatus?.(data.message || '')
        if (currentEvent === 'done') callbacks.onDone?.(data)
      }
    }
  }
}
