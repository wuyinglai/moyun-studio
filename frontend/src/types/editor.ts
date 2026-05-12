// 编辑器相关类型

export interface CursorPosition {
  line: number
  col: number
}

export interface EditorState {
  contents: Record<string, string>
  frontmatter: Record<string, Record<string, unknown>>
  isDirty: boolean
  wordCount: number
  cursorPosition: CursorPosition
}

export interface VersionSnapshot {
  id: string
  content: string
  timestamp: string
  reason?: string
}
