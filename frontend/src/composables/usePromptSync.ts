/**
 * usePromptSync
 *
 * 切换编辑器文件时，在右侧面板同步显示该文件关联的 prompt。
 */

import { watch } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useRightPanelStore } from '@/stores/rightPanel'
import { guessPromptType } from '@/utils/promptTypes'

export function usePromptSync() {
  const editorStore = useEditorStore()
  const projectStore = useProjectStore()
  const rightPanelStore = useRightPanelStore()

  watch(
    () => editorStore.currentFilePath,
    async (path) => {
      if (!path) return

      const saved = editorStore.getFilePrompt(path)
      if (saved) {
        rightPanelStore.updatePrompt(saved)
        return
      }

      // 没有已保存的 prompt，根据文件类型加载默认模板
      const promptType = guessPromptType(path)
      if (!promptType) return

      try {
        const res = await fetch(`/api/prompts/${promptType}?project_id=${projectStore.currentProject?.id || ''}`)
        const json = await res.json()
        if (json?.data?.content) {
          editorStore.setFilePrompt(path, json.data.content)
          rightPanelStore.updatePrompt(json.data.content)
        }
      } catch {
        // 静默失败
      }
    },
  )
}
