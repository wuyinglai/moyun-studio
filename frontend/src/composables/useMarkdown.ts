/**
 * useMarkdown - Markdown 解析 composable
 * 对 utils/markdown.ts 的响应式封装
 */
import { computed } from 'vue'
import { renderMarkdown, stripMarkdown, countWords } from '@/utils/markdown'

export function useMarkdown(source: { value: string }) {
  /** 渲染后的 HTML */
  const html = computed(() => renderMarkdown(source.value))

  /** 纯文本 */
  const plainText = computed(() => stripMarkdown(source.value))

  /** 字数统计 */
  const wordCount = computed(() => countWords(source.value))

  return {
    html,
    plainText,
    wordCount,
  }
}
