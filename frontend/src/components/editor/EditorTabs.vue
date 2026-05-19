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
        <i
          :class="getFileIcon(file.name)"
          class="tab-icon"
        />

        <!-- 文件名 -->
        <span class="tab-name">{{ file.name }}</span>

        <!-- 脏标记 -->
        <span
          v-if="fileStore.unsavedFiles.has(file.path)"
          class="tab-dirty"
        >●</span>

        <!-- 关闭按钮 -->
        <button
          class="tab-close"
          title="关闭"
          @click.stop="closeTab(file.path)"
        >
          <i class="fa-solid fa-times" />
        </button>
      </div>
    </div>

    <!-- 状态栏 -->
    <div
      v-if="fileStore.currentFile"
      class="tabs-status"
    >
      <span class="status-item">
        <i class="fa-solid fa-font" />
        {{ editorStore.wordCount.toLocaleString() }} 字
      </span>
      <span class="status-item">
        <i class="fa-solid fa-location-dot" />
        Ln {{ editorStore.cursorPosition.line }}, Col {{ editorStore.cursorPosition.col }}
      </span>
      <span
        class="status-item status-save"
        :class="saveStatusClass"
      >
        {{ saveStatusText }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'

const fileStore = useFileStore()
const editorStore = useEditorStore()

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
  background: var(--ink-mid);
  border-bottom: 1px solid var(--border-ink);
  flex-shrink: 0;
}

.tabs-bar {
  display: flex;
  align-items: center;
  padding: 0 8px;
  gap: 2px;
  overflow-x: auto;
  min-height: 38px;

  &::-webkit-scrollbar { height: 3px; }
  &::-webkit-scrollbar-thumb {
    background: var(--border-ink);
    border-radius: 2px;
  }
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted-ink);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  border-radius: 6px 6px 0 0;
  transition: all var(--transition-fast);
  max-width: 160px;
  margin-bottom: -1px;
  position: relative;

  &:hover {
    background: rgba(255, 255, 255, 0.03);
    color: var(--text-ink);

    .tab-close { opacity: 1; }
  }

  &.active {
    color: var(--gold-primary);
    background: var(--ink-deep);
    border-bottom-color: var(--gold-primary);

    .tab-icon { color: var(--gold-primary); }

    &::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 20%;
      right: 20%;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
    }
  }
}

.tab-icon {
  font-size: 12px;
  color: var(--text-faint);
  flex-shrink: 0;
}

.tab-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}

.tab-dirty {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold-primary);
  flex-shrink: 0;
  animation: dirtyPulse 1.5s ease-in-out infinite;
}

@keyframes dirtyPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.tab-close {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-faint);
  cursor: pointer;
  border-radius: 50%;
  font-size: 9px;
  opacity: 0;
  transition: all var(--transition-fast);
  flex-shrink: 0;

  &:hover {
    background: var(--vermillion);
    color: white;
  }
}

.tabs-status {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 5px 16px;
  background: var(--ink-mid);
  border-top: 1px solid var(--border-ink);
  font-size: 11px;
  color: var(--text-faint);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 400;

  i { font-size: 10px; }

  &.status-save {
    margin-left: auto;

    &.saving { color: var(--gold-primary); }
    &.unsaved { color: var(--gold-primary); }
    &.saved { color: var(--jade-light); }
  }
}
</style>
