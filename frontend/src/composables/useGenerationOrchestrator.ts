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
import { useTaskStore } from '@/stores/task'
import { useLLMStore } from '@/stores/llm'
import { useFileMetaStore } from '@/stores/fileMeta'
import { useNotificationStore } from '@/stores/notification'
import { useFileGeneration } from './useFileGeneration'
import api from '@/services/api'

export function useGenerationOrchestrator() {
  const projectStore = useProjectStore()
  const fileGen = useFileGeneration()

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

      // 等待路由导航完成 + 文件树加载
      await new Promise(resolve => setTimeout(resolve, 500))

      // 打开文件
      const editorStore = useEditorStore()
      editorStore.setFilePrompt(filePath, prompt)
      const fileStore = useFileStore()
      const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
      fileStore.openFile(node)
      editorStore.setCurrentFile(filePath)

      try {
        const fileContent = await fileStore.readFile(projectId, filePath)
        if (fileContent) {
          editorStore.loadContent(filePath, fileContent.content || '')
        }
      } catch {
        // 文件可能尚未就绪
      }

      // 触发流式生成
      useNotificationStore().info('正在生成创意...')
      const taskStore = useTaskStore()
      const taskId = `gen-${Date.now()}`
      const taskName = `AI 生成: ${filePath.split('/').pop() || filePath}`
      taskStore.addTask(taskId, taskName)
      taskStore.startTask(taskId)

      try {
        await fileGen.generateToFile(projectId, filePath, prompt, pending.extraVars, pending.promptType)
        taskStore.completeTask(taskId)
        taskStore.addLog('success', `完成: ${taskName}`)

        // 保存元数据
        if (pending.promptType) {
          useFileMetaStore().saveMeta(projectId, filePath, {
            promptType: pending.promptType,
            extraVars: { ...(pending.extraVars || {}) },
            generatedAt: new Date().toISOString(),
          })
        }

        // 从磁盘重新加载内容到编辑器
        try {
          const result = await fileStore.readFile(projectId, filePath)
          if (result && result.content) {
            editorStore.loadContent(filePath, result.content)
          }
        } catch {}
      } catch (e: any) {
        taskStore.failTask(taskId)
        taskStore.addLog('error', `失败: ${taskName}`)
        console.error('自动生成失败:', e)
      }

      projectStore.setPendingGeneration(null)
    },
  )
}
