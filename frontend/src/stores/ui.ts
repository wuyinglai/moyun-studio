import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project } from './project'

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
  function openSettings() {
    modals.value.settings = true
  }

  function closeSettings() {
    modals.value.settings = false
  }

  function openCreateProject() {
    modals.value.createProject = true
    modals.value.editingProject = null
  }

  function closeCreateProject() {
    modals.value.createProject = false
    modals.value.editingProject = null
  }

  function openOpenProject() {
    modals.value.openProject = true
  }

  function closeOpenProject() {
    modals.value.openProject = false
  }

  function openEditProject(project: Project) {
    modals.value.editingProject = project
    modals.value.createProject = true
  }

  function openTokenCount() {
    modals.value.tokenCount = true
  }

  function closeTokenCount() {
    modals.value.tokenCount = false
  }

  function openCompare() {
    modals.value.compare = true
  }

  function closeCompare() {
    modals.value.compare = false
  }

  function openFeedback() {
    modals.value.feedback = true
  }

  function closeFeedback() {
    modals.value.feedback = false
  }

  function openRevisionLog() {
    modals.value.revisionLog = true
  }

  function closeRevisionLog() {
    modals.value.revisionLog = false
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
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['theme'],
  },
})
