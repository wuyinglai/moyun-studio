/**
 * usePromptSync
 *
 * 切换编辑器文件时，在右侧面板同步显示该文件关联的 prompt。
 */

import { watch } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useRightPanelStore } from '@/stores/rightPanel'
import { usePipelineStore } from '@/stores/pipeline'
import { getPipelineForFile, guessPromptType } from '@/utils/promptTypes'
import { isSceneFile } from '@/modules/scene/scenePath'
import { API_ROUTES, API_BASE } from '@/shared/api/routes'

export function usePromptSync() {
  const editorStore = useEditorStore()
  const projectStore = useProjectStore()
  const rightPanelStore = useRightPanelStore()
  const pipelineStore = usePipelineStore()

  watch(
    () => editorStore.currentFilePath,
    async (path) => {
      if (!path) return

      const saved = editorStore.getFilePrompt(path)
      if (saved) {
        rightPanelStore.updatePrompt(saved)
        return
      }

      // 优先从 pipeline 定义加载 prompt
      const pipelineName = isSceneFile(path) ? 'generate' : getPipelineForFile(path)
      if (pipelineName) {
        try {
          await pipelineStore.fetchPipelineDetail(pipelineName)
          const step = pipelineStore.currentDetail?.steps?.[0]
          if (step?.prompt_content) {
            editorStore.setFilePrompt(path, step.prompt_content)
            rightPanelStore.updatePrompt(step.prompt_content)
            return
          }
        } catch {
          // pipeline 加载失败，fallback 到 guessPromptType
        }
      }

      // 没有已保存的 prompt 也不是 pipeline 文件，根据文件类型加载默认模板
      const promptType = guessPromptType(path)
      if (!promptType) return

      try {
        const res = await fetch(API_BASE + API_ROUTES.prompts(promptType) + `?project_id=${projectStore.currentProject?.id || ''}`)
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
