/**
 * 真实 LLM 环境变量读取
 *
 * 安全要求：
 * - API Key 不得打印到 console
 * - 测试报告不得包含 API Key
 * - 如果 MOYUN_E2E_REAL_LLM 不是 true，则跳过真实 LLM 相关测试
 */

export interface LLMEnvConfig {
  realLLM: boolean
  provider: string
  baseUrl: string
  model: string
  /** API Key — 严禁打印或写入报告 */
  apiKey: string
  timeoutMs: number
}

function maskApiKey(key: string | undefined): string {
  if (!key) return '(未设置)'
  if (key.length <= 8) return '****'
  return key.slice(0, 4) + '****' + key.slice(-4)
}

export function getLLMEnv(): LLMEnvConfig {
  const realLLM = process.env.MOYUN_E2E_REAL_LLM === 'true'
  const provider = process.env.MOYUN_E2E_PROVIDER || 'openai-compatible'
  const baseUrl = process.env.MOYUN_E2E_BASE_URL || 'http://127.0.0.1:1234/v1'
  const model = process.env.MOYUN_E2E_MODEL || 'local-model'
  const apiKey = process.env.MOYUN_E2E_API_KEY || ''
  const timeoutMs = parseInt(process.env.MOYUN_E2E_TIMEOUT_MS || '120000', 10)

  return {
    realLLM,
    provider,
    baseUrl,
    model,
    apiKey,
    timeoutMs,
  }
}

/** 获取 LLM 配置的安全日志版本（API Key 已脱敏） */
export function getLLMEnvSafe(): Omit<LLMEnvConfig, 'apiKey'> & { apiKey: string } {
  const env = getLLMEnv()
  return {
    ...env,
    apiKey: maskApiKey(env.apiKey),
  }
}

/** 验证 LLM 环境配置完整性，缺失时给出清晰提示 */
export function validateLLMEnv(): { valid: boolean; errors: string[] } {
  const env = getLLMEnv()
  const errors: string[] = []

  if (!env.realLLM) {
    return { valid: false, errors: ['MOYUN_E2E_REAL_LLM 未设置为 true，跳过真实 LLM 测试'] }
  }

  if (!env.baseUrl) {
    errors.push(
      'MOYUN_E2E_BASE_URL 未设置。请设置 LLM API 地址，例如：\n' +
      '  本地模型: MOYUN_E2E_BASE_URL=http://127.0.0.1:1234/v1\n' +
      '  DeepSeek: MOYUN_E2E_BASE_URL=https://api.deepseek.com/v1'
    )
  }

  if (!env.model) {
    errors.push(
      'MOYUN_E2E_MODEL 未设置。请设置模型名称，例如：\n' +
      '  本地模型: MOYUN_E2E_MODEL=local-model\n' +
      '  DeepSeek: MOYUN_E2E_MODEL=deepseek-v4-flash'
    )
  }

  if (!env.apiKey && !env.baseUrl.includes('127.0.0.1')) {
    errors.push(
      'MOYUN_E2E_API_KEY 未设置。云模型需要 API Key，请设置：\n' +
      '  MOYUN_E2E_API_KEY=sk-xxxx'
    )
  }

  return { valid: errors.length === 0, errors }
}

/** 如果未启用真实 LLM 则返回 true，用于 test.skip */
export function shouldSkipLLMTests(): boolean {
  return process.env.MOYUN_E2E_REAL_LLM !== 'true'
}

/** 安全打印（脱敏），仅在调试时使用 */
export function debugLogLLMEnv(): void {
  const safe = getLLMEnvSafe()
  console.log('[LLM Env]', JSON.stringify(safe, null, 2))
}
