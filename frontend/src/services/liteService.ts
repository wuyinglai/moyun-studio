import api from '@/services/api'

export interface LiteWritingPrefs {
  style: string
  intensity: string
  pace: string
  protagonist: string
  likes: string
  dislikes: string
  genre_params: Record<string, string>
}

export interface LiteIdeaCard {
  id: string
  title: string
  genre: '玄幻' | '武侠' | '言情' | '都市' | '仙侠'
  one_liner: string
  protagonist_hook: string
  core_conflict: string
  selling_point: string
}

export interface LiteNextOptionCard {
  id: string
  title: string
  beat: string
  scene: string
  payoff: string
  hook: string
}

export interface LiteProjectCreateResponse {
  project_id: string
  first_file: string
  story_engine: string
}

export interface LiteNextOptionsResponse {
  cards: LiteNextOptionCard[]
  current_file: string
  next_file: string
}

export interface LiteWriteNextResponse {
  file_path: string
  content: string
  quality_summary: string
  story_engine_summary: Record<string, string>
  chapter_plan?: string | null
}

export type LiteWriteAction = 'write' | 'rewrite' | 'more_exciting' | 'more_reasonable' | 'continue'

export interface LiteWriteStreamCallbacks {
  onMeta?: (data: { file_path: string; label: string }) => void
  onDelta?: (delta: string) => void
  onReplace?: (content: string) => void
  onStatus?: (message: string) => void
  onDone?: (data: LiteWriteNextResponse) => void
}

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
  return await api.post<LiteNextOptionsResponse>('/lite/next-options', {
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
) {
  return await api.post<LiteWriteNextResponse>('/lite/write-next', {
    project_id: projectId,
    target_file: targetFile,
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
) {
  const response = await fetch('/api/lite/write-next-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal: options.signal,
    body: JSON.stringify({
      project_id: projectId,
      target_file: targetFile,
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
