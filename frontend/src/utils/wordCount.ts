/**
 * 字数统计工具
 */

/**
 * 计算字符串字数（中文按字符，英文按单词）
 */
export function countWords(content: string): number {
  if (!content) return 0
  const chineseChars = (content.match(/[\u4e00-\u9fa5]/g) || []).length
  const englishWords = content
    .replace(/[\u4e00-\u9fa5]/g, '')
    .replace(/[^\w\s]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length
  return chineseChars + englishWords
}

/**
 * 计算字符数（不含空格）
 */
export function countChars(content: string): number {
  return content.replace(/\s/g, '').length
}

/**
 * 格式化字数显示（1万字、10.5万字等）
 */
export function formatWordCount(count: number): string {
  if (count >= 10000) {
    return `${(count / 10000).toFixed(1)}万字`
  }
  return `${count}字`
}

/**
 * 估算 Token 数量（粗略：中文约 2 token/字，英文约 1.3 token/词）
 */
export function estimateTokens(content: string): number {
  if (!content) return 0
  const chineseChars = (content.match(/[\u4e00-\u9fa5]/g) || []).length
  const englishWords = content
    .replace(/[\u4e00-\u9fa5]/g, '')
    .replace(/[^\w\s]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length
  return Math.ceil(chineseChars * 2 + englishWords * 1.3)
}
