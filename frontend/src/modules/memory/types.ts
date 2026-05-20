/** 记忆模块 - 类型定义 */

export interface MemoryStatus {
  has_recent_context: boolean
  has_story_state: boolean
  recent_context_scenes: number
  last_updated?: string
}
