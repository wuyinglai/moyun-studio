/**
 * 项目服务 - 封装 /api/projects 相关操作
 */
import api from './api'
import type { Project, CreateProjectDTO } from '@/types/project'

export const projectService = {
  /** 获取所有项目列表 */
  list() {
    return api.get<{ projects: Record<string, unknown>[]; total: number }>('/projects')
  },

  /** 获取单个项目 */
  get(id: string) {
    return api.get<Record<string, unknown>>(`/projects/${id}`)
  },

  /** 创建项目 */
  create(data: CreateProjectDTO) {
    return api.post<Record<string, unknown>>('/projects', data)
  },

  /** 更新项目 */
  update(id: string, data: Partial<Project>) {
    return api.put<Record<string, unknown>>(`/projects/${id}`, data)
  },

  /** 删除项目 */
  delete(id: string) {
    return api.delete(`/projects/${id}`)
  },

  // ===== Wizard 流程 =====

  /** 生成书名创意 */
  generateIdea(params: CreateProjectDTO) {
    return api.post<{ name: string; description: string }>('/wizard/generate-idea', params)
  },

  /** 生成大纲 */
  generateOutline(projectId: string, params: Record<string, unknown>) {
    return api.post<{ outline: string; chapters: unknown[] }>(
      `/wizard/${projectId}/generate-outline`,
      { project_id: projectId, ...params }
    )
  },

  /** 确认大纲并创建目录 */
  confirmOutline(projectId: string, outline: string) {
    return api.post(`/wizard/${projectId}/confirm-outline`, {
      project_id: projectId,
      outline,
    })
  },
}
