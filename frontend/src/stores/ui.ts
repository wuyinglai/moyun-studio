import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { Project } from './project'
import { saveConfig as saveRemoteConfig } from '@/services/configService'

export type Theme = 'dark' | 'green' | 'gray'

export interface PanelWidths {
  left: number
  right: number
  editorChat: number
}

export interface ModalState {
  settings: boolean
  createProject: boolean
  openProject: boolean
  editingProject: Project | null
  tokenCount: boolean
  compare: boolean
  feedback: boolean
  revisionLog: boolean
  batchGenerate: boolean
  extract: boolean
  qualityReview: boolean
  search: boolean
  quickOpen: boolean
  trash: boolean
  backup: boolean
}

const THEME_LABELS: Record<Theme, string> = {
  dark: '深邃夜紫',
  green: '墨绿护眼',
  gray: '经典炭灰',
}

export const useUIStore = defineStore('ui', () => {
  const theme = ref<Theme>('dark')

  // 模态框显示状态
  const modals = ref<ModalState>({
    settings: false,
    createProject: false,
    openProject: false,
    editingProject: null,
    tokenCount: false,
    compare: false,
    feedback: false,
    revisionLog: false,
    batchGenerate: false,
    extract: false,
    qualityReview: false,
    search: false,
    quickOpen: false,
    trash: false,
    backup: false,
  })

  // 初始化时应用主题
  function applyTheme(t: Theme) {
    document.documentElement.dataset.theme = t === 'dark' ? '' : t
    if (t === 'dark') {
      document.documentElement.removeAttribute('data-theme')
    }
    theme.value = t
  }

  // 立即应用保存的主题（从 persist 恢复后自动生效）
  applyTheme(theme.value)

  // G0104 主题变更同步到后端 .config.json
  watch(theme, (val) => {
    saveRemoteConfig({ theme: val }).catch(() => {})
  })

  function setTheme(t: Theme) {
    applyTheme(t)
  }

  /** 切换到下一个主题（循环） */
  function toggleTheme() {
    const themes: Theme[] = ['dark', 'green', 'gray']
    const current = themes.indexOf(theme.value)
    const next = themes[(current + 1) % themes.length]
    setTheme(next)
  }

  /** 获取主题对应的显示名称 */
  function getThemeLabel(t: Theme): string {
    return THEME_LABELS[t]
  }

  // 模态框控制
  function _closeAllModals() {
    for (const key of Object.keys(modals.value)) {
      if (key !== 'editingProject') {
        (modals.value as Record<string, unknown>)[key] = false
      }
    }
  }

  function openSettings() {
    _closeAllModals()
    modals.value.settings = true
  }

  function closeSettings() {
    modals.value.settings = false
  }

  function openCreateProject() {
    _closeAllModals()
    modals.value.createProject = true
    modals.value.editingProject = null
  }

  function closeCreateProject() {
    modals.value.createProject = false
    modals.value.editingProject = null
  }

  function openOpenProject() {
    _closeAllModals()
    modals.value.openProject = true
  }

  function closeOpenProject() {
    modals.value.openProject = false
  }

  function openEditProject(project: Project) {
    _closeAllModals()
    modals.value.editingProject = project
    modals.value.createProject = true
  }

  function openTokenCount() {
    _closeAllModals()
    modals.value.tokenCount = true
  }

  function closeTokenCount() {
    modals.value.tokenCount = false
  }

  function openCompare() {
    _closeAllModals()
    modals.value.compare = true
  }

  function closeCompare() {
    modals.value.compare = false
  }

  function openFeedback() {
    _closeAllModals()
    modals.value.feedback = true
  }

  function closeFeedback() {
    modals.value.feedback = false
  }

  function openRevisionLog() {
    _closeAllModals()
    modals.value.revisionLog = true
  }

  function closeRevisionLog() {
    modals.value.revisionLog = false
  }

  function openBatchGenerate() {
    _closeAllModals()
    modals.value.batchGenerate = true
  }

  function closeBatchGenerate() {
    modals.value.batchGenerate = false
  }

  function openExtract() {
    _closeAllModals()
    modals.value.extract = true
  }

  function closeExtract() {
    modals.value.extract = false
  }

  function openQualityReview() {
    _closeAllModals()
    modals.value.qualityReview = true
  }

  function closeQualityReview() {
    modals.value.qualityReview = false
  }

  function openSearch() {
    _closeAllModals()
    modals.value.search = true
  }

  function closeSearch() {
    modals.value.search = false
  }

  function openQuickOpen() {
    _closeAllModals()
    modals.value.quickOpen = true
  }

  function closeQuickOpen() {
    modals.value.quickOpen = false
  }

  function openTrash() {
    _closeAllModals()
    modals.value.trash = true
  }

  function closeTrash() {
    modals.value.trash = false
  }

  function openBackup() {
    _closeAllModals()
    modals.value.backup = true
  }

  function closeBackup() {
    modals.value.backup = false
  }

  return {
    theme,
    modals,
    setTheme,
    toggleTheme,
    getThemeLabel,
    openSettings,
    closeSettings,
    openCreateProject,
    closeCreateProject,
    openOpenProject,
    closeOpenProject,
    openEditProject,
    openTokenCount,
    closeTokenCount,
    openCompare,
    closeCompare,
    openFeedback,
    closeFeedback,
    openRevisionLog,
    closeRevisionLog,
    openBatchGenerate,
    closeBatchGenerate,
    openExtract,
    closeExtract,
    openQualityReview,
    closeQualityReview,
    openSearch,
    closeSearch,
    openQuickOpen,
    closeQuickOpen,
    openTrash,
    closeTrash,
    openBackup,
    closeBackup,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['theme'],
  },
})
