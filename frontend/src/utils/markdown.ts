/**
 * Markdown 渲染工具
 * 使用 marked.js 解析 + DOMPurify 过滤 XSS
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked 选项
marked.setOptions({
  breaks: true,    // 换行符转为 <br>
  gfm: true,       // GitHub 风格 Markdown
})

// DOMPurify 允许的标签和属性（白名单）
const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'del',
  'code', 'pre', 'blockquote',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  'a', 'img',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'hr', 'span',
]

const ALLOWED_ATTR = ['href', 'src', 'alt', 'title', 'class', 'target']

/**
 * 将 Markdown 字符串渲染为安全的 HTML
 */
export function renderMarkdown(content: string): string {
  if (!content) return ''
  const html = marked.parse(content, { async: false }) as string
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    // 强制在新窗口打开链接
    ADD_ATTR: ['target'],
  })
}

/**
 * 提取纯文本（去除所有 Markdown 格式）
 */
export function stripMarkdown(content: string): string {
  if (!content) return ''
  // 去除 Markdown 语法，保留纯文本
  return content
    .replace(/#{1,6}\s+/g, '')           // 标题
    .replace(/\*\*(.+?)\*\*/g, '$1')     // 粗体
    .replace(/\*(.+?)\*/g, '$1')         // 斜体
    .replace(/`(.+?)`/g, '$1')           // 行内代码
    .replace(/```[\s\S]*?```/g, '')       // 代码块
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')   // 链接
    .replace(/!\[.*?\]\(.+?\)/g, '')      // 图片
    .replace(/^>\s+/gm, '')               // 引用
    .replace(/^[-*+]\s+/gm, '')           // 无序列表
    .replace(/^\d+\.\s+/gm, '')          // 有序列表
    .replace(/---+/g, '')                 // 分隔线
    .trim()
}

/**
 * 统计 Markdown 内容的字数
 */
export function countWords(content: string): number {
  const plain = stripMarkdown(content)
  // 中文按字符计，英文按单词计
  const chineseChars = (plain.match(/[\u4e00-\u9fa5]/g) || []).length
  const englishWords = plain
    .replace(/[\u4e00-\u9fa5]/g, '')
    .replace(/[^\w\s]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length
  return chineseChars + englishWords
}
