/**
 * useHotkeys - 全局快捷键 composable
 * 使用 hotkeys-js 库
 */
import { onBeforeUnmount } from 'vue'
import hotkeys from 'hotkeys-js'
import type { KeyHandler } from 'hotkeys-js'

export interface HotkeyBinding {
  key: string
  scope?: string
  description?: string
}

const registeredKeys = new Set<string>()

export function useHotkeys() {
  /**
   * 注册快捷键
   * @param key 快捷键描述，如 'command+s', 'ctrl+shift+p'
   * @param handler 回调函数
   * @param scope 作用域，默认 'global'
   */
  function register(key: string, handler: KeyHandler, scope = 'global') {
    hotkeys(key, { scope }, handler)
    registeredKeys.add(key)
  }

  /**
   * 批量注册快捷键
   */
  function registerBatch(bindings: HotkeyBinding[], handler: KeyHandler) {
    bindings.forEach(({ key, scope = 'global' }) => {
      register(key, handler, scope)
    })
  }

  /** 注销快捷键 */
  function unregister(key: string, scope = 'global') {
    hotkeys.unbind(key, scope)
    registeredKeys.delete(key)
  }

  /** 注销所有（组件卸载时调用） */
  function unregisterAll() {
    registeredKeys.forEach((key) => {
      hotkeys.unbind(key)
    })
    registeredKeys.clear()
  }

  onBeforeUnmount(() => {
    unregisterAll()
  })

  return {
    register,
    registerBatch,
    unregister,
    unregisterAll,
  }
}

// 预设快捷键常量
export const HOTKEYS = {
  SAVE: 'command+s',
  NEW_FILE: 'command+n',
  FIND: 'command+f',
  REWRITE: 'command+shift+r',
  CONTINUE: 'command+shift+n',
  STOP: 'command+shift+s',
  TOGGLE_THEME: 'command+shift+t',
  OPEN_SETTINGS: 'command+,',
} as const
