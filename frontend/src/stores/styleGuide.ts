import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'

export const useStyleGuideStore = defineStore('styleGuide', () => {
  const content = ref('')
  const isLoading = ref(false)

  async function load(projectId: string) {
    isLoading.value = true
    try {
      const data = await api.get(API_ROUTES.file, {
        params: { project_id: projectId, path: 'style-guide.md' },
      })
      content.value = data?.content || ''
    } catch {
      content.value = ''
    } finally {
      isLoading.value = false
    }
  }

  async function save(projectId: string) {
    await api.post(`${API_ROUTES.file}?project_id=${projectId}`, {
      path: 'style-guide.md',
      content: content.value,
    })
  }

  return { content, isLoading, load, save }
})
