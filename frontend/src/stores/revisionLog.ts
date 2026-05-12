import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface RevisionLog {
  id: string
  chapter_path: string
  old_content: string
  new_content: string
  reason: string
  created_at: string
}

export const useRevisionLogStore = defineStore('revisionLog', () => {
  const logs = ref<RevisionLog[]>([])
  const isLoading = ref(false)

  async function loadForChapter(projectId: string, chapterPath: string) {
    isLoading.value = true
    try {
      const data = await api.get<RevisionLog[]>('/revision-log', {
        params: { project_id: projectId, chapter_path: chapterPath },
      })
      logs.value = data || []
    } catch {
      logs.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function createLog(
    projectId: string,
    chapterPath: string,
    oldContent: string,
    newContent: string,
    reason: string
  ) {
    const log = await api.post<RevisionLog>('/revision-log', {
      project_id: projectId,
      chapter_path: chapterPath,
      old_content: oldContent,
      new_content: newContent,
      reason,
    })
    logs.value.push(log)
    return log
  }

  async function restoreRevision(projectId: string, revisionId: string) {
    return await api.post('/revision-log/restore', {
      project_id: projectId,
      revision_id: revisionId,
    })
  }

  return { logs, isLoading, loadForChapter, createLog, restoreRevision }
})
