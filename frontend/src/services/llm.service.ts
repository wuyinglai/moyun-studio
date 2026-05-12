/**
 * LLM 服务 - 封装 /api/llm/* 相关操作
 */
import api from './api'
import type { LLMConfig, ModelInfo, ConnectionTestResult } from '@/types/llm'

export const llmService = {
  /** 获取当前 LLM 配置 */
  getConfig() {
    return api.get<LLMConfig>('/llm/config')
  },

  /** 保存 LLM 配置 */
  saveConfig(config: Partial<LLMConfig>) {
    return api.post('/llm/config', config)
  },

  /** 测试连接 */
  testConnection() {
    return api.post<ConnectionTestResult>('/llm/test')
  },

  /** 获取可用模型列表 */
  listModels() {
    return api.get<ModelInfo[]>('/llm/models')
  },
}
