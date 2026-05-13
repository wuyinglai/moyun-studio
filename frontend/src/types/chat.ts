// 生成/提取相关类型

export interface BatchGenerateRequest {
  project_id: string
  volume_number?: number | null
  chapter_number?: number | null
  section_numbers?: number[] | null
  prompt_type?: string
  temperature?: number
}

export interface BatchGenerateItem {
  target_file: string
  status: string
  word_count: number
  error?: string | null
  prompt?: string
}

export interface BatchGenerateResponse {
  tasks: BatchGenerateItem[]
  total: number
  succeeded: number
  failed: number
}

export interface ExtractTaskRequest {
  project_id: string
  type: 'character' | 'plot' | 'scene' | 'summary'
  source_file: string
}

export interface ExtractTaskResponse {
  id: string
  type: string
  title: string
  content: string
  source_file: string
  created_at: string
}

// 质量审查相关类型 (G0112)

export interface QualityScores {
  coherence: number
  character_consistency: number
  setting_consistency: number
  writing_quality: number
  logic: number
  style_compliance: number
}

export interface ReviewIssue {
  severity: 'critical' | 'major' | 'minor'
  category: string
  location: string
  description: string
}

export interface QualityReviewResult {
  scores: QualityScores
  summary: string
  strengths: string[]
  issues: ReviewIssue[]
  suggestions: string[]
}

export interface ReviewRequest {
  project_id: string
  target_file: string
  chapter_title?: string | null
}

export interface ReviewResponse {
  review_id: string
  target_file: string
  result: QualityReviewResult
}

export interface BatchReviewRequest {
  project_id: string
  target_files: string[]
}

export interface ReviewItem {
  target_file: string
  status: string
  result?: QualityReviewResult | null
  error?: string | null
}

export interface BatchReviewResponse {
  reviews: ReviewItem[]
  total: number
  succeeded: number
  failed: number
}

// 聊天相关类型

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: number
  thinking?: string
  taskId?: string
}

export interface ChatSession {
  projectId: string
  messages: ChatMessage[]
  isStreaming: boolean
}

// SSE 事件类型（前端用）
export interface SSEEvent {
  type: SSEEventType
  data: unknown
}

export type SSEEventType =
  | 'generation'
  | 'file-created'
  | 'file-updated'
  | 'file-renamed'
  | 'directory-created'
  | 'task'
  | 'queue'
  | 'llm-status'
  | 'thinking'
  | 'error'
  | 'done'
  | 'connected'
