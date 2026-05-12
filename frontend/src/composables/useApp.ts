/**
 * 应用初始化和全局状态管理
 * 负责应用启动时的初始化流程和全局状态同步
 */
import { useLLMStore } from '@/stores/llm'
import { useProjectStore } from '@/stores/project'
import { sseService } from '@/composables/useSSE'

export function useAppInit() {
  const llmStore = useLLMStore()
  const projectStore = useProjectStore()

  async function initApp() {
    await llmStore.loadConfig()
    try {
      await llmStore.testConnection()
    } catch {
      console.warn('LLM 连接测试失败，部分功能可能不可用')
    }
    sseService.connect()
    await projectStore.loadProjects()
  }

  function cleanupApp() {
    sseService.disconnect()
    sseService.removeAllListeners()
  }

  return {
    initApp,
    cleanupApp,
  }
}
