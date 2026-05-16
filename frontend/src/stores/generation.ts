import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { useEditorStore } from './editor'
import { useTaskStore } from './task'
import type { BatchGenerateRequest, BatchGenerateResponse, ExtractTaskRequest, ExtractTaskResponse } from '@/types/chat'

export const useGenerationStore = defineStore('generation', () => {
  const isGenerating = ref(false)

  /**
   * 批量生成（调用 /api/generate/batch）
   */
  async function batchGenerate(req: BatchGenerateRequest): Promise<BatchGenerateResponse> {
    return await api.post<BatchGenerateResponse>('/generate/batch', req)
  }

  /**
   * 提取任务（调用 /api/extract）
   */
  async function extractTask(req: ExtractTaskRequest): Promise<ExtractTaskResponse> {
    return await api.post<ExtractTaskResponse>('/extract', req)
  }

  /**
   * 续写当前文件（仅任务管理，流式事件由 useSSE 处理）
   */
  async function continueWriting(projectId: string, filePath: string, prompt?: string) {
    const taskStore = useTaskStore()
    const editorStore = useEditorStore()

    if (prompt) {
      editorStore.setFilePrompt(filePath, prompt)
    }

    const taskId = `task-${Date.now()}`
    taskStore.addTask(taskId, `续写: ${filePath.split('/').pop()}`)
    taskStore.startTask(taskId)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          file_path: filePath,
          prompt_type: 'generate/continuation',
          extra_vars: prompt ? { user_prompt: prompt } : {},
          mode: 'append',
          stream: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      // 消费响应体（generation 事件由 useSSE 处理）
      await response.body?.getReader()?.cancel()

      // 根据自动化模式决定是否等待确认
      const autoMode = localStorage.getItem('moyun-auto-mode') || 'L1'
      if (autoMode === 'L1') {
        taskStore.waitForConfirm(taskId)
      } else {
        taskStore.completeTask(taskId)
      }
    } catch (e) {
      taskStore.failTask(taskId)
      throw e
    }
  }

  /**
   * 重写当前文件（仅任务管理，流式事件由 useSSE 处理）
   */
  async function rewriteContent(projectId: string, filePath: string, prompt?: string) {
    const taskStore = useTaskStore()
    const editorStore = useEditorStore()

    if (prompt) {
      editorStore.setFilePrompt(filePath, prompt)
    }

    const taskId = `task-${Date.now()}`
    taskStore.addTask(taskId, `重写: ${filePath.split('/').pop()}`)
    taskStore.startTask(taskId)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          file_path: filePath,
          prompt_type: 'generate/rewrite',
          extra_vars: prompt ? { user_prompt: prompt } : {},
          mode: 'rewrite',
          stream: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      await response.body?.getReader()?.cancel()

      const autoMode = localStorage.getItem('moyun-auto-mode') || 'L1'
      if (autoMode === 'L1') {
        taskStore.waitForConfirm(taskId)
      } else {
        taskStore.completeTask(taskId)
      }
    } catch (e) {
      taskStore.failTask(taskId)
      throw e
    }
  }

  return {
    isGenerating,
    batchGenerate,
    extractTask,
    continueWriting,
    rewriteContent,
  }
})
