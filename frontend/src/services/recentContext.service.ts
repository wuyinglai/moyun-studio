/**
 * 近期上下文服务 - 读写 recent-context.md
 */
import api from '@/services/api'

export const recentContextService = {
  load(projectId: string) {
    return api.get<{ content: string }>('/file', {
      params: { project_id: projectId, path: 'recent-context.md' },
    })
  },

  save(projectId: string, content: string) {
    return api.post('/file', {
      project_id: projectId,
      path: 'recent-context.md',
      content,
    })
  },

  /** 追加新上下文 */
  append(projectId: string, entry: string) {
    return api.post('/file/append', {
      project_id: projectId,
      path: 'recent-context.md',
      content: entry,
    })
  },
}
