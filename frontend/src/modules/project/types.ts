/** 项目模块 - 类型定义 — 核心类型已迁移到 @/shared/api/types */

export type { ProjectInfo as Project, ProjectCreateRequest as CreateProjectParams } from '@/shared/api/types'

/** UI-only: 项目列表项（精简字段） */
export interface ProjectListItem {
  id: string
  name: string
  genre?: string
  created_at?: string
  total_words?: number
  completion_rate?: number
}
