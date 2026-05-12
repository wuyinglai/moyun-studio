/**
 * useAutoSave - 自动保存 composable
 * 防抖机制：300ms 内不触发，超过后自动保存
 */
import { ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'

const DEBOUNCE_MS = 300

export function useAutoSave() {
  const fileStore = useFileStore()
  const editorStore = useEditorStore()
  const projectStore = useProjectStore()
  const notification = useNotificationStore()

  const isSaving = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  /** 标记文件已修改，启动防抖计时 */
  function triggerAutoSave(filePath: string) {
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      doSave(filePath)
    }, DEBOUNCE_MS)
  }

  /** 执行保存 */
  async function doSave(filePath: string) {
    if (isSaving.value) return
    if (!projectStore.currentProject) return
    if (!fileStore.unsavedFiles.has(filePath)) return

    isSaving.value = true
    try {
      const content = editorStore.getContent(filePath)
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
  }

  return {
    isSaving,
    triggerAutoSave,
    saveNow,
    cleanup,
  }
}
