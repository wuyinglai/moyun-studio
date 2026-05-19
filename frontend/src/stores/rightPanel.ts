import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useRightPanelStore = defineStore('rightPanel', () => {
  const promptContent = ref('')
  const promptHistory = ref<string[]>([])
  const currentHistoryIndex = ref(-1)
  const executionLogs = ref<string[]>([])
  const activePipelineTab = ref<'quick' | 'editor'>('quick')
  const activeTab = ref<string>('quick')  // 右侧面板当前高亮的 Tab ID
  const isPipelineRunning = ref(false)

  const currentPrompt = computed(() => promptContent.value)

  function loadPromptTemplate(content: string) {
    promptContent.value = content
    promptHistory.value.unshift(content)
    currentHistoryIndex.value = -1
    if (promptHistory.value.length > 50) {
      promptHistory.value.pop()
    }
  }

  function updatePrompt(content: string) {
    promptContent.value = content
  }

  function goPromptHistoryBack() {
    if (currentHistoryIndex.value < promptHistory.value.length - 1) {
      currentHistoryIndex.value++
      promptContent.value = promptHistory.value[currentHistoryIndex.value]
    }
  }

  function goPromptHistoryForward() {
    if (currentHistoryIndex.value > 0) {
      currentHistoryIndex.value--
      promptContent.value = promptHistory.value[currentHistoryIndex.value]
    } else if (currentHistoryIndex.value === 0) {
      currentHistoryIndex.value = -1
      promptContent.value = ''
    }
  }

  function appendLog(log: string) {
    executionLogs.value.push(`[${new Date().toLocaleTimeString()}] ${log}`)
    if (executionLogs.value.length > 500) {
      executionLogs.value.splice(0, executionLogs.value.length - 500)
    }
  }

  function clearLogs() {
    executionLogs.value = []
  }

  function clearHistory() {
    promptHistory.value = []
    currentHistoryIndex.value = -1
  }

  function setPipelineTab(tab: 'quick' | 'editor') {
    activePipelineTab.value = tab
  }

  function setPipelineRunning(running: boolean) {
    isPipelineRunning.value = running
  }

  function setActiveTab(tab: string) {
    activeTab.value = tab
  }

  function navigateToPipeline(pipelineName: string) {
    void pipelineName
    activeTab.value = 'pipeline'
    activePipelineTab.value = 'editor'
    // 设置 pipeline store 的 currentPipelineName
    // 由调用方在 import 后设置
  }

  return {
    promptContent,
    promptHistory,
    currentHistoryIndex,
    currentPrompt,
    executionLogs,
    activeTab,
    activePipelineTab,
    isPipelineRunning,
    loadPromptTemplate,
    updatePrompt,
    goPromptHistoryBack,
    goPromptHistoryForward,
    appendLog,
    clearLogs,
    clearHistory,
    setPipelineTab,
    setActiveTab,
    setPipelineRunning,
    navigateToPipeline,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['promptHistory', 'promptContent'],
  },
})
