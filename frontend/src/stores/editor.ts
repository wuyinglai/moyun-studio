import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useFileStore } from './file'

export const useEditorStore = defineStore('editor', () => {
  const contents = ref<Record<string, string>>({})
  const frontmatter = ref<Record<string, Record<string, unknown>>({})
  const currentFilePath = ref<string | null>(null)
  const isDirty = computed(() => {
    const fileStore = useFileStore()
    return fileStore.unsavedFiles.size > 0
  })
  const wordCount = ref(0)
  const cursorPosition = ref({ line: 1, col: 1 })

  function loadContent(path: string, content: string, fm?: Record<string, unknown>) {
    contents.value[path] = content
    if (fm) {
      frontmatter.value[path] = fm
    }
    updateWordCount(path)
  }

  function updateContent(path: string, content: string) {
    contents.value[path] = content
    updateWordCount(path)
    const fileStore = useFileStore()
    fileStore.markDirty(path)
  }

  function updateWordCount(path: string) {
    const content = contents.value[path] || ''
    const text = content.replace(/[#*`_~\[\]()]/g, '').trim()
    wordCount.value = text.length
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
      updateWordCount(currentFilePath.value)
    }
  }

  function setCurrentFile(path: string | null) {
    currentFilePath.value = path
  }

  function appendContent(content: string) {
    if (currentFilePath.value) {
      const current = contents.value[currentFilePath.value] || ''
      contents.value[currentFilePath.value] = current + content
      updateWordCount(currentFilePath.value)
      const fileStore = useFileStore()
      fileStore.markDirty(currentFilePath.value)
    }
  }

  function insertContent(content: string) {
    // 供 PromptPanel / AI 生成调用，插入到当前光标位置
    // 实际插入由 MarkdownEditor 组件通过 v-model 或ref完成
    // 此 action 负责更新 store 中的内容
    if (currentFilePath.value) {
      contents.value[currentFilePath.value] = (contents.value[currentFilePath.value] || '') + content
      updateWordCount(currentFilePath.value)
      const fileStore = useFileStore()
      fileStore.markDirty(currentFilePath.value)
    }
  }

  return {
    contents,
    frontmatter,
    isDirty,
    wordCount,
    cursorPosition,
    currentFilePath,
    loadContent,
    updateContent,
    appendContent,
    updateWordCount,
    clearFile,
    getContent,
    setContent,
    setCurrentFile,
    insertContent,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['currentFilePath'],
  },
})
