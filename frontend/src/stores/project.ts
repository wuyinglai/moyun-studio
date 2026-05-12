import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface Project {
  id: string   // computed alias for project_id
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

export interface CreateProjectParams {
  // 创作参数
  genre?: string
  tone?: string
  background?: string
  theme?: string
  writing_style?: string
  author?: string
  target_word_count?: number
  // 高级选项
  outline?: string // 大纲内容
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const createStep = ref(1) // 1: 创作参数, 2: 生成大纲, 3: 确认大纲

  async function loadProjects() {
    isLoading.value = true
    try {
      const result = await api.get<{ projects: Record<string, unknown>[]; total: number }>('/projects')
      projects.value = (result?.projects || []).map(normalizeProject)
    } finally {
      isLoading.value = false
    }
  }

  async function createProject(params: CreateProjectParams) {
    isCreating.value = true
    createStep.value = 1
    try {
      const raw = await api.post<Record<string, unknown>>('/projects', {
        name: params.genre || '新项目',
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

  async function generateBookIdea(params: CreateProjectParams) {
    createStep.value = 1
    return await api.post<{ name: string; description: string }>('/wizard/generate-idea', params)
  }

  async function generateOutline(projectId: string, params: CreateProjectParams & { book_name?: string; book_description?: string }) {
    createStep.value = 2
    const result = await api.post<{ outline: string; chapters: ChapterInfo[] }>(`/wizard/${projectId}/generate-outline`, {
      project_id: projectId,
      ...params,
    })
    createStep.value = 2.5
    return result
  }

  async function confirmOutlineAndCreate(projectId: string, outline: string) {
    createStep.value = 3
    await api.post(`/wizard/${projectId}/confirm-outline`, { project_id: projectId, outline })
  }

  async function openProject(id: string) {
    const raw = await api.get<Record<string, unknown>>(`/projects/${id}`)
    const project = normalizeProject(raw)
    currentProject.value = project
    return project
  }

  async function deleteProject(id: string) {
    await api.delete(`/projects/${id}`)
    projects.value = projects.value.filter((p) => p.id !== id)
    if (currentProject.value?.id === id) {
      currentProject.value = null
    }
  }

  async function updateProject(id: string, data: Partial<Project>) {
    const raw = await api.put<Record<string, unknown>>(`/projects/${id}`, data)
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

  function calculateCompletion(project: Project): number {
    if (!project.target_word_count) return 0
    return Math.round((project.total_words / project.target_word_count) * 100)
  }

  return {
    projects,
    currentProject,
    isLoading,
    isCreating,
    createStep,
    loadProjects,
    createProject,
    generateBookIdea,
    generateOutline,
    confirmOutlineAndCreate,
    openProject,
    deleteProject,
    updateProject,
    closeProject,
    calculateCompletion,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['projects', 'currentProject', 'createStep'],
  },
})

interface ChapterInfo {
  id: string
  name: string
  sections: number
}

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
  }
}
