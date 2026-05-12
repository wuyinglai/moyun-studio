<template>
  <div class="editor-tabs">
    <!-- 标签栏 -->
    <div class="tabs-bar">
      <div
        v-for="file in fileStore.openFiles"
        :key="file.path"
        class="tab"
        :class="{ active: fileStore.currentFile?.path === file.path }"
        @click="switchToTab(file.path)"
      >
        <!-- 文件图标 -->
        <i :class="getFileIcon(file.name)" class="tab-icon"></i>

        <!-- 文件名 -->
        <span class="tab-name">{{ getFileName(file.name) }}</span>

        <!-- 脏标记 -->
        <span v-if="fileStore.unsavedFiles.has(file.path)" class="tab-dirty">●</span>

        <!-- 关闭按钮 -->
        <button
          class="tab-close"
          @click.stop="closeTab(file.path)"
          title="关闭"
        >
          <i class="fa-solid fa-times"></i>
        </button>
      </div>
    </div>

    <!-- 状态栏 -->
    <div class="tabs-status" v-if="fileStore.currentFile">
      <span class="status-item">
        <i class="fa-solid fa-font"></i>
        {{ editorStore.wordCount.toLocaleString() }} 字
      </span>
      <span class="status-item">
        <i class="fa-solid fa-location-dot"></i>
        Ln {{ editorStore.cursorPosition.line }}, Col {{ editorStore.cursorPosition.col }}
      </span>
      <span class="status-item status-save" :class="saveStatusClass">
        {{ saveStatusText }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'

const fileStore = useFileStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()

const isSaving = ref(false)

const saveStatusClass = computed(() => {
  if (isSaving.value) return 'saving'
  if (fileStore.isLoading) return 'loading'
  if (fileStore.unsavedFiles.has(fileStore.currentFile?.path || '')) return 'unsaved'
  return 'saved'
})

const saveStatusText = computed(() => {
  if (isSaving.value) return '保存中...'
  if (fileStore.unsavedFiles.has(fileStore.currentFile?.path || '')) return '未保存'
  return '已保存'
})

function getFileName(name: string): string {
  return name
}

function getFileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase()
  const iconMap: Record<string, string> = {
    md: 'fa-solid fa-file-lines',
    txt: 'fa-solid fa-file-lines',
    json: 'fa-solid fa-file-code',
    yaml: 'fa-solid fa-file-code',
  }
  return iconMap[ext || ''] || 'fa-solid fa-file'
}

function switchToTab(path: string) {
  const file = fileStore.openFiles.find(f => f.path === path)
  if (file) {
    fileStore.currentFile = file
    // 加载该文件内容到编辑器
    editorStore.setCurrentFile(path)
  }
}

async function closeTab(path: string) {
  const isDirty = fileStore.unsavedFiles.has(path)

  if (isDirty) {
    // 简单处理：直接关闭（后续可加确认对话框）
    const confirmed = window.confirm('文件有未保存的更改，确定要关闭吗？')
    if (!confirmed) return
  }

  fileStore.closeFile(path)
  editorStore.clearFile(path)
}
</script>

<style scoped lang="scss">
.editor-tabs {
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.tabs-bar {
  display: flex;
  align-items: center;
  padding: 0 8px;
  gap: 4px;
  overflow-x: auto;
  min-height: 36px;

  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 2px;
  }
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: all 0.15s;
  max-width: 180px;

  &:hover {
    background: var(--bg-card);
    color: var(--text-primary);

    .tab-close {
      opacity: 1;
    }
  }

  &.active {
    color: var(--accent-primary);
    background: var(--bg-primary);
    border-bottom-color: var(--accent-primary);

    .tab-icon {
      color: var(--accent-primary);
    }
  }
}

.tab-icon {
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.tab-name {
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-dirty {
  color: var(--accent-warning);
  font-size: 8px;
  flex-shrink: 0;
}

.tab-close {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 50%;
  font-size: 10px;
  opacity: 0;
  transition: all 0.15s;
  flex-shrink: 0;

  &:hover {
    background: var(--accent-danger);
    color: white;
  }
}

.tabs-status {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 4px 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;

  i {
    font-size: 10px;
  }

  &.status-save {
    margin-left: auto;

    &.saving {
      color: var(--accent-warning);
    }

    &.unsaved {
      color: var(--accent-warning);
    }

    &.saved {
      color: var(--accent-success);
    }
  }
}
</style>
