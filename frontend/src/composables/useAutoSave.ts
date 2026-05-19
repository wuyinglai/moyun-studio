/**
 * useAutoSave - 自动保存 composable。
 * 输入 300ms 后保存；编辑 10 秒后创建持久快照。
 */
import { ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useHistoryStore } from '@/stores/history'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

const DEBOUNCE_MS = 300

function createBackendSnapshot(projectId: string, filePath: string, label?: string) {
  api.post(`/snapshots/${projectId}`, {
    file_path: filePath,
    label: label || null,
  }).catch(() => {
    // 快照创建失败不应影响编辑体验。
  })
}

function createRevisionLog(projectId: string, filePath: string, before: string, after: string) {
  if (!before || before === after) return
  api.post(`/revision-log/${projectId}`, {
    chapter_path: filePath,
    revision_type: 'auto_save',
    description: '自动保存',
    content_before: before,
    content_after: after,
  }).catch(() => {
    // 修改日志不应阻断保存。
  })
}

export function useAutoSave() {
  const fileStore = useFileStore()
  const editorStore = useEditorStore()
  const projectStore = useProjectStore()
  const historyStore = useHistoryStore()
  const notification = useNotificationStore()

  const isSaving = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null
  let snapshotTimer: ReturnType<typeof setTimeout> | null = null

  function triggerAutoSave(filePath: string) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      doSave(filePath)
    }, DEBOUNCE_MS)

    if (snapshotTimer) clearTimeout(snapshotTimer)
    snapshotTimer = setTimeout(() => {
      const content = editorStore.getContent(filePath)
      if (content) {
        historyStore.pushHistory(filePath, content)
        if (projectStore.currentProject) {
          createBackendSnapshot(projectStore.currentProject.id, filePath)
        }
      }
    }, 10000)
  }

  async function doSave(filePath: string) {
    if (isSaving.value) return
    if (!projectStore.currentProject) return
    if (!fileStore.unsavedFiles.has(filePath)) return

    isSaving.value = true
    try {
      const content = editorStore.getContent(filePath)
      const previous = fileStore.fileContents[filePath]?.content || ''
      if (content) {
        historyStore.pushHistory(filePath, content)
        createBackendSnapshot(projectStore.currentProject.id, filePath, '自动保存')
        createRevisionLog(projectStore.currentProject.id, filePath, previous, content)
      }
      await fileStore.saveFile(projectStore.currentProject.id, filePath, content)
    } catch {
      notification.error('自动保存失败')
    } finally {
      isSaving.value = false
    }
  }

  async function saveNow(filePath: string) {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    await doSave(filePath)
  }

  function cleanup() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (snapshotTimer) {
      clearTimeout(snapshotTimer)
      snapshotTimer = null
    }
  }

  return {
    isSaving,
    triggerAutoSave,
    saveNow,
    cleanup,
  }
}
