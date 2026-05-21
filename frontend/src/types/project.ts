// 项目相关类型 — 核心类型已迁移到 @/shared/api/types

import type { ProjectInfo, ProjectCreateRequest } from '@/shared/api/types'

export type { ProjectInfo, ProjectCreateRequest } from '@/shared/api/types'

/** @deprecated Use ProjectInfo from @/shared/api/types */
export type Project = ProjectInfo

/** @deprecated Use ProjectCreateRequest from @/shared/api/types */
export type CreateProjectDTO = ProjectCreateRequest

/** UI-only: 项目列表项（精简字段） */
export interface ProjectListItem {
  id: string
  name: string
  author: string
  created_at: string
  completion_rate: number
  total_words: number
}
