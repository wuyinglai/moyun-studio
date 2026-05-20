/** 项目模块 - API 调用 */

import api from '@/services/api'
import type { Project, CreateProjectParams, ProjectListItem } from './types'

/** 获取项目列表 */
export async function listProjects(): Promise<ProjectListItem[]> {
  const res = await api.get<{ projects: ProjectListItem[] }>('/projects')
  return res.projects || []
}

/** 创建项目 */
export async function createProject(params: CreateProjectParams): Promise<Project> {
  return await api.post<Project>('/projects', params)
}

/** 获取项目详情 */
export async function getProject(projectId: string): Promise<Project> {
  return await api.get<Project>(`/projects/${projectId}`)
}

/** 更新项目 */
export async function updateProject(projectId: string, data: Partial<Project>): Promise<Project> {
  return await api.put<Project>(`/projects/${projectId}`, data)
}

/** 删除项目 */
export async function deleteProject(projectId: string): Promise<{ success: boolean }> {
  return await api.delete<{ success: boolean }>(`/projects/${projectId}`)
}
