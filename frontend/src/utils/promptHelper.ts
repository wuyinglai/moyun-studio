/**
 * Prompt 变量替换工具
 * 支持：
 * - @{filepath}  → 加载文件内容
 * - {{ story_state }}  → 加载故事状态
 * - {{ style_guide }} → 加载文风指南
 * - {{ recent_context }} → 加载近期上下文
 */

import api from '@/services/api'
import { useStoryStateStore } from '@/stores/storyState'
import { useStyleGuideStore } from '@/stores/styleGuide'
import { useRecentContextStore } from '@/stores/recentContext'
import { useProjectStore } from '@/stores/project'

// 变量正则：@{filepath} 或 {{ variable }}
const VARIABLE_PATTERN = /(@\{[^}]+\}|\{\{\s*\w+(\.\w+)*\s*\}\})/g

export interface VariableRef {
  fullMatch: string
  type: 'file' | 'context'
  name: string
  path?: string
}

/**
 * 解析 Prompt 模板中的变量引用
 */
export function parseVariableRefs(template: string): VariableRef[] {
  const refs: VariableRef[] = []
  let match: RegExpExecArray | null

  // 重置 lastIndex
  VARIABLE_PATTERN.lastIndex = 0

  while ((match = VARIABLE_PATTERN.exec(template)) !== null) {
    const fullMatch = match[0]
    if (fullMatch.startsWith('@{')) {
      // 文件引用：@{filepath}
      refs.push({
        fullMatch,
        type: 'file',
        name: 'file',
        path: fullMatch.slice(2, -1).trim(),
      })
    } else {
      // 上下文引用：{{ variable_name }}
      const name = fullMatch.slice(2, -2).trim()
      refs.push({
        fullMatch,
        type: 'context',
        name,
      })
    }
  }
  return refs
}

/**
 * 替换 Prompt 模板中的变量
 */
export async function resolvePromptTemplate(
  template: string,
  projectId?: string
): Promise<string> {
  let result = template
  const refs = parseVariableRefs(template)

  for (const ref of refs) {
    try {
      let value = ''

      if (ref.type === 'file' && ref.path) {
        // 加载文件内容
        const data = await api.get('/file', {
          params: { project_id: projectId, path: ref.path },
        })
        value = data?.content || ''
      } else if (ref.type === 'context' && projectId) {
        // 加载上下文变量
        value = await resolveContextVariable(ref.name, projectId)
      }

      result = result.replace(ref.fullMatch, value)
    } catch (e) {
      console.warn(`无法解析变量 ${ref.fullMatch}:`, e)
      result = result.replace(ref.fullMatch, `[无法加载: ${ref.fullMatch}]`)
    }
  }

  return result
}

/**
 * 解析上下文变量（story_state、style_guide 等）
 */
async function resolveContextVariable(name: string, projectId: string): Promise<string> {
  switch (name.toLowerCase()) {
    case 'story_state':
    case 'storystate': {
      const store = useStoryStateStore()
      await store.load(projectId)
      return store.content
    }
    case 'style_guide':
    case 'styleguide': {
      const store = useStyleGuideStore()
      await store.load(projectId)
      return store.content
    }
    case 'recent_context':
    case 'recentcontext': {
      const store = useRecentContextStore()
      await store.load(projectId)
      return store.content
    }
    default:
      return `[未知变量: ${name}]`
  }
}

/**
 * 高亮显示 Prompt 中的变量引用（用于编辑器展示）
 */
export function highlightVariables(template: string): string {
  return template.replace(
    VARIABLE_PATTERN,
    (match) => `<span class="prompt-variable">${match}</span>`
  )
}
