import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface HistoryItem {
  id: string
  content: string
  timestamp: number
  path: string
}

export const useHistoryStore = defineStore('history', () => {
  const historyMap = ref<Map<string, HistoryItem[]>>(new Map())
  const currentIndexMap = ref<Map<string, number>>(new Map())
  const MAX_HISTORY = 20

  function getHistory(path: string): HistoryItem[] {
    return historyMap.value.get(path) || []
  }

  function getCurrentIndex(path: string): number {
    return currentIndexMap.value.get(path) ?? -1
  }

  function pushHistory(path: string, content: string) {
    let history = getHistory(path)
    let currentIndex = getCurrentIndex(path)

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

    historyMap.value.set(path, history)
    currentIndexMap.value.set(path, history.length - 1)
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
      currentIndexMap.value.set(path, idx)
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
      currentIndexMap.value.set(path, idx)
      return history[idx]?.content || null
    }
    return null
  }

  function clearHistory(path?: string) {
    if (path) {
      historyMap.value.delete(path)
      currentIndexMap.value.delete(path)
    } else {
      historyMap.value.clear()
      currentIndexMap.value.clear()
    }
  }

  return {
    historyMap,
    currentIndexMap,
    getHistory,
    getCurrentIndex,
    pushHistory,
    canGoBack,
    canGoForward,
    goBack,
    goForward,
    clearHistory,
  }
})
