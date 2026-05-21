// 文件树相关类型 — 核心类型已迁移到 @/shared/api/types

export type { FileTreeNode, FileReadResponse } from '@/shared/api/types'

/** UI-only: 文件树节点（含展开状态等前端扩展字段） */
export interface FileNode {
  id: string
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  expanded?: boolean
  word_count?: number
  modified?: string
}

/** UI-only: 文件树 */
export interface FileTree {
  project_id: string
  nodes: FileNode[]
}

/** UI-only: 文件内容（含 name、word_count 等展示字段） */
export interface FileContent {
  path: string
  name: string
  content: string
  frontmatter?: Record<string, unknown>
  word_count: number
  modified_at?: string
}
