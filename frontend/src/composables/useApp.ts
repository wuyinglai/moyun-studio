/**
 * 应用初始化和全局状态管理
 * 负责应用启动时的初始化流程和全局状态同步
 */
import { ref } from 'vue'
import { useLLMStore } from '@/stores/llm'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
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

export function useProjectSwitch() {
  const projectStore = useProjectStore()
  const fileStore = useFileStore()

  async function switchProject(projectId: string) {
    if (projectStore.currentProject) {
      projectStore.closeProject()
    }
    const project = await projectStore.openProject(projectId)
    await fileStore.loadTree(projectId)
    return project
  }

  return {
    switchProject,
  }
}

export function useAutomation() {
  const isAutoMode = ref(false)
  const currentLevel = ref<'L1' | 'L2'>('L1')
  const isPaused = ref(false)

  function setLevel(level: 'L1' | 'L2') {
    currentLevel.value = level
    isAutoMode.value = level === 'L2'
  }

  function pause() {
    isPaused.value = true
  }

  function resume() {
    isPaused.value = false
  }

  async function waitForUserConfirm(): Promise<boolean> {
    return new Promise((resolve) => {
      const MAX_WAIT = 5 * 60 * 1000
      const deadline = Date.now() + MAX_WAIT
      let resolved = false

      const check = setInterval(() => {
        if (!isPaused.value && !resolved) {
          resolved = true
          clearInterval(check)
          resolve(true)
        }
        if (Date.now() > deadline && !resolved) {
          resolved = true
          clearInterval(check)
          resolve(false)
        }
      }, 100)
    })
  }

  return {
    isAutoMode,
    currentLevel,
    isPaused,
    setLevel,
    pause,
    resume,
    waitForUserConfirm,
  }
}
