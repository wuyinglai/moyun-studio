/**
 * useAutoSave - 自动保存 composable
 * 防抖机制：300ms 内不触发，超过后自动保存
 * 编辑10秒后自动创建后端版本快照
 */
import { ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useHistoryStore } from '@/stores/history'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

const DEBOUNCE_MS = 300

/** 在后台创建版本快照（不阻塞调用方） */
function createBackendSnapshot(projectId: string, filePath: string, label?: string) {
  api.post(`/snapshots/${projectId}`, {
    file_path: filePath,
    label: label || null,
  }).catch(() => {
    // 快照创建失败不应影响编辑体验，静默忽略
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

  /** 标记文件已修改，启动防抖计时 */
  function triggerAutoSave(filePath: string) {
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      doSave(filePath)
    }, DEBOUNCE_MS)

    // G0101: 版本快照 — 编辑10秒后生成快照（内存 + 后端持久化）
    if (snapshotTimer) {
      clearTimeout(snapshotTimer)
    }
    snapshotTimer = setTimeout(() => {
      const content = editorStore.getContent(filePath)
      if (content) {
        historyStore.pushHistory(filePath, content)
        // 同步创建后端快照
        if (projectStore.currentProject) {
          createBackendSnapshot(projectStore.currentProject.id, filePath)
        }
      }
    }, 10000)
  }

  /** 执行保存 */
  async function doSave(filePath: string) {
    if (isSaving.value) return
    if (!projectStore.currentProject) return
    if (!fileStore.unsavedFiles.has(filePath)) return

    isSaving.value = true
    try {
      // 保存前先生成版本快照
      const content = editorStore.getContent(filePath)
      if (content) {
        historyStore.pushHistory(filePath, content)
        createBackendSnapshot(projectStore.currentProject.id, filePath, '自动保存')
      }
      await fileStore.saveFile(projectStore.currentProject.id, filePath, content)
    } catch {
      notification.error('自动保存失败')
    } finally {
      isSaving.value = false
    }
  }

  /** 立即保存（忽略防抖） */
  async function saveNow(filePath: string) {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    await doSave(filePath)
  }

  /** 清理 */
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
