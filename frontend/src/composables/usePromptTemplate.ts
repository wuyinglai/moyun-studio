/**
 * usePromptTemplate - Prompt 模板变量替换 composable
 */
import { ref } from 'vue'
import {
  resolvePromptTemplate,
  parseVariableRefs,
  highlightVariables,
} from '@/utils/promptHelper'
import type { VariableRef } from '@/utils/promptHelper'

export function usePromptTemplate() {
  const isResolving = ref(false)
  const variableRefs = ref<VariableRef[]>([])

  /**
   * 解析模板中的变量引用
   */
  function parse(template: string): VariableRef[] {
    variableRefs.value = parseVariableRefs(template)
    return variableRefs.value
  }

  /**
   * 替换模板中的变量（加载实际内容）
   */
  async function resolve(template: string, projectId?: string): Promise<string> {
    isResolving.value = true
    try {
      return await resolvePromptTemplate(template, projectId)
    } finally {
      isResolving.value = false
    }
  }

  /**
   * 高亮变量引用（用于编辑器展示）
   */
  function highlight(template: string): string {
    return highlightVariables(template)
  }

  return {
    isResolving,
    variableRefs,
    parse,
    resolve,
    highlight,
  }
}
