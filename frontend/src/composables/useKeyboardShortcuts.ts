/**
 * 全局键盘快捷键
 */
import { onMounted, onBeforeUnmount } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useAutoSave } from '@/composables/useAutoSave'

type Handler = (e: KeyboardEvent) => void

const _shortcuts: Array<{ key: string; ctrl?: boolean; shift?: boolean; handler: Handler }> = []

function _matches(e: KeyboardEvent, key: string, ctrl?: boolean, shift?: boolean): boolean {
  if (e.key.toLowerCase() !== key.toLowerCase()) return false
  if (ctrl && !e.ctrlKey && !e.metaKey) return false
  if (shift && !e.shiftKey) return false
  if (!ctrl && !shift && (e.ctrlKey || e.metaKey || e.shiftKey)) return false
  return true
}

function _onKeydown(e: KeyboardEvent) {
  // 忽略在输入框/textarea 中的按键
  const tag = (e.target as HTMLElement).tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement).isContentEditable) {
    const key = e.key.toLowerCase()
    const isGlobalShortcut = (e.ctrlKey || e.metaKey)
      && (key === 's' || key === 'p' || (key === 'f' && e.shiftKey))
    if (!isGlobalShortcut) {
      return
    }
  }

  for (const shortcut of _shortcuts) {
    if (_matches(e, shortcut.key, shortcut.ctrl, shortcut.shift)) {
      e.preventDefault()
      shortcut.handler(e)
      return
    }
  }
}

export function registerShortcut(
  key: string,
  handler: Handler,
  ctrl = false,
  shift = false,
) {
  _shortcuts.push({ key, ctrl, shift, handler })
}

export function useKeyboardShortcuts() {
  const uiStore = useUIStore()
  const editorStore = useEditorStore()
  const { triggerAutoSave } = useAutoSave()

  function _openSearch() {
    uiStore.openSearch()
  }

  function _save() {
    const path = editorStore.currentFilePath
    if (path) {
      triggerAutoSave(path)
    }
  }

  function _quickOpen() {
    uiStore.openQuickOpen()
  }

  onMounted(() => {
    // Ctrl+S: 保存
    registerShortcut('s', _save, true)
    // Ctrl+Shift+F: 全局搜索
    registerShortcut('f', _openSearch, true, true)
    // Ctrl+P: 快速打开文件
    registerShortcut('p', _quickOpen, true)

    window.addEventListener('keydown', _onKeydown)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', _onKeydown)
    _shortcuts.length = 0
  })
}
