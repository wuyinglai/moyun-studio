import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useFileStore } from './file'
import { countWords } from '@/utils/wordCount'

export const useEditorStore = defineStore('editor', () => {
  const contents = ref<Record<string, string>>({})
  const frontmatter = ref<Record<string, Record<string, unknown>>>({})
  const currentFilePath = ref<string | null>(null)
  // 文件路径 → 最后一次用于生成该文件的 prompt
  const filePrompts = ref<Record<string, string>>({})
  const isDirty = computed(() => {
    const fileStore = useFileStore()
    return fileStore.unsavedFiles.size > 0
  })
  const wordCount = computed(() => {
    if (!currentFilePath.value) return 0
    return countWords(contents.value[currentFilePath.value] || '')
  })
  const cursorPosition = ref({ line: 1, col: 1 })

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

  function setFilePrompt(path: string, prompt: string) {
    if (prompt) {
      filePrompts.value[path] = prompt
    }
  }

  function getFilePrompt(path: string): string {
    return filePrompts.value[path] || ''
  }

  return {
    contents,
    frontmatter,
    filePrompts,
    isDirty,
    wordCount,
    cursorPosition,
    currentFilePath,
    loadContent,
    updateContent,
    appendContent,
    clearFile,
    getContent,
    setContent,
    setCurrentFile,
    setFilePrompt,
    getFilePrompt,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['currentFilePath', 'filePrompts'],
  },
})
