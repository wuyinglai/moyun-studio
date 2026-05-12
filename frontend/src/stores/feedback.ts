import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface Feedback {
  id: string
  chapter_path: string
  content: string
  created_at: string
}

export const useFeedbackStore = defineStore('feedback', () => {
  const feedbacks = ref<Feedback[]>([])
  const isLoading = ref(false)

  async function loadForChapter(projectId: string, chapterPath: string) {
    isLoading.value = true
    try {
      const data = await api.get<Feedback[]>('/feedback', {
        params: { project_id: projectId, chapter_path: chapterPath },
      })
      feedbacks.value = data || []
    } catch {
      feedbacks.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function addFeedback(projectId: string, chapterPath: string, content: string) {
    const feedback = await api.post<Feedback>('/feedback', {
      project_id: projectId,
      chapter_path: chapterPath,
      content,
    })
    feedbacks.value.push(feedback)
    return feedback
  }

  async function deleteFeedback(_projectId: string, feedbackId: string) {
    await api.delete(`/feedback/${feedbackId}`)
    feedbacks.value = feedbacks.value.filter((f) => f.id !== feedbackId)
  }

  return { feedbacks, isLoading, loadForChapter, addFeedback, deleteFeedback }
})
