import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface LLMConfig {
  apiType: 'openai' | 'ollama' | 'claude' | 'deepseek' | 'other'
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
  const availableModels = ref<string[]>([])

  async function loadConfig() {
    try {
      const data = await api.get<LLMConfig>('/llm/config')
      if (data) {
        config.value = data
      }
    } catch {
      // 配置不存在，使用默认
    }
  }

  async function saveConfig(cfg: Partial<LLMConfig>) {
    await api.post('/llm/config', { ...config.value, ...cfg })
    // 合并本地配置（后端仅保存，不返回完整配置）
    Object.assign(config.value, cfg)
  }

  async function testConnection(signal?: AbortSignal): Promise<boolean> {
    try {
      await api.post('/llm/test', config.value, { signal, timeout: 15000 })
      isConnected.value = true
      return true
    } catch {
      isConnected.value = false
      return false
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
    availableModels,
    loadConfig,
    saveConfig,
    testConnection,
    fetchModels,
    setThinking,
    setGenerating,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['config'],
  },
})
