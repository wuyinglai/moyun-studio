import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
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
}

export const useUIStore = defineStore('ui', () => {
  const theme = ref<Theme>('dark')
  const leftWidth = ref<number>(20)
  const rightWidth = ref<number>(25)

  // 模态框显示状态
  const modals = ref<ModalState>({
    settings: false,
    createProject: false,
    openProject: false,
    editingProject: null,
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

  function setLeftWidth(w: number) {
    leftWidth.value = w
  }

  function setRightWidth(w: number) {
    rightWidth.value = w
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

  return {
    theme,
    leftWidth,
    rightWidth,
    modals,
    setTheme,
    setLeftWidth,
    setRightWidth,
    openSettings,
    closeSettings,
    openCreateProject,
    closeCreateProject,
    openOpenProject,
    closeOpenProject,
    openEditProject,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['theme', 'leftWidth', 'rightWidth'],
  },
})
