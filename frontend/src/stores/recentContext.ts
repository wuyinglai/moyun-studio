import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

const MAX_RECENT_CHAPTERS = 5

export const useRecentContextStore = defineStore('recentContext', () => {
  const content = ref('')
  const isLoading = ref(false)

  async function load(projectId: string) {
    isLoading.value = true
    try {
      const data = await api.get('/file', {
        params: { project_id: projectId, path: 'recent-context.md' },
      })
      content.value = data?.content || ''
    } catch {
      content.value = ''
    } finally {
      isLoading.value = false
    }
  }

  async function save(projectId: string) {
    await api.post(`/file?project_id=${projectId}`, {
      path: 'recent-context.md',
      content: content.value,
    })
  }

  async function appendChapter(projectId: string, chapterSummary: string) {
    const timestamp = new Date().toLocaleString()
    const entry = `\n\n## ${timestamp}\n\n${chapterSummary}\n`
    content.value += entry

    // 只保留最近5章摘要（按 ## 标题分割）
    const sections = content.value.split(/(?=^## )/m)
    if (sections.length > MAX_RECENT_CHAPTERS) {
      content.value = sections.slice(-MAX_RECENT_CHAPTERS).join('')
    }

    await save(projectId)
  }

  return { content, isLoading, load, save, appendChapter }
})
