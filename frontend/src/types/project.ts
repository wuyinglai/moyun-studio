// 项目相关类型

export interface Project {
  id: string
  project_id: string
  name: string
  author: string
  genre: string
  tone: string
  background: string
  theme: string
  writing_style: string
  target_word_count: number
  completion_rate: number
  total_words: number
  created_at: string
  updated_at: string
}

export interface CreateProjectDTO {
  name?: string
  author?: string
  genre?: string
  tone?: string
  background?: string
  theme?: string
  writing_style?: string
  target_word_count?: number
  // Wizard 流程用
  outline?: string
  book_name?: string
  book_description?: string
}

export interface ProjectListItem {
  id: string
  name: string
  author: string
  created_at: string
  completion_rate: number
  total_words: number
}
