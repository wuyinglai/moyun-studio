/**
 * 错误消息翻译层 — 将技术错误映射为用户可理解的文案
 *
 * 用法：
 *   import { toUserFacingMessage, getApiErrorCode, getApiErrorMessage } from '@/utils/errorMessages'
 *   notification.error(toUserFacingMessage(error, '操作失败'))
 */

// ─── 错误码 → 用户文案映射 ───────────────────────────────

export const ERROR_CODE_MAP: Record<string, string> = {
  FILE_CONFLICT: '正文已被其他操作修改。请先刷新或保存当前内容，再重新操作。',
  SCENE_PATH_INVALID: '场景路径无效，请检查文件名格式（如 sec-001.md）。',
  FILE_NOT_FOUND: '找不到目标文件，请确认文件是否已被删除或移动。',
  PIPELINE_NOT_FOUND: '找不到指定的管线，请检查管线名称。',
  CANDIDATE_NOT_FOUND: '候选稿不存在或已被删除。',
  LLM_ERROR: '生成服务遇到问题，请稍后重试。如持续出现，请检查模型配置。',
  LLM_CIRCUIT_OPEN: '模型连续失败，已临时熔断。请稍后重试或检查模型服务。',
  LLM_API_ERROR: '模型 API 调用异常，请检查网络连接或模型服务。',
  CONTEXT_LENGTH_ERROR: '当前内容过长，超出模型上下文限制。建议缩短前文或分段生成。',
}

// ─── HTTP 状态码 → 用户文案映射 ──────────────────────────

const HTTP_STATUS_MAP: Record<number, string> = {
  401: 'LLM 配置不可用，请检查 API Key 或模型服务设置。',
  403: 'LLM 配置不可用，请检查 API Key 或模型服务设置。',
  404: '找不到请求的资源，请确认项目或文件是否存在。',
  409: '正文已被其他操作修改。请先刷新或保存当前内容，再重新操作。',
  429: '请求过于频繁，请稍后再试。',
  500: '生成服务暂时出错，请稍后重试。如多次出现，请查看后端日志。',
  502: '后端服务不可用，请确认 Moyun 后端已启动。',
  503: '生成服务暂时不可用，请稍后重试。',
  504: '后端响应超时，请稍后重试或检查后端状态。',
}

// ─── 关键词 → 用户文案映射（按优先级排列，先匹配先返回） ─────

const KEYWORD_PATTERNS: Array<{ pattern: RegExp; message: string }> = [
  {
    pattern: /ECONNREFUSED|ENOTFOUND|NetworkError|fetch failed|Failed to fetch|网络/i,
    message: '无法连接后端服务，请确认 Moyun 后端已启动。',
  },
  {
    pattern: /api.?key|unauthorized|认证失败|配置缺失|LLM.*配置|模型.*不可用/i,
    message: 'LLM 配置不可用，请检查 API Key 或模型服务设置。',
  },
  {
    pattern: /dry.?run|模拟运行|Pipeline Dry Run/i,
    message: '这是一次模拟运行，不会写入正文，也不会生成正式候选稿。',
  },
  {
    pattern: /timeout|超时|ETIMEDOUT/i,
    message: '操作超时，请稍后重试。',
  },
  {
    pattern: /Internal Server Error/i,
    message: '生成服务暂时出错，请稍后重试。如多次出现，请查看后端日志。',
  },
]

// ─── 默认 fallback ──────────────────────────────────────

const DEFAULT_MESSAGE = '操作失败，请稍后重试。'

// ─── 公共工具：提取 API 错误码 ────────────────────────────

/**
 * 从 Axios 错误响应中提取后端返回的 error code。
 * 支持 `{ error: { code: string } }` 格式。
 */
export function getApiErrorCode(error: unknown): string | undefined {
  const response = (error as { response?: { data?: { error?: { code?: string } } } }).response
  return response?.data?.error?.code
}

// ─── 公共工具：提取 API 原始错误消息 ──────────────────────

/**
 * 从 Axios 错误响应中提取后端返回的原始错误消息。
 * 兼容多种后端响应格式：
 *   - { detail: "..." }  (FastAPI 标准)
 *   - { error: { message: "..." } }  (结构化错误)
 *   - { message: "..." }  (简单格式)
 *   - { detail: { message: "..." } }  (嵌套格式)
 *   - Error.message  (JS Error)
 */
export function getApiErrorMessage(error: unknown): string {
  if (!error) return ''

  // Axios response 格式
  const resp = (error as { response?: { data?: unknown } }).response
  if (resp?.data) {
    const data = resp.data as Record<string, unknown>

    // FastAPI 标准: { detail: "..." }
    if (typeof data.detail === 'string') return data.detail

    // 结构化: { error: { message: "..." } }
    const errObj = data.error as Record<string, unknown> | undefined
    if (errObj && typeof errObj.message === 'string') return errObj.message

    // 简单: { message: "..." }
    if (typeof data.message === 'string') return data.message

    // 嵌套: { detail: { message: "..." } }
    const detailObj = data.detail as Record<string, unknown> | undefined
    if (detailObj && typeof detailObj.message === 'string') return detailObj.message
  }

  // JS Error
  if (error instanceof Error && error.message) return error.message

  // fetch 非 OK 响应：可能传入 "HTTP 500: Internal Server Error" 字符串
  if (typeof error === 'string') return error

  return ''
}

// ─── 核心函数：技术错误 → 用户文案 ───────────────────────

/**
 * 将技术错误映射为用户可理解的文案。
 *
 * 匹配优先级：
 *   1. 后端 error code（FILE_CONFLICT 等）
 *   2. HTTP 状态码（401, 500 等）
 *   3. 原始消息关键词（NetworkError, dry_run 等）
 *   4. fallback 参数或默认文案
 *
 * @param error    - Axios 错误、JS Error、或任意 error 对象
 * @param fallback - 无法匹配时的兜底文案（默认 "操作失败，请稍后重试。"）
 * @returns 面向用户的中文消息
 */
export function toUserFacingMessage(error: unknown, fallback?: string): string {
  // 1. 后端 error code
  const code = getApiErrorCode(error)
  if (code && ERROR_CODE_MAP[code]) {
    return ERROR_CODE_MAP[code]
  }

  // 2. HTTP 状态码
  const status = (error as { response?: { status?: number } }).response?.status
  if (status && HTTP_STATUS_MAP[status]) {
    return HTTP_STATUS_MAP[status]
  }

  // 3. 原始消息关键词
  const raw = getApiErrorMessage(error)
  if (raw) {
    for (const { pattern, message } of KEYWORD_PATTERNS) {
      if (pattern.test(raw)) return message
    }
  }

  // 4. fallback
  return fallback || DEFAULT_MESSAGE
}
