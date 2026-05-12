/**
 * 故事状态服务 - 读写 story-state.md
 */
import api from '@/services/api'

export const storyStateService = {
  load(projectId: string) {
    return api.get<{ content: string }>('/file', {
      params: { project_id: projectId, path: 'story-state.md' },
    })
  },

  save(projectId: string, content: string) {
    return api.post('/file', {
      project_id: projectId,
      path: 'story-state.md',
      content,
    })
  },

  /** 自动追加新内容到 story-state.md */
  append(projectId: string, newContent: string) {
    return api.post('/file/append', {
      project_id: projectId,
      path: 'story-state.md',
      content: newContent,
    })
  },
}
