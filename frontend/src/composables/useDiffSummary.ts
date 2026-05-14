/**
 * AI 修改摘要 - 管线执行后展示结构化修改分析
 */
import { ref, computed } from 'vue'

export interface DiffSummaryItem {
  text: string
  type: 'optimize' | 'warning' | 'style' | 'addition' | 'deletion'
}

export interface DiffSummaryData {
  summary: string
  target_file: string
  timestamp: number
  overview?: string
  items?: DiffSummaryItem[]
}

const _current = ref<DiffSummaryData | null>(null)
const _history = ref<DiffSummaryData[]>([])
const _showPanel = ref(false)

export function useDiffSummary() {
  const current = computed(() => _current.value)
  const history = computed(() => _history.value)
  const showPanel = computed(() => _showPanel.value)
  const hasSummary = computed(() => _current.value !== null)

  function setSummary(summary: string, targetFile: string) {
    const data: DiffSummaryData = {
      summary,
      target_file: targetFile,
      timestamp: Date.now(),
    }
    _current.value = data
    _history.value.unshift(data)
    if (_history.value.length > 20) {
      _history.value = _history.value.slice(0, 20)
    }
    _showPanel.value = true
  }

  function dismiss() {
    _current.value = null
    _showPanel.value = false
  }

  function togglePanel() {
    _showPanel.value = !_showPanel.value
  }

  function viewHistory(item: DiffSummaryData) {
    _current.value = item
    _showPanel.value = true
  }

  return {
    current,
    history,
    showPanel,
    hasSummary,
    setSummary,
    dismiss,
    togglePanel,
    viewHistory,
  }
}
