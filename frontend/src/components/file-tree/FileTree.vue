<template>
  <div class="file-tree">
    <!-- 文件树头部 -->
    <div class="tree-header">
      <div class="tree-title-group">
        <span class="tree-icon" aria-hidden="true">📄</span>
        <span class="tree-title">文件</span>
      </div>
      <button class="tree-refresh-btn" @click="refreshTree" :title="isLoading ? '加载中...' : '刷新文件树'">
        <svg
          width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"
          :class="{ spinning: isLoading }"
        >
          <polyline points="23 4 23 10 17 10"/>
          <polyline points="1 20 1 14 7 14"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="tree-loading">
      <div class="loading-ink">
        <span></span><span></span><span></span>
      </div>
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!projectStore.currentProject" class="tree-empty">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
      </div>
      <span class="empty-text">暂无项目</span>
      <span class="empty-hint">创建或打开一个项目开始创作</span>
      <div class="empty-actions">
        <button class="empty-btn empty-btn--primary" @click="uiStore.openCreateProject()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新建项目
        </button>
        <button class="empty-btn empty-btn--secondary" @click="uiStore.openOpenProject()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          打开项目
        </button>
      </div>
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
import { useFileStore } from '@/stores/file'
import type { FileNode } from '@/stores/file'
import { useProjectStore } from '@/stores/project'
import { useEditorStore } from '@/stores/editor'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notification'
import TreeNode from './TreeNode.vue'

const fileStore = useFileStore()
const projectStore = useProjectStore()
const editorStore = useEditorStore()
const uiStore = useUIStore()
const notification = useNotificationStore()

const isLoading = computed(() => fileStore.isLoading)

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
      const fileData = await fileStore.readFile(projectStore.currentProject!.id, node.path)
      fileStore.openFile(node)
      editorStore.loadContent(node.path, fileData.content)
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
  background: var(--ink-dark);
}

/* ── 头部 ── */
.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 12px;
  position: relative;

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 16px;
    right: 16px;
    height: 1px;
    background: linear-gradient(90deg, var(--gold-primary), var(--border-ink), transparent);
    opacity: 0.2;
  }
}

.tree-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-icon {
  font-size: 14px;
  opacity: 0.6;
}

.tree-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted-ink);
  text-transform: uppercase;
  letter-spacing: 1.5px;
}

.tree-refresh-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-faint);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--ink-hover);
    color: var(--gold-primary);
  }
}

.spinning {
  animation: spin 0.8s linear infinite;
}

/* ── 加载状态 ── */
.tree-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted-ink);
  font-size: 13px;
  padding: 32px;
}

.loading-ink {
  display: flex;
  gap: 5px;

  span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--gold-primary);
    animation: dot-bounce 1.4s ease-in-out infinite both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
    &:nth-child(3) { animation-delay: 0s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* ── 空状态 ── */
.tree-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 24px;
  text-align: center;
}

.empty-icon {
  color: var(--text-faint);
  opacity: 0.3;
  margin-bottom: 4px;
}

.empty-text {
  font-size: 14px;
  color: var(--text-muted-ink);
  font-weight: 500;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-faint);
  line-height: 1.5;
  max-width: 180px;
}

.empty-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
  width: 100%;
  max-width: 160px;
}

.empty-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);

  svg { flex-shrink: 0; }

  &--primary {
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
    color: var(--ink-deepest);
    border: none;

    &:hover {
      box-shadow: 0 4px 12px rgba(201, 169, 110, 0.3);
      transform: translateY(-1px);
    }
  }

  &--secondary {
    background: var(--ink-mid);
    color: var(--text-ink);
    border: 1px solid var(--border-ink);

    &:hover {
      background: var(--ink-hover);
      border-color: var(--gold-primary);
      color: var(--gold-primary);
    }
  }
}

/* ── 树内容 ── */
.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
</style>
