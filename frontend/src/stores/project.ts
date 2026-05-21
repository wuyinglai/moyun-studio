import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { ProjectInfo, ProjectCreateRequest } from '@/shared/api/types'

/** Store-level project type — ProjectInfo with defaults applied (required fields) */
export interface Project extends ProjectInfo {
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

export type CreateProjectParams = ProjectCreateRequest

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const pendingGeneration = ref<{ filePath: string; prompt: string; promptType?: string; extraVars?: Record<string, string> } | null>(null)

  async function loadProjects() {
    isLoading.value = true
    try {
      const result = await api.get<{ projects: Record<string, unknown>[]; total: number }>(API_ROUTES.projects)
      projects.value = (result?.projects || []).map(normalizeProject)
    } finally {
      isLoading.value = false
    }
  }

  async function createProject(params: CreateProjectParams) {
    isCreating.value = true
    try {
      const raw = await api.post<Record<string, unknown>>(API_ROUTES.projects, {
        name: params.name || '新项目',
        author: params.author || '',
        genre: params.genre || '',
        tone: params.tone || '',
        background: params.background || '',
        theme: params.theme || '',
        writing_style: params.writing_style || '',
        target_word_count: params.target_word_count || 50000,
      })
      const project = normalizeProject(raw)
      projects.value.push(project)
      currentProject.value = project
      return project
    } finally {
      isCreating.value = false
    }
  }

  async function openProject(id: string) {
    const raw = await api.get<Record<string, unknown>>(API_ROUTES.projectDetail(id))
    const project = normalizeProject(raw)
    currentProject.value = project
    return project
  }

  async function deleteProject(id: string) {
    await api.delete(API_ROUTES.projectDetail(id))
    projects.value = projects.value.filter((p) => p.id !== id)
    if (currentProject.value?.id === id) {
      currentProject.value = null
    }
  }

  async function updateProject(id: string, data: Partial<Project>) {
    const raw = await api.put<Record<string, unknown>>(API_ROUTES.projectDetail(id), data)
    const updated = normalizeProject(raw)
    const index = projects.value.findIndex((p) => p.id === id)
    if (index !== -1) {
      projects.value[index] = updated
    }
    if (currentProject.value?.id === id) {
      currentProject.value = updated
    }
    return updated
  }

  function closeProject() {
    currentProject.value = null
  }

  function setPendingGeneration(val: { filePath: string; prompt: string; promptType?: string; extraVars?: Record<string, string> } | null) {
    pendingGeneration.value = val
  }

  function calculateCompletion(project: Project): number {
    if (!project.target_word_count) return 0
    return Math.round((project.total_words / project.target_word_count) * 100)
  }

  return {
    projects,
    currentProject,
    isLoading,
    isCreating,
    loadProjects,
    createProject,
    openProject,
    deleteProject,
    updateProject,
    closeProject,
    calculateCompletion,
    pendingGeneration,
    setPendingGeneration,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['currentProject'],
  },
})

function normalizeProject(p: Record<string, unknown>): Project {
  const pid = (p.project_id as string) || (p.id as string)
  return {
    id: pid,
    project_id: pid,
    name: (p.name as string) || '',
    author: (p.author as string) || '',
    genre: (p.genre as string) || '',
    tone: (p.tone as string) || '',
    background: (p.background as string) || '',
    theme: (p.theme as string) || '',
    writing_style: (p.writing_style as string) || '',
    target_word_count: (p.target_word_count as number) || 0,
    completion_rate: (p.completion_rate as number) || 0,
    total_words: (p.total_words as number) || 0,
    created_at: (p.created_at as string) || '',
    updated_at: (p.updated_at as string) || '',
    scene_target_chars: (p.scene_target_chars as number) || 800,
    scenes_per_chapter: (p.scenes_per_chapter as number) || 5,
    chapters_per_volume: (p.chapters_per_volume as number) || 12,
    unit_label: (p.unit_label as string) || 'scene',
  }
}
