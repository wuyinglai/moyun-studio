import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface LLMConfig {
  apiType: 'openai' | 'ollama' | 'anthropic' | 'claude' | 'deepseek' | 'custom' | 'other'
  apiUrl: string
  apiKey: string
  model: string
  thinking: boolean
}

export const useLLMStore = defineStore('llm', () => {
  const config = ref<LLMConfig>({
    apiType: 'openai',
    apiUrl: '',
    apiKey: '',
    model: '',
    thinking: false,
  })
  const isConnected = ref(false)
  const isThinking = ref(false)
  const isGenerating = ref(false)
  const currentStepLabel = ref('')  // pipeline 当前步骤名称，如"优化节奏"
  const availableModels = ref<string[]>([])

  async function loadConfig() {
    try {
      const data = await api.get<Record<string, unknown>>('/llm/config')
      if (data) {
        config.value = normalizeConfig(data)
      }
    } catch {
      // 配置不存在，使用默认
    }
  }

  async function saveConfig(cfg: Partial<LLMConfig>) {
    const next = normalizeConfig({ ...config.value, ...cfg })
    await api.post('/llm/config', {
      api_type: normalizeProvider(next.apiType),
      api_url: next.apiUrl,
      api_key: next.apiKey,
      model: next.model,
      thinking: next.thinking,
    })
    // 合并本地配置（后端仅保存，不返回完整配置）
    config.value = next
  }

  async function testConnection(signal?: AbortSignal): Promise<boolean> {
    try {
      const status = await api.post<{ connected: boolean }>('/llm/test', undefined, { signal, timeout: 15000 })
      isConnected.value = Boolean(status?.connected)
      return isConnected.value
    } catch {
      isConnected.value = false
      return false
    }
  }

  async function loadStatus() {
    try {
      const status = await api.get<{ connected: boolean }>('/llm/status', { timeout: 15000 })
      isConnected.value = Boolean(status?.connected)
    } catch {
      isConnected.value = false
    }
  }

  async function fetchModels(signal?: AbortSignal) {
    try {
      const data = await api.get<{ models: Array<{ id: string; name: string }> }>('/llm/models', { signal, timeout: 15000 })
      availableModels.value = (data?.models || []).map((m) => m.id)
    } catch {
      availableModels.value = []
    }
  }

  function setThinking(val: boolean) {
    isThinking.value = val
  }

  function setGenerating(val: boolean) {
    isGenerating.value = val
  }

  return {
    config,
    isConnected,
    isThinking,
    isGenerating,
    currentStepLabel,
    availableModels,
    loadConfig,
    saveConfig,
    testConnection,
    fetchModels,
    loadStatus,
    setThinking,
    setGenerating,
  }
}, {
  // 安全：API Key 不持久化到 localStorage，只保留在内存中
  // 持久化 provider/model/base_url，但不包含 apiKey
  persist: {
    storage: localStorage,
    pick: ['config'],
    serializer: {
      // 只持久化非敏感配置
      deserialize: (value: string) => {
        try {
          const parsed = JSON.parse(value)
          if (parsed.config) {
            // 移除敏感信息
            parsed.config.apiKey = ''
          }
          return parsed
        } catch {
          return { config: { apiKey: '' } }
        }
      },
      serialize: (value: object) => {
        // 序列化时移除敏感信息
        const safe = JSON.parse(JSON.stringify(value))
        if (safe.config) {
          safe.config.apiKey = ''
        }
        return JSON.stringify(safe)
      },
    },
  },
})

function normalizeProvider(provider: unknown): LLMConfig['apiType'] {
  if (provider === 'claude') return 'anthropic'
  if (provider === 'other') return 'custom'
  if (
    provider === 'openai' ||
    provider === 'ollama' ||
    provider === 'anthropic' ||
    provider === 'deepseek' ||
    provider === 'custom'
  ) {
    return provider
  }
  return 'openai'
}

function normalizeConfig(raw: Record<string, unknown>): LLMConfig {
  return {
    apiType: normalizeProvider(raw.apiType ?? raw.api_type),
    apiUrl: String(raw.apiUrl ?? raw.api_url ?? ''),
    apiKey: String(raw.apiKey ?? raw.api_key ?? ''),
    model: String(raw.model ?? ''),
    thinking: Boolean(raw.thinking),
  }
}
