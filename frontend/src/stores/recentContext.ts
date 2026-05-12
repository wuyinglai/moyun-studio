import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

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

  return { content, isLoading, load, save }
})
