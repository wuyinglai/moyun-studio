import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useRightPanelStore = defineStore('rightPanel', () => {
  const activeTab = ref<'prompt' | 'execution'>('prompt')
  const promptContent = ref('')
  const promptHistory = ref<string[]>([])
  const currentHistoryIndex = ref(-1)
  const executionLogs = ref<string[]>([])

  const currentPrompt = computed(() => promptContent.value)

  function setActiveTab(tab: 'prompt' | 'execution') {
    activeTab.value = tab
  }

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

  return {
    activeTab,
    promptContent,
    promptHistory,
    currentHistoryIndex,
    currentPrompt,
    executionLogs,
    setActiveTab,
    loadPromptTemplate,
    updatePrompt,
    goPromptHistoryBack,
    goPromptHistoryForward,
    appendLog,
    clearLogs,
    clearHistory,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['promptHistory', 'activeTab', 'promptContent'],
  },
})
