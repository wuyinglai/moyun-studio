/**
 * useFileTree - 文件树 composable
 * 提供文件树加载、刷新、节点操作逻辑
 */
import { ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useProjectStore } from '@/stores/project'
import { fileService } from '@/services/file.service'

export interface TreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: TreeNode[]
  expanded?: boolean
}

export function useFileTree() {
  const fileStore = useFileStore()
  const projectStore = useProjectStore()
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function loadTree(projectId?: string) {
    const pid = projectId || projectStore.currentProject?.id
    if (!pid) return

    isLoading.value = true
    error.value = null
    try {
      const tree = await fileService.getTree(pid)
      fileStore.tree = tree.nodes || []
    } catch (e) {
      error.value = '加载文件树失败'
      console.error(e)
    } finally {
      isLoading.value = false
    }
  }

  async function refresh() {
    await loadTree()
  }

  function toggleNode(node: TreeNode) {
    if (node.type !== 'directory') return
    node.expanded = !node.expanded
  }

  function expandAll(nodes?: TreeNode[]) {
    const list = nodes || fileStore.tree as TreeNode[]
    list.forEach((node) => {
      if (node.type === 'directory') {
        node.expanded = true
        if (node.children) {
          expandAll(node.children)
        }
      }
    })
  }

  function collapseAll(nodes?: TreeNode[]) {
    const list = nodes || fileStore.tree as TreeNode[]
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
