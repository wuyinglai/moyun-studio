// LLM 配置相关类型

export type LLMProvider = 'openai' | 'ollama' | 'anthropic' | 'deepseek' | 'other'

export interface LLMConfig {
  provider: LLMProvider
  api_base: string
  api_key: string
  model: string
  thinking_enabled: boolean
}

export interface ModelInfo {
  id: string
  name: string
  provider: LLMProvider
  // 其他信息
  context_length?: number
  capabilities?: string[]
}

export interface ConnectionTestResult {
  success: boolean
  latency_ms?: number
  model?: string
  error?: string
}
