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
    const data = await api.post<LLMConfig>('/llm/config', { ...config.value, ...cfg })
    config.value = data
  }

  async function testConnection(): Promise<boolean> {
    try {
      await api.post('/llm/test', config.value)
      isConnected.value = true
      return true
    } catch {
      isConnected.value = false
      return false
    }
  }

  async function fetchModels() {
    try {
      const data = await api.get<string[]>('/llm/models')
      availableModels.value = data || []
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
