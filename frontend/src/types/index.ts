// 全局类型导出
export * from './api'
export * from './project'
export * from './file'
export * from './editor'
export * from './chat'
export * from './llm'
export * from './task'

// 通知类型
export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  message: string
  autoClose: boolean
  duration?: number
}

// 主题类型
export type ThemeName = 'dark' | 'green' | 'gray'
