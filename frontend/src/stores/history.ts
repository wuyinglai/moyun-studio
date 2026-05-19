import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface HistoryItem {
  id: string
  content: string
  timestamp: number
  path: string
}

export const useHistoryStore = defineStore('history', () => {
  const historyMap = ref<Record<string, HistoryItem[]>>({})
  const currentIndexMap = ref<Record<string, number>>({})
  const MAX_HISTORY = 30
  // 浏览历史时记录当前是否在"浏览旧版本"状态（非最新版本）
  const isBrowsing = ref(false)

  function getHistory(path: string): HistoryItem[] {
    return historyMap.value[path] || []
  }

  function getCurrentIndex(path: string): number {
    return currentIndexMap.value[path] ?? -1
  }

  function pushHistory(path: string, content: string) {
    let history = getHistory(path)
    const currentIndex = getCurrentIndex(path)

    // 如果当前不在最新位置，删除之后的历史
    if (currentIndex < history.length - 1 && history.length > 0) {
      history = history.slice(0, currentIndex + 1)
    }

    const item: HistoryItem = {
      id: Date.now().toString(),
      content,
      timestamp: Date.now(),
      path,
    }

    history.push(item)

    // 限制历史数量
    if (history.length > MAX_HISTORY) {
      history.shift()
    }

    historyMap.value[path] = history
    currentIndexMap.value[path] = history.length - 1
    isBrowsing.value = false
  }

  const canGoBack = (path?: string): boolean => {
    if (!path) return false
    const idx = getCurrentIndex(path)
    return idx > 0
  }

  const canGoForward = (path?: string): boolean => {
    if (!path) return false
    const history = getHistory(path)
    const idx = getCurrentIndex(path)
    return idx >= 0 && idx < history.length - 1
  }

  function goBack(path?: string): string | null {
    if (!path) return null
    const history = getHistory(path)
    let idx = getCurrentIndex(path)

    if (idx > 0) {
      idx--
      currentIndexMap.value[path] = idx
      isBrowsing.value = idx < history.length - 1
      return history[idx]?.content || null
    }
    return null
  }

  function goForward(path?: string): string | null {
    if (!path) return null
    const history = getHistory(path)
    let idx = getCurrentIndex(path)

    if (idx >= 0 && idx < history.length - 1) {
      idx++
      currentIndexMap.value[path] = idx
      isBrowsing.value = idx < history.length - 1
      return history[idx]?.content || null
    }
    return null
  }

  /** 浏览历史时确认当前版本为最终版本：截断之后的历史，退出浏览模式 */
  function saveCurrentVersion(path: string) {
    const history = getHistory(path)
    const idx = getCurrentIndex(path)
    if (idx >= 0 && idx < history.length) {
      historyMap.value[path] = history.slice(0, idx + 1)
      currentIndexMap.value[path] = history.length - 1
    }
    isBrowsing.value = false
  }

  function clearHistory(path?: string) {
    if (path) {
      delete historyMap.value[path]
      delete currentIndexMap.value[path]
    } else {
      historyMap.value = {}
      currentIndexMap.value = {}
    }
  }

  return {
    historyMap,
    currentIndexMap,
    isBrowsing,
    getHistory,
    getCurrentIndex,
    pushHistory,
    canGoBack,
    canGoForward,
    goBack,
    goForward,
    saveCurrentVersion,
    clearHistory,
  }
})
