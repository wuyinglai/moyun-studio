/**
 * useGenerationOrchestrator
 *
 * 管理项目创建后的自动生成流程：
 * 1. 监听 pendingGeneration
 * 2. 打开目标文件
 * 3. 触发流式生成
 * 4. 生成后保存元数据并重新加载编辑器内容
 */

import { watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { useWorkflowGuide } from './useWorkflowGuide'

export function useGenerationOrchestrator() {
  const projectStore = useProjectStore()
  const guide = useWorkflowGuide()

  watch(
    () => projectStore.pendingGeneration,
    async (pending) => {
      if (!pending || !projectStore.currentProject) return

      const llmStore = useLLMStore()
      if (!llmStore.isConnected) {
        useNotificationStore().warning('LLM 未配置，跳过自动生成')
        projectStore.setPendingGeneration(null)
        return
      }

      const projectId = projectStore.currentProject.id
      const { filePath, prompt } = pending
      const editorStore = useEditorStore()
      const fileStore = useFileStore()

      // 等待路由导航完成 + 文件树加载
      await new Promise(resolve => setTimeout(resolve, 500))

      // 打开目标文件
      editorStore.setFilePrompt(filePath, prompt)
      const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
      fileStore.openFile(node)
      editorStore.setCurrentFile(filePath)

      // 启动完整小说创作工作流（第一步就是生成书名与创意）
      useNotificationStore().info('正在生成创意...')
      await guide.start(projectId, filePath)
      projectStore.setPendingGeneration(null)
    },
  )
}

