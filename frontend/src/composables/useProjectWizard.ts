/**
 * 新建项目工作流程
 * 实现 G0107 描述的三步骤流程
 */

import { ref, computed } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useNotificationStore } from '@/stores/notification'

export interface BookIdea {
  name: string
  description: string
}

export interface ChapterInfo {
  id: string
  name: string
  sections: number
}

export interface Outline {
  content?: string
  outline: string
  chapters: ChapterInfo[]
}

export const useProjectWizard = () => {
  const projectStore = useProjectStore()
  const fileStore = useFileStore()
  const notification = useNotificationStore()

  // 当前步骤
  const currentStep = ref(1)

  // 创作参数
  const params = ref({
    genre: '',
    tone: '',
    background: '',
    theme: '',
    writing_style: '',
    author: '',
    target_word_count: 50000,
  })

  // 书名和创意
  const bookIdea = ref<BookIdea | null>(null)

  // 大纲
  const outline = ref<Outline | null>(null)

  // 编辑后的大纲
  const editedOutline = ref('')

  // 是否正在生成
  const isGenerating = ref(false)

  // 预估章节数
  const estimatedChapters = computed(() => {
    const sections = Math.ceil(params.value.target_word_count / 1800)
    return Math.ceil(sections / 4)
  })

  // 预估卷数
  const estimatedVolumes = computed(() => {
    const ch = estimatedChapters.value
    return Math.ceil(ch / 12) // 平均每卷 12 章
  })

  /**
   * 步骤1：生成书名和创意
   */
  async function generateBookIdea() {
    if (!params.value.genre) {
      notification.warning('请选择题材')
      return
    }

    isGenerating.value = true
    try {
      const result = await projectStore.generateBookIdea(params.value)
      bookIdea.value = result
      currentStep.value = 1.5 // 中间步骤：显示书名创意
    } catch (e) {
      notification.error('生成书名失败')
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * 接受书名创意，创建项目并继续步骤2
   */
  async function acceptBookIdea() {
    if (!bookIdea.value) return

    isGenerating.value = true
    try {
      // 先用书名创建项目（占位），后续 confirm-outline 时更新为最终名称
      const project = await projectStore.createProject({
        name: bookIdea.value.name,
        genre: params.value.genre,
        tone: params.value.tone,
        background: params.value.background,
        theme: params.value.theme,
        writing_style: params.value.writing_style,
        author: params.value.author,
        target_word_count: params.value.target_word_count,
      })
      projectStore.currentProject = project
      currentStep.value = 2
    } catch (e) {
      notification.error('创建项目失败')
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * 修改书名创意
   */
  function editBookIdea() {
    bookIdea.value = null
    currentStep.value = 1
  }

  /**
   * 步骤2：生成章节大纲
   */
  async function generateOutline(projectId: string) {
    isGenerating.value = true
    try {
      // 传递书名和创意描述
      const result = await projectStore.generateOutline(projectId, {
        ...params.value,
        book_name: bookIdea.value?.name || '',
        book_description: bookIdea.value?.description || '',
      })
      outline.value = result
      editedOutline.value = result.outline
      currentStep.value = 2.5 // 中间步骤：显示大纲
    } catch (e) {
      notification.error('生成大纲失败')
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * 接受大纲并生成目录结构
   */
  async function acceptOutlineAndCreate() {
    if (!projectStore.currentProject || !outline.value) return

    isGenerating.value = true
    try {
      const projectId = projectStore.currentProject.id

      // 确认大纲并生成目录结构
      await projectStore.confirmOutlineAndCreate(projectId, editedOutline.value)

      // 加载文件树
      await fileStore.loadTree(projectId)

      // 更新项目名为最终确认的书名（用户可能编辑过）
      if (bookIdea.value?.name) {
        await projectStore.updateProject(projectId, { name: bookIdea.value.name })
      }

      notification.success(`项目 "${bookIdea.value?.name}" 创建成功！`)
      currentStep.value = 3
    } catch (e) {
      notification.error('创建项目失败')
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * 修改大纲
   */
  function editOutline() {
    currentStep.value = 2
  }

  /**
   * 重置工作流程
   */
  function reset() {
    currentStep.value = 1
    params.value = {
      genre: '',
      tone: '',
      background: '',
      theme: '',
      writing_style: '',
      author: '',
      target_word_count: 50000,
    }
    bookIdea.value = null
    outline.value = null
    editedOutline.value = ''
    isGenerating.value = false
  }

  return {
    currentStep,
    params,
    bookIdea,
    outline,
    editedOutline,
    isGenerating,
    estimatedChapters,
    estimatedVolumes,
    generateBookIdea,
    acceptBookIdea,
    editBookIdea,
    generateOutline,
    acceptOutlineAndCreate,
    editOutline,
    reset,
  }
}
