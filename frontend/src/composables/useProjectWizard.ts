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

  async function createProject(p: typeof params.value) {
    if (!p.genre) {
      throw new Error('请选择题材')
    }
    isGenerating.value = true
    try {
      const project = await projectStore.createProject({
        name: p.name || '新项目',
        genre: p.genre,
        tone: p.tone,
        background: p.background,
        theme: p.theme,
        writing_style: p.writing_style,
        author: p.author,
        target_word_count: p.target_word_count,
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
