<template>
  <div class="file-tree">
    <!-- 文件树头部 -->
    <div class="tree-header">
      <span class="tree-title">文件</span>
      <button class="btn-icon" @click="refreshTree" title="刷新">
        <i class="fa-solid fa-rotate-right" :class="{ spinning: isLoading }"></i>
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="tree-loading">
      <i class="fa-solid fa-spinner fa-spin"></i>
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!projectStore.currentProject" class="tree-empty">
      <i class="fa-solid fa-folder-open"></i>
      <span>请先打开项目</span>
    </div>

    <!-- 文件树 -->
    <div v-else class="tree-content">
      <TreeNode
        v-for="node in fileStore.tree"
        :key="node.path"
        :node="node"
        :depth="0"
        @file-click="handleFileClick"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useFileStore, FileNode } from '@/stores/file'
import { useProjectStore } from '@/stores/project'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import TreeNode from './TreeNode.vue'

const fileStore = useFileStore()
const projectStore = useProjectStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()

const isLoading = computed(() => fileStore.isLoading)

// 监听项目切换，加载对应文件树
watch(
  () => projectStore.currentProject,
  async (project) => {
    if (project) {
      await fileStore.loadTree(project.id)
    }
  },
  { immediate: true }
)

async function refreshTree() {
  if (projectStore.currentProject) {
    await fileStore.loadTree(projectStore.currentProject.id)
    notification.success('文件树已刷新')
  }
}

async function handleFileClick(node: FileNode) {
  if (node.type === 'file') {
    try {
      // 读取文件内容
      const content = await fileStore.readFile(projectStore.currentProject!.id, node.path)
      // 打开文件（添加到标签栏）
      fileStore.openFile(node)
      // 设置编辑器内容
      editorStore.setContent(content)
      editorStore.setCurrentFile(node.path)
    } catch (e) {
      notification.error(`无法打开文件: ${node.name}`)
    }
  }
}
</script>

<style scoped lang="scss">
.file-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.tree-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;

  &:hover {
    background: var(--bg-card);
    color: var(--text-primary);
  }

  .spinning {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tree-loading,
.tree-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
  padding: 20px;
  text-align: center;

  i {
    font-size: 32px;
    opacity: 0.5;
  }
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
</style>
