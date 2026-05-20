/** 项目模块 - 类型定义 */

export interface Project {
  id: string
  project_id: string
  name: string
  author?: string
  genre?: string
  tone?: string
  background?: string
  theme?: string
  writing_style?: string
  target_word_count?: number
  completion_rate?: number
  total_words?: number
  created_at?: string
  updated_at?: string
  scene_target_chars?: number
  scenes_per_chapter?: number
  chapters_per_volume?: number
  unit_label?: string
}

export interface CreateProjectParams {
  name: string
  genre?: string
  tone?: string
  background?: string
  theme?: string
  writing_style?: string
  target_word_count?: number
  outline?: string
  book_name?: string
  book_description?: string
  scene_target_chars?: number
  scenes_per_chapter?: number
  chapters_per_volume?: number
  unit_label?: string
}

export interface ProjectListItem {
  id: string
  name: string
  genre?: string
  created_at?: string
  total_words?: number
  completion_rate?: number
}
