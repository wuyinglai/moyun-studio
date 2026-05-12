// 文件树相关类型

export interface FileNode {
  id: string
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  expanded?: boolean
  // 扩展信息
  word_count?: number
  modified?: string
}

export interface FileTree {
  project_id: string
  nodes: FileNode[]
}

export interface FileContent {
  path: string
  name: string
  content: string
  frontmatter?: Record<string, unknown>
  word_count: number
  modified_at?: string
}
