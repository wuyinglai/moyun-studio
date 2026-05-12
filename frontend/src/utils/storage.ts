/**
 * localStorage 封装
 * 提供类型安全的存取接口
 */

/**
 * 获取存储值，不存在返回默认值
 */
export function getStorage<T>(key: string, defaultValue: T): T {
  try {
    const stored = localStorage.getItem(key)
    if (stored === null) return defaultValue
    return JSON.parse(stored) as T
  } catch {
    return defaultValue
  }
}

/**
 * 设置存储值
 */
export function setStorage<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (e) {
    console.warn('localStorage 设置失败:', key, e)
  }
}

/**
 * 删除存储值
 */
export function removeStorage(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch (e) {
    console.warn('localStorage 删除失败:', key, e)
  }
}

// 常用 key 常量
export const STORAGE_KEYS = {
  THEME: 'moyun-theme',
  LAYOUT_SIZES: 'moyun-layout-sizes',
  EDITOR_CHAT_SIZES: 'moyun-editor-chat-sizes',
  LLM_CONFIG: 'moyun-llm-config',
  RECENT_FILES: 'moyun-recent-files',
  PANEL_LEFT_WIDTH: 'moyun-panel-left-width',
  PANEL_RIGHT_WIDTH: 'moyun-panel-right-width',
} as const
