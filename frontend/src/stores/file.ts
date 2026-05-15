import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import api from '@/services/api'
import { useProjectStore } from './project'

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
}

export interface FileContent {
  content: string
  frontmatter?: Record<string, unknown>
  wordCount?: number
}

export interface VersionSnapshot {
  id: string
  path: string
  version: number
  createdAt: string
  wordCount: number
}

export const useFileStore = defineStore('file', () => {
  const tree = ref<FileNode[]>([])
  const openFiles = ref<FileNode[]>([])
  const currentFile = ref<FileNode | null>(null)
  const unsavedFiles = ref<Set<string>>(new Set())
  const isLoading = ref(false)
  const fileContents = ref<Record<string, FileContent>>({})
  const snapshots = ref<Record<string, VersionSnapshot[]>>({})

  // 按 projectId 隔离的文件状态（持久化）
  const perProjectData = ref<Record<string, { openFiles: FileNode[]; currentFile: FileNode | null }>>({})

  async function loadTree(projectId: string) {
    isLoading.value = true
    try {
      const data = await api.get<any>('/tree', { params: { project_id: projectId } })
      tree.value = (data && data.tree) || []
      // 后端 tree 路径包含 project_id 前缀（如 "abc123/书名.md"），需剥离
      const prefix = projectId + '/'
      stripTreePathPrefix(tree.value, prefix)
    } finally {
      isLoading.value = false
    }
  }

  function stripTreePathPrefix(nodes: FileNode[], prefix: string) {
    for (const node of nodes) {
      if (node.path.startsWith(prefix)) {
        node.path = node.path.slice(prefix.length)
      }
      if (node.children) {
        stripTreePathPrefix(node.children, prefix)
      }
    }
  }

  async function readFile(projectId: string, path: string): Promise<FileContent> {
    const data = await api.get<FileContent>('/file', { params: { project_id: projectId, path } })
    fileContents.value[path] = data
    return data
  }

  async function saveFile(projectId: string, path: string, content: string) {
    await api.post(`/file?project_id=${projectId}`, { path, content })
    unsavedFiles.value.delete(path)
    fileContents.value[path] = { content }
  }

  async function createFile(projectId: string, path: string, content: string = '') {
    return await api.post('/file/create', { project_id: projectId, path, content })
  }

  async function createDirectory(projectId: string, path: string) {
    return await api.post('/directory/create', { project_id: projectId, path })
  }

  async function renameFile(projectId: string, oldPath: string, newPath: string) {
    return await api.post('/file/rename', { project_id: projectId, old_path: oldPath, new_path: newPath })
  }

  async function loadSnapshots(projectId: string, path: string) {
    const data = await api.get<VersionSnapshot[]>(`/backup/${projectId}/snapshots`, {
      params: { path },
    })
    snapshots.value[path] = data || []
    return data
  }

  async function restoreSnapshot(projectId: string, path: string, snapshotId: string) {
    return await api.post('/backup/restore', {
      project_id: projectId,
      path,
      snapshot_id: snapshotId,
    })
  }

  async function forwardVersion(projectId: string, path: string) {
    return await api.post('/backup/forward', { project_id: projectId, path })
  }

  async function backwardVersion(projectId: string, path: string) {
    return await api.post('/backup/backward', { project_id: projectId, path })
  }

  function openFile(node: FileNode) {
    if (!openFiles.value.find((f) => f.path === node.path)) {
      openFiles.value.push(node)
    }
    currentFile.value = node
  }

  function closeFile(path: string) {
    const index = openFiles.value.findIndex((f) => f.path === path)
    if (index !== -1) {
      openFiles.value.splice(index, 1)
    }
    if (currentFile.value?.path === path) {
      currentFile.value = openFiles.value[0] || null
    }
  }

  function markDirty(path: string) {
    unsavedFiles.value.add(path)
  }

  function refreshTree() {
    const projectStore = useProjectStore()
    if (projectStore.currentProject) {
      loadTree(projectStore.currentProject.id)
    }
  }

  function handleFileCreated(_path: string, _name?: string) {
    refreshTree()
  }

  function handleDirectoryCreated(_path: string, _name?: string) {
    refreshTree()
  }

  function handleFileRenamed(oldPath: string, newPath: string) {
    const openFile = openFiles.value.find((f) => f.path === oldPath)
    if (openFile) {
      openFile.path = newPath
      openFile.name = newPath.split('/').pop() || ''
    }
    refreshTree()
  }

  function handleFileUpdated(path: string, content: string) {
    if (content !== undefined && content !== null) {
      fileContents.value[path] = { content }
    }
  }

  // ─── 按 projectId 隔离：切换项目时保存/恢复 openFiles/currentFile ───
  watch(
    () => useProjectStore().currentProject,
    (newProj, oldProj) => {
      // 保存旧项目状态
      if (oldProj) {
        perProjectData.value[oldProj.id] = JSON.parse(JSON.stringify({
          openFiles: openFiles.value,
          currentFile: currentFile.value,
        }))
      }
      // 清理当前状态
      openFiles.value = []
      currentFile.value = null
      // 恢复新项目状态
      if (newProj && perProjectData.value[newProj.id]) {
        const saved = perProjectData.value[newProj.id]
        if (saved.openFiles) openFiles.value = saved.openFiles
        if (saved.currentFile) currentFile.value = saved.currentFile
      }
    },
  )

  return {
    tree,
    openFiles,
    currentFile,
    unsavedFiles,
    isLoading,
    fileContents,
    snapshots,
    loadTree,
    readFile,
    saveFile,
    createFile,
    createDirectory,
    renameFile,
    loadSnapshots,
    restoreSnapshot,
    forwardVersion,
    backwardVersion,
    openFile,
    closeFile,
    markDirty,
    refreshTree,
    handleFileCreated,
    handleDirectoryCreated,
    handleFileRenamed,
    handleFileUpdated,
    perProjectData,
  }
}, {
  persist: {
    storage: localStorage,
    pick: ['perProjectData'],
  },
})
