/**
 * useFileTree - 文件树 composable
 * 提供文件树加载、刷新、节点操作逻辑
 */
import { ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useProjectStore } from '@/stores/project'
import { fileService } from '@/services/file.service'
import type { FileNode } from '@/types/file'

export function useFileTree() {
  const fileStore = useFileStore()
  const projectStore = useProjectStore()
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  /** 加载项目文件树 */
  async function loadTree(projectId?: string) {
    const pid = projectId || projectStore.currentProject?.id
    if (!pid) return

    isLoading.value = true
    error.value = null
    try {
      const tree = await fileService.getTree(pid)
      fileStore.setTree(tree.nodes || [])
    } catch (e) {
      error.value = '加载文件树失败'
      console.error(e)
    } finally {
      isLoading.value = false
    }
  }

  /** 刷新文件树 */
  async function refresh() {
    await loadTree()
  }

  /** 展开/折叠目录 */
  function toggleNode(node: FileNode) {
    if (node.type !== 'directory') return
    node.expanded = !node.expanded
  }

  /** 展开所有目录 */
  function expandAll(nodes?: FileNode[]) {
    const list = nodes || fileStore.tree
    list.forEach((node) => {
      if (node.type === 'directory') {
        node.expanded = true
        if (node.children) {
          expandAll(node.children)
        }
      }
    })
  }

  /** 折叠所有目录 */
  function collapseAll(nodes?: FileNode[]) {
    const list = nodes || fileStore.tree
    list.forEach((node) => {
      if (node.type === 'directory') {
        node.expanded = false
        if (node.children) {
          collapseAll(node.children)
        }
      }
    })
  }

  return {
    isLoading,
    error,
    loadTree,
    refresh,
    toggleNode,
    expandAll,
    collapseAll,
  }
}
