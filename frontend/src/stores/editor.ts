import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useFileStore } from './file'
import { useProjectStore } from './project'
import { countWords } from '@/utils/wordCount'

export const useEditorStore = defineStore('editor', () => {
  const contents = ref<Record<string, string>>({})
  const frontmatter = ref<Record<string, Record<string, unknown>>>({})
  const currentFilePath = ref<string | null>(null)
  // 文件路径 → 最后一次用于生成该文件的 prompt
  const filePrompts = ref<Record<string, string>>({})
  // 内容来源标记：'local' = 用户本地编辑，'external' = AI生成等外部更新
  const contentSource = ref<'local' | 'external'>('local')
  const isDirty = computed(() => {
    const fileStore = useFileStore()
    return fileStore.unsavedFiles.size > 0
  })
  const wordCount = computed(() => {
    if (!currentFilePath.value) return 0
    return countWords(contents.value[currentFilePath.value] || '')
  })
  const cursorPosition = ref({ line: 1, col: 1 })

  // 按 projectId 隔离的编辑器状态（持久化）
  const perProjectData = ref<Record<string, { currentFilePath: string | null; filePrompts: Record<string, string> }>>({})

  function loadContent(path: string, content: string, fm?: Record<string, unknown>) {
    contents.value[path] = content
    if (fm) {
      frontmatter.value[path] = fm
    }
  }

  function updateContent(path: string, content: string) {
    contents.value[path] = content
    const fileStore = useFileStore()
    fileStore.markDirty(path)
  }

  function clearFile(path: string) {
    delete contents.value[path]
    delete frontmatter.value[path]
  }

  function getContent(path: string) {
    return contents.value[path] || ''
  }

  function setContent(content: string) {
    if (currentFilePath.value) {
      contents.value[currentFilePath.value] = content
    }
  }

  function setCurrentFile(path: string | null) {
    currentFilePath.value = path
  }

  function appendContent(content: string) {
    if (currentFilePath.value) {
      const current = contents.value[currentFilePath.value] || ''
      contents.value[currentFilePath.value] = current + content
      const fileStore = useFileStore()
      fileStore.markDirty(currentFilePath.value)
    }
  }

  /** 追加内容到指定文件（AI 生成等外部更新使用，同时标记 contentSource） */
  function appendContentToFile(path: string, content: string) {
    contentSource.value = 'external'
    const current = contents.value[path] || ''
    contents.value[path] = current + content
    const fileStore = useFileStore()
    fileStore.markDirty(path)
    // 不自动重置 contentSource，由 MarkdownEditor 的 watcher 在更新编辑器后重置
  }

  function setFilePrompt(path: string, prompt: string) {
    if (prompt) {
      filePrompts.value[path] = prompt
    }
  }

  function getFilePrompt(path: string): string {
    return filePrompts.value[path] || ''
  }

  /** 标记本地编辑已发生，用于防止外部更新覆盖本地编辑 */
  function markLocalEdit() {
    contentSource.value = 'local'
  }

  // ─── 按 projectId 隔离：切换项目时保存/恢复 currentFilePath/filePrompts ───
  watch(
    () => useProjectStore().currentProject,
    (newProj, oldProj) => {
      if (oldProj) {
        perProjectData.value[oldProj.id] = {
          currentFilePath: currentFilePath.value,
          filePrompts: { ...filePrompts.value },
        }
      }
      currentFilePath.value = null
      filePrompts.value = {}
      if (newProj && perProjectData.value[newProj.id]) {
        const saved = perProjectData.value[newProj.id]
        if (saved.currentFilePath) currentFilePath.value = saved.currentFilePath
        if (saved.filePrompts) filePrompts.value = saved.filePrompts
      }
    },
  )

  return {
    contents,
    frontmatter,
    filePrompts,
    contentSource,
    isDirty,
    wordCount,
    cursorPosition,
    currentFilePath,
    loadContent,
    updateContent,
    appendContent,
    appendContentToFile,
    clearFile,
    getContent,
    setContent,
    setCurrentFile,
    setFilePrompt,
    getFilePrompt,
    markLocalEdit,
    perProjectData,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['perProjectData'],
  },
})
