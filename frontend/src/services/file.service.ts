/**
 * 文件服务 - 封装 /api/file 和 /api/tree 相关操作
 */
import api from './api'

export const fileService = {
  /** 获取项目文件树 */
  getTree(projectId: string) {
    return api.get<{ nodes: any[] }>('/tree', {
      params: { project_id: projectId },
    })
  },

  /** 读取文件内容 */
  read(projectId: string, path: string) {
    return api.get<{ content: string; word_count: number }>('/file', {
      params: { project_id: projectId, path },
    })
  },

  /** 写入文件 */
  write(projectId: string, path: string, content: string) {
    return api.post('/file', {
      project_id: projectId,
      path,
      content,
    })
  },

  /** 创建文件 */
  create(projectId: string, path: string) {
    return api.post('/file/create', {
      project_id: projectId,
      path,
    })
  },

  /** 删除文件 */
  remove(projectId: string, path: string) {
    return api.delete(`/file?project_id=${projectId}&path=${encodeURIComponent(path)}`)
  },

  /** 重命名文件 */
  rename(projectId: string, oldPath: string, newPath: string) {
    return api.post('/file/rename', {
      project_id: projectId,
      old_path: oldPath,
      new_path: newPath,
    })
  },
}
