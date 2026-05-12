import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useStoryStateStore = defineStore('storyState', () => {
  const content = ref('')
  const isLoading = ref(false)

  async function load(projectId: string) {
    isLoading.value = true
    try {
      const data = await api.get('/file', {
        params: { project_id: projectId, path: 'story-state.md' },
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
      path: 'story-state.md',
      content: content.value,
    })
  }

  async function updateAfterChapter(projectId: string, chapterContent: string) {
    // 每次生成章节后自动追加到 story-state.md
    const timestamp = new Date().toLocaleString()
    const entry = `\n\n## ${timestamp}\n\n${chapterContent}\n`
    content.value += entry
    await save(projectId)
  }

  return { content, isLoading, load, save, updateAfterChapter }
})
