/** 墨韵配置服务 — 与 workspace/.config.json 同步（G0104） */

import api from '@/services/api'

export interface AppConfig {
  theme: string
  autoMode: string
  layout: { left: number; right: number; editorChat: number }
  llm: Record<string, any>
  customParams: Record<string, any>
}

export async function getConfig(): Promise<AppConfig> {
  return api.get<AppConfig>('/config')
}

export async function saveConfig(partial: Partial<AppConfig>): Promise<AppConfig> {
  return api.put<AppConfig>('/config', partial)
}
