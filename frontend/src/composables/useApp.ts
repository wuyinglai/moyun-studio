/**
 * 应用初始化和全局状态管理
 * 负责应用启动时的初始化流程和全局状态同步
 */

import { onMounted, watch, ref } from 'vue'
import { useLLMStore } from '@/stores/llm'
import { useProjectStore } from '@/stores/project'
import { useUIStore } from '@/stores/ui'
import { useFileStore } from '@/stores/file'
import { useSSE, sseService } from '@/composables/useSSE'

/**
 * 应用初始化 hook
 * 在应用启动时调用
 */
export function useAppInit() {
  const llmStore = useLLMStore()
  const projectStore = useProjectStore()
  const uiStore = useUIStore()

  /**
   * 初始化应用
   */
  async function initApp() {
    // 1. 加载 LLM 配置
    await llmStore.loadConfig()

    // 2. 测试 LLM 连接（失败不阻断初始化）
    try {
      await llmStore.testConnection()
    } catch {
      console.warn('LLM 连接测试失败，部分功能可能不可用')
    }

    // 3. 连接 SSE
    sseService.connect()

    // 4. 如果有当前项目，加载项目列表
    await projectStore.loadProjects()
  }

  /**
   * 清理应用
   */
  function cleanupApp() {
    sseService.disconnect()
    sseService.removeAllListeners()
  }

  return {
    initApp,
    cleanupApp,
  }
}

/**
 * 项目切换 hook
 * 处理项目切换时的状态更新
 */
export function useProjectSwitch() {
  const projectStore = useProjectStore()
  const fileStore = useFileStore()

  /**
   * 切换项目
   */
  async function switchProject(projectId: string) {
    // 1. 关闭当前项目
    if (projectStore.currentProject) {
      projectStore.closeProject()
    }

    // 2. 打开新项目
    const project = await projectStore.openProject(projectId)

    // 3. 加载文件树
    await fileStore.loadTree(projectId)

    return project
  }

  return {
    switchProject,
  }
}

/**
 * 自动化等级管理
 */
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

  /**
   * L1 模式：等待用户确认
   * 带超时兜底（5分钟），防止无限轮询导致内存泄漏
   */
  async function waitForUserConfirm(): Promise<boolean> {
    return new Promise((resolve) => {
      const MAX_WAIT = 5 * 60 * 1000 // 5 分钟超时
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
          resolve(false) // 超时，不继续
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
