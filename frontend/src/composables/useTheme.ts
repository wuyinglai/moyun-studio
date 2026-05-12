/**
 * useTheme - 主题切换 composable
 * 支持：深邃夜紫（默认）、墨绿护眼、经典炭灰
 */
import { ref, watch } from 'vue'
import { getStorage, setStorage, STORAGE_KEYS } from '@/utils/storage'
import type { ThemeName } from '@/types'

const DEFAULT_THEME: ThemeName = 'dark-purple'

const theme = ref<ThemeName>(getStorage<ThemeName>(STORAGE_KEYS.THEME, DEFAULT_THEME))

export function useTheme() {
  /** 设置主题 */
  function setTheme(newTheme: ThemeName) {
    theme.value = newTheme
    applyTheme(newTheme)
    setStorage(STORAGE_KEYS.THEME, newTheme)
  }

  /** 应用主题到 document */
  function applyTheme(t: ThemeName) {
    document.documentElement.setAttribute('data-theme', t === 'dark-purple' ? '' : t)
  }

  /** 初始化主题（App 启动时调用一次） */
  function initTheme() {
    applyTheme(theme.value)
  }

  /** 切换到下一个主题（循环） */
  function toggleTheme() {
    const themes: ThemeName[] = ['dark-purple', 'green', 'dark-gray']
    const current = themes.indexOf(theme.value)
    const next = themes[(current + 1) % themes.length]
    setTheme(next)
  }

  /** 获取主题对应的显示名称 */
  function getThemeLabel(t: ThemeName): string {
    const labels: Record<ThemeName, string> = {
      'dark-purple': '深邃夜紫',
      green: '墨绿护眼',
      'dark-gray': '经典炭灰',
    }
    return labels[t]
  }

  // 监听变化并同步到 DOM
  watch(theme, (t) => applyTheme(t), { immediate: true })

  return {
    theme,
    setTheme,
    toggleTheme,
    initTheme,
    getThemeLabel,
  }
}
