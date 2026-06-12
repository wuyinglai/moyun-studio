/**
 * 墨韵 - 共享 API 类型定义
 *
 * 所有前端 API 请求和响应类型集中管理。
 * 修改接口字段时只需改此处，不用猜后端返回什么。
 *
 * 注意：
 * - UI-only 类型仍保留在组件或模块内
 * - 与后端 schema 对应关系见各注释
 */

// ═══════════════════════════════════════════════════════════
// 一、通用类型
// ═══════════════════════════════════════════════════════════

/** API 统一响应格式 — 对应 backend/schemas/common.py ApiResponse */
export interface ApiResponse<T = unknown> {
  ok?: boolean
  success?: boolean
  data?: T
  error?: ApiError
  message?: string
}

/** API 错误详情 — 对应 backend/schemas/common.py ErrorDetail */
export interface ApiError {
  code: string
  message: string
  details?: unknown
}

// ═══════════════════════════════════════════════════════════
// 二、Project 类型
// ═══════════════════════════════════════════════════════════

/** 项目信息 — 对应 backend/schemas/project.py ProjectInfo */
export interface ProjectInfo {
  id: string
  project_id?: string
  name: string
  author?: string
  genre?: string
  tone?: string
  background?: string
  theme?: string
  writing_style?: string
  target_word_count?: number
  completion_rate?: number
  total_words?: number
  created_at?: string
  updated_at?: string
  scene_target_chars?: number
  scenes_per_chapter?: number
  chapters_per_volume?: number
  unit_label?: string
}

/** 创建项目请求 — 对应 backend/schemas/project.py CreateProjectRequest */
export interface ProjectCreateRequest {
  name?: string
  genre?: string
  tone?: string
  background?: string
  theme?: string
  writing_style?: string
  author?: string
  target_word_count?: number
  outline?: string
  scene_target_chars?: number
  scenes_per_chapter?: number
  chapters_per_volume?: number
  unit_label?: string
}

// ═══════════════════════════════════════════════════════════
// 三、File 类型
// ═══════════════════════════════════════════════════════════

/** 文件读取响应 — 对应 backend/schemas/file.py FileReadResponse */
export interface FileReadResponse {
  path: string
  content: string
  frontmatter: Record<string, unknown> | null
  mtime: number | null
  hash?: string | null
}

/** 文件写入请求 — 对应 backend/schemas/file.py FileWriteRequest */
export interface FileWriteRequest {
  path: string
  content: string
  frontmatter?: Record<string, unknown> | null
  expected_mtime?: number | null
  expected_hash?: string | null
}

/** 文件树节点 — 对应 backend/schemas/file.py TreeNode */
export interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
  mtime?: number | null
  size?: number | null
}

// ═══════════════════════════════════════════════════════════
// 四、Candidate 类型
// ═══════════════════════════════════════════════════════════

/** 候选稿操作类型 */
export type CandidateAction = 'rewrite' | 'continue' | 'modify' | 'chat' | 'expand' | 'shrink' | 'polish' | 'fallback_draft'

/** 候选稿状态 */
export type CandidateStatus = 'pending' | 'adopted' | 'rejected' | 'discarded'

/** 候选稿连续性信息 — 后端 continuity gate 返回 */
export interface ContinuityInfo {
  has_warning: boolean
  severity: 'low' | 'medium' | 'high'
  anchors_missing?: string[]
  anchors_preserved?: string[]
  continuity_ratio?: number
  message?: string
}

/** 候选稿信息 — 对应 backend/schemas/candidate.py CandidateInfo */
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
  adopted_at?: string | null
  word_count: number
  summary?: string | null
  workflow_run_id?: string | null
  model?: string | null
  pipeline_id?: string | null
  prompt_version?: string | null
  source_filename?: string
  filename?: string
  /** 连续性检查结果 — 来自后端 continuity gate */
  continuity?: ContinuityInfo | null
  /** 来源类型 — 真实 LLM 生成 vs dry-run 模拟 */
  source_type?: 'llm' | 'dry-run' | null
  /** 简短摘要 — 如"可能与前文设定不一致"，便于卡片展示 */
  warning_message?: string | null
}

/** 候选稿详情 — 对应 backend/schemas/candidate.py CandidateDetailResponse */
export interface CandidateDetail {
  candidate: CandidateInfo
  content: string
  diff?: string
}

/** 候选稿采用结果 — 对应 backend/schemas/candidate.py AdoptCandidateResponse */
export interface CandidateAdoptResult {
  success: boolean
  message: string
  file_path?: string
  conflict: boolean
}

// ═══════════════════════════════════════════════════════════
// 五、Pipeline 类型
// ═══════════════════════════════════════════════════════════

/** Pipeline 运行请求 — 对应 backend/schemas/pipeline.py PipelineRunRequest */
export interface PipelineRunRequest {
  project_id: string
  pipeline: string
  target_file?: string | null
  user_input?: string | null
  output_mode?: string
  extra_vars?: Record<string, unknown>
}

/** Pipeline 步骤定义 — 对应 backend/schemas/pipeline.py PipelineStepDef */
export interface PipelineStepDef {
  id: string
  label: string
  prompt: string
  fallback?: string | null
  output?: string | null
  confirm?: boolean
}

/** Pipeline 定义 — 对应 backend/schemas/pipeline.py PipelineDef */
export interface PipelineDef {
  name: string
  label: string
  steps: PipelineStepDef[]
}

/** Pipeline 步骤详情 — 对应 backend/schemas/pipeline.py StepDetail */
export interface PipelineStepDetail {
  id: string
  label: string
  prompt_content: string
  fallback?: string | null
  confirm?: boolean
}

/** Pipeline 详情 — 对应 backend/schemas/pipeline.py PipelineDetail */
export interface PipelineDetail {
  name: string
  label: string
  source: 'system' | 'custom'
  steps: PipelineStepDetail[]
}

/** Pipeline SSE 事件 — 通用结构 */
export interface PipelineEvent {
  type: string
  project_id?: string | null
  task_id?: string | null
  timestamp?: string
  payload?: Record<string, unknown>
}

// ═══════════════════════════════════════════════════════════
// 六、Lite 类型
// ═══════════════════════════════════════════════════════════

/** Lite 开局卡 */
export interface LiteIdeaCard {
  id: string
  title: string
  genre: string
  one_liner: string
  protagonist_hook: string
  core_conflict: string
  selling_point: string
}

/** Lite 写作偏好 */
export interface LiteWritingPrefs {
  style: string
  intensity: string
  pace: string
  protagonist: string
  likes: string
  dislikes: string
  genre_params: Record<string, string>
}

/** Lite 写入操作类型 */
export type LiteWriteAction = 'write' | 'rewrite' | 'more_exciting' | 'more_reasonable' | 'continue'

/** Lite 创建项目响应 */
export interface LiteProjectCreateResponse {
  project_id: string
  first_file: string
  story_engine?: Record<string, unknown>
}

/** Lite 下一选项卡 */
export interface LiteNextOptionCard {
  id: string
  title: string
  beat: string
  scene: string
  protagonist_desire: string
  obstacle: string
  payoff: string
  hook: string
  advancement: string
}

/** Lite 流式事件 */
export interface LiteStreamEvent {
  type: 'meta' | 'delta' | 'status' | 'done' | 'error'
  file_path?: string
  delta?: string
  payload?: Record<string, unknown>
}

// ═══════════════════════════════════════════════════════════
// 七、SSE 类型
// ═══════════════════════════════════════════════════════════

/** SSE 通用事件 — 对应 backend/domain/events.py AppEvent */
export interface AppEvent<T = unknown> {
  event_id?: string
  type: string
  project_id?: string | null
  task_id?: string | null
  run_id?: string | null
  source?: string
  timestamp: string
  payload: T
}

/** file.updated 事件 payload — 不含 content */
export interface FileUpdatedPayload {
  path: string
  size?: number
  mtime?: number
  oldPath?: string
  newPath?: string
}

/** sse.heartbeat 事件 payload */
export interface HeartbeatPayload {
  server_time: string
  interval?: number
}

/** candidate.created 事件 payload */
export interface CandidateCreatedPayload {
  candidate_id: string
  source_path: string
  action: string
}

/** candidate.adopted 事件 payload */
export interface CandidateAdoptedPayload {
  candidate_id: string
  source_path: string
}

/** pipeline.started 事件 payload */
export interface PipelineStartedPayload {
  pipeline: string
}

/** pipeline.step 事件 payload */
export interface PipelineStepPayload {
  step_id: string
  label?: string
  error?: string
}
