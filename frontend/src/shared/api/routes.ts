/**
 * API 路由集中定义
 *
 * 所有前端 API 路径统一在此声明，避免散落在各组件/Store 中。
 * 修改接口路径时只需改此处。
 *
 * 注意：
 * - api (axios) 实例 baseURL 为 '/api'，所以 api.get('/projects') 实际请求 /api/projects
 * - fetch() 调用需要完整路径，使用 API_BASE + path 拼接
 */

export interface FileContentResponse {
  content: string
  hash?: string
  mtime?: number
}

export const API_BASE = '/api'

export const API_ROUTES = {
  // ── Projects ──────────────────────────────────────
  projects: '/projects',
  projectDetail: (projectId: string) => `/projects/${projectId}`,
  continuityAnchors: (projectId: string) => `/projects/${projectId}/continuity-anchors`,

  // ── Files ─────────────────────────────────────────
  file: '/file',
  fileCreate: '/file/create',
  fileRename: '/file/rename',
  fileDelete: '/file/delete',
  filesSearch: '/files/search',
  directoryCreate: '/directory/create',
  directoryDelete: '/directory/delete',

  // ── Pipeline ──────────────────────────────────────
  pipelineRun: '/pipeline/run',
  pipelineDetail: (name: string) => `/pipeline/${name}`,
  pipelineCustom: '/pipeline/custom',

  // ── Generate ──────────────────────────────────────
  generate: '/generate',
  generateBatch: '/generate/batch',

  // ── Candidates ────────────────────────────────────
  candidates: (projectId: string) => `/candidates/${projectId}`,
  candidateDetail: (projectId: string, candidateId: string) => `/candidates/${projectId}/${candidateId}`,
  candidateAdopt: (projectId: string, candidateId: string) => `/candidates/${projectId}/${candidateId}/adopt`,
  candidateRevise: (projectId: string, candidateId: string) => `/candidates/${projectId}/${candidateId}/revise`,
  candidateDelete: (projectId: string, candidateId: string) => `/candidates/${projectId}/${candidateId}/delete`,

  // ── Lite ──────────────────────────────────────────
  liteIdeas: '/lite/ideas',
  liteProjects: '/lite/projects',
  liteNextOptions: '/lite/next-options',
  liteWriteNext: '/lite/write-next',
  liteWriteNextStream: '/lite/write-next-stream',

  // ── LLM / Settings ───────────────────────────────
  llmConfig: '/llm/config',
  llmTest: '/llm/test',

  // ── SSE ───────────────────────────────────────────
  sse: '/sse',

  // ── Chat ──────────────────────────────────────────
  chat: '/chat',

  // ── Prompts ───────────────────────────────────────
  prompts: (promptType: string) => `/prompts/${promptType}`,
  promptsRawFile: '/prompts/raw-file',

  // ── Snapshots ─────────────────────────────────────
  snapshot: (projectId: string) => `/snapshots/${projectId}`,
  snapshotRestore: (projectId: string) => `/snapshots/${projectId}/restore`,

  // ── Revision Log ──────────────────────────────────
  revisionLog: (projectId: string) => `/revision-log/${projectId}`,

  // ── Backup ────────────────────────────────────────
  backupForward: '/backup/forward',
  backupBackward: '/backup/backward',
  backupDetail: (backupId: string) => `/backup/${backupId}`,

  // ── Trash ─────────────────────────────────────────
  trashRestore: '/trash/restore',

  // ── Feedback ──────────────────────────────────────
  feedback: (projectId: string) => `/feedback/${projectId}`,
  feedbackDetail: (projectId: string, feedbackId: string) => `/feedback/${projectId}/${feedbackId}`,

  // ── Quality Review ────────────────────────────────
  qualityReviews: (projectId: string) => `/quality/reviews/${projectId}`,

  // ── Tasks ─────────────────────────────────────────
  taskCancel: (taskId: string) => `/tasks/${taskId}/cancel`,

  // ── Workflows ─────────────────────────────────────
  workflowsRun: '/workflows/run',
  workflowRunResume: (runId: string) => `/workflows/runs/${runId}/resume`,
  workflowStop: (runId: string) => `/workflows/stop/${runId}`,
  workflowsSave: '/workflows/save',
  workflowDetail: (name: string) => `/workflows/${name}`,

  // ── Config ────────────────────────────────────────
  configCustomParams: '/config/custom-params',

  // ── Scene Plan ────────────────────────────────────
  scenePlanGenerate: '/scene-plan/generate',
  scenePlanValidate: '/scene-plan/validate',
  scenePlanSave: '/scene-plan/save',
  scenePlanLoad: '/scene-plan/load',
} as const
