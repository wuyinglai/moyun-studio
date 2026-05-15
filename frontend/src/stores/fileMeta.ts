import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface FileGenMeta {
  promptType: string
  extraVars: Record<string, string>
  generatedAt: string
}

export const useFileMetaStore = defineStore('fileMeta', () => {
  // projectId → filePath → FileGenMeta
  const fileMetaMap = ref<Record<string, Record<string, FileGenMeta>>>({})

  function saveMeta(projectId: string, filePath: string, meta: FileGenMeta) {
    if (!fileMetaMap.value[projectId]) {
      fileMetaMap.value[projectId] = {}
    }
    fileMetaMap.value[projectId][filePath] = meta
  }

  function getMeta(projectId: string, filePath: string): FileGenMeta | null {
    return fileMetaMap.value[projectId]?.[filePath] ?? null
  }

  function removeMeta(projectId: string, filePath: string) {
    if (fileMetaMap.value[projectId]) {
      delete fileMetaMap.value[projectId][filePath]
    }
  }

  /** 删除某个项目的所有元数据（项目删除时清理） */
  function removeProjectMeta(projectId: string) {
    delete fileMetaMap.value[projectId]
  }

  return {
    fileMetaMap,
    saveMeta,
    getMeta,
    removeMeta,
    removeProjectMeta,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['fileMetaMap'],
  },
})
