/**
 * Markdown 预览功能
 */
import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useEditorStore } from '@/stores/editor'

export function useMarkdownPreview() {
  const editorStore = useEditorStore()
  const isPreviewMode = ref(false)
  const previewHtml = ref('')

  // 配置 marked
  marked.setOptions({
    gfm: true,
    breaks: true,
  })

  const currentContent = computed(() => {
    if (!editorStore.currentFilePath) return ''
    return editorStore.getContent(editorStore.currentFilePath) || ''
  })

  function togglePreview() {
    if (isPreviewMode.value) {
      // 关闭预览
      isPreviewMode.value = false
      previewHtml.value = ''
    } else {
      // 开启预览
      const rawHtml = marked.parse(currentContent.value) as string
      previewHtml.value = DOMPurify.sanitize(rawHtml)
      isPreviewMode.value = true
    }
  }

  function updatePreview() {
    if (isPreviewMode.value) {
      const rawHtml = marked.parse(currentContent.value) as string
      previewHtml.value = DOMPurify.sanitize(rawHtml)
    }
  }

  return {
    isPreviewMode,
    previewHtml,
    currentContent,
    togglePreview,
    updatePreview,
  }
}
