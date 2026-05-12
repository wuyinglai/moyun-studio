/**
 * 文风指南服务 - 读写 style-guide.md
 */
import api from '@/services/api'

export const styleGuideService = {
  load(projectId: string) {
    return api.get<{ content: string }>('/file', {
      params: { project_id: projectId, path: 'style-guide.md' },
    })
  },

  save(projectId: string, content: string) {
    return api.post('/file', {
      project_id: projectId,
      path: 'style-guide.md',
      content,
    })
  },
}
