import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { Modal } from 'ant-design-vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import { useProjectStore } from './project'
import { useEditorStore } from './editor'

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
  mtime?: number | null
  hash?: string | null
}

export interface VersionSnapshot {
  snapshot_id: string
  file_path: string
  label?: string | null
  created_at: string
  word_count: number
}

export const useFileStore = defineStore('file', () => {
  const tree = ref<FileNode[]>([])
  const openFiles = ref<FileNode[]>([])
  const currentFile = ref<FileNode | null>(null)
  const unsavedFiles = ref<Set<string>>(new Set())
  const isLoading = ref(false)
  const fileContents = ref<Record<string, FileContent>>({})
  const fileMeta = ref<Record<string, { mtime?: number | null; hash?: string | null }>>({})
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
    const data = await api.get<FileContent>(API_ROUTES.file, { params: { project_id: projectId, path } })
    fileContents.value[path] = data
    fileMeta.value[path] = { mtime: data.mtime, hash: data.hash }
    return data
  }

  async function saveFile(projectId: string, path: string, content: string) {
    const known = fileMeta.value[path] || fileContents.value[path] || {}
    try {
      const result = await api.post<FileContent | null>(`${API_ROUTES.file}?project_id=${projectId}`, {
        path,
        content,
        expected_mtime: known.mtime ?? undefined,
        expected_hash: known.hash ?? undefined,
      })
      unsavedFiles.value.delete(path)
      fileContents.value[path] = {
        content,
        mtime: result?.mtime ?? known.mtime,
        hash: result?.hash ?? known.hash,
      }
      fileMeta.value[path] = {
        mtime: result?.mtime ?? known.mtime,
        hash: result?.hash ?? known.hash,
      }
    } catch (error: unknown) {
      const err = error as { response?: { status?: number; data?: { error?: { code?: string } } } }
      const code = err?.response?.data?.error?.code
      if (err?.response?.status === 409 || code === 'FILE_CONFLICT') {
        await showFileConflict(projectId, path)
      }
      throw error
    }
  }

  async function showFileConflict(projectId: string, path: string) {
    return new Promise<void>((resolve) => {
      Modal.confirm({
        title: '文件已被其他操作修改',
        content: '文件已被其他操作修改，请重新加载服务器版本或取消保存。为避免静默覆盖，本次保存没有写入。',
        okText: '重新加载服务器版本',
        cancelText: '取消保存',
        async onOk() {
          const latest = await readFile(projectId, path)
          fileContents.value[path] = latest
          const editorStore = useEditorStore()
          editorStore.loadContent(path, latest.content)
          editorStore.contentSource = 'external'
          unsavedFiles.value.delete(path)
          resolve()
        },
        onCancel() {
          resolve()
        },
      })
    })
  }

  async function createFile(projectId: string, path: string, content: string = '') {
    return await api.post(API_ROUTES.fileCreate, { project_id: projectId, path, content })
  }

  async function createDirectory(projectId: string, path: string) {
    return await api.post(API_ROUTES.directoryCreate, { project_id: projectId, path })
  }

  async function renameFile(projectId: string, oldPath: string, newPath: string) {
    return await api.post(API_ROUTES.fileRename, { project_id: projectId, old_path: oldPath, new_path: newPath })
  }

  async function deleteFile(projectId: string, path: string) {
    return await api.post(API_ROUTES.fileDelete, { project_id: projectId, path })
  }

  async function deleteDirectory(projectId: string, path: string) {
    return await api.post(API_ROUTES.directoryDelete, { project_id: projectId, path })
  }

  async function loadSnapshots(projectId: string, path: string) {
    const data = await api.get<VersionSnapshot[]>(API_ROUTES.snapshot(projectId), {
      params: { file_path: path },
    })
    snapshots.value[path] = data || []
    return data
  }

  async function restoreSnapshot(projectId: string, path: string, snapshotId: string) {
    return await api.post(API_ROUTES.snapshotRestore(projectId), {
      project_id: projectId,
      path,
      snapshot_id: snapshotId,
    })
  }

  async function forwardVersion(projectId: string, path: string) {
    return await api.post(API_ROUTES.backupForward, { project_id: projectId, path })
  }

  async function backwardVersion(projectId: string, path: string) {
    return await api.post(API_ROUTES.backupBackward, { project_id: projectId, path })
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
    fileMeta,
    snapshots,
    loadTree,
    readFile,
    saveFile,
    createFile,
    createDirectory,
    renameFile,
    deleteFile,
    deleteDirectory,
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
