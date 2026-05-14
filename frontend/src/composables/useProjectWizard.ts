import { ref } from 'vue'
import { useProjectStore } from '@/stores/project'

export const useProjectWizard = () => {
  const projectStore = useProjectStore()

  // 创作参数
  const params = ref({
    name: '',
    genre: '',
    tone: '',
    background: '',
    theme: '',
    writing_style: '',
    author: '',
    target_word_count: 50000,
  })

  const isGenerating = ref(false)

  async function createProject(params: typeof params.value) {
    if (!params.genre) {
      throw new Error('请选择题材')
    }
    isGenerating.value = true
    try {
      const project = await projectStore.createProject({
        name: params.name || '新项目',
        genre: params.genre,
        tone: params.tone,
        background: params.background,
        theme: params.theme,
        writing_style: params.writing_style,
        author: params.author,
        target_word_count: params.target_word_count,
      })
      return project
    } finally {
      isGenerating.value = false
    }
  }

  function reset() {
    params.value = {
      name: '',
      genre: '',
      tone: '',
      background: '',
      theme: '',
      writing_style: '',
      author: '',
      target_word_count: 50000,
    }
    isGenerating.value = false
  }

  return {
    params,
    isGenerating,
    createProject,
    reset,
  }
}
