/** 候选稿模块 - 类型定义 */

export type CandidateAction = 'rewrite' | 'continue' | 'modify' | 'chat' | 'expand' | 'shrink' | 'polish'

export type CandidateStatus = 'pending' | 'adopted' | 'rejected' | 'discarded'

export interface CandidateInfo {
  id: string
  project_id: string
  source_path: string
  candidate_path: string
  action: CandidateAction
  status: CandidateStatus
  base_hash: string
  base_mtime: number | null
  created_at: string
  adopted_at?: string
  word_count: number
  summary?: string
  workflow_run_id?: string
  model?: string
  pipeline_id?: string
  prompt_version?: string
  source_filename?: string
  filename?: string
}

export interface CandidateDetail {
  candidate: CandidateInfo
  content: string
}

export interface AdoptResult {
  success: boolean
  message: string
  file_path: string
  conflict: boolean
}
