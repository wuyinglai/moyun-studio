<template>
  <div class="tree-node">
    <!-- 节点行 -->
    <div
      class="node-row"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      :class="{ active: isActive }"
      @click="handleClick"
    >
      <!-- 展开/折叠箭头 -->
      <span
        v-if="node.type === 'directory'"
        class="node-arrow"
        :class="{ expanded: isExpanded }"
        @click.stop="toggleExpand"
      >
        <i class="fa-solid fa-chevron-right"></i>
      </span>
      <span v-else class="node-arrow node-arrow--spacer"></span>

      <!-- 图标 -->
      <i :class="iconClass" class="node-icon"></i>

      <!-- 文件名 -->
      <span class="node-name">{{ node.name }}</span>

      <!-- 脏标记 -->
      <span v-if="isDirty" class="node-dirty" title="有未保存的更改">●</span>
    </div>

    <!-- 子节点 -->
    <div v-if="node.type === 'directory' && isExpanded" class="node-children">
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        @file-click="$emit('file-click', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useFileStore } from '@/stores/file'
import type { FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'

const props = defineProps<{
  node: FileNode
  depth: number
}>()

const emit = defineEmits<{
  (e: 'file-click', node: FileNode): void
}>()

const fileStore = useFileStore()
const editorStore = useEditorStore()

const isExpanded = ref(props.depth === 0) // 根目录默认展开

// 根据文件类型获取图标
const iconClass = computed(() => {
  if (props.node.type === 'directory') {
    return isExpanded.value
      ? 'fa-solid fa-folder-open'
      : 'fa-solid fa-folder'
  }

  const ext = props.node.name.split('.').pop()?.toLowerCase()
  const iconMap: Record<string, string> = {
    md: 'fa-solid fa-file-lines',     // Markdown
    txt: 'fa-solid fa-file-lines',
    json: 'fa-solid fa-file-code',
    yaml: 'fa-solid fa-file-code',
    yml: 'fa-solid fa-file-code',
    py: 'fa-brands fa-python',
    js: 'fa-brands fa-js',
    ts: 'fa-solid fa-file-code',
    css: 'fa-solid fa-file-code',
    html: 'fa-solid fa-file-code',
    png: 'fa-solid fa-file-image',
    jpg: 'fa-solid fa-file-image',
    jpeg: 'fa-solid fa-file-image',
    gif: 'fa-solid fa-file-image',
    svg: 'fa-solid fa-file-image',
    pdf: 'fa-solid fa-file-pdf',
    doc: 'fa-solid fa-file-word',
    docx: 'fa-solid fa-file-word',
    xls: 'fa-solid fa-file-excel',
    xlsx: 'fa-solid fa-file-excel',
  }
  return iconMap[ext || ''] || 'fa-solid fa-file'
})

const isActive = computed(() => {
  return fileStore.currentFile?.path === props.node.path
})

const isDirty = computed(() => {
  return fileStore.unsavedFiles.has(props.node.path)
})

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function handleClick() {
  if (props.node.type === 'file') {
    emit('file-click', props.node)
  } else {
    toggleExpand()
  }
}
</script>

<style scoped lang="scss">
.tree-node {
  user-select: none;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
  font-size: 13px;
  color: var(--text-primary);

  &:hover {
    background: var(--bg-card);
  }

  &.active {
    background: var(--accent-primary);
    color: white;

    .node-icon,
    .node-arrow {
      color: white;
    }
  }
}

.node-arrow {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: var(--text-muted);
  transition: transform 0.2s;

  &--spacer {
    visibility: hidden;
  }

  &.expanded {
    transform: rotate(90deg);
  }
}

.node-icon {
  width: 16px;
  color: var(--text-muted);
  flex-shrink: 0;

  // 文件夹颜色
  .fa-folder,
  .fa-folder-open {
    color: var(--accent-warning);
  }
}

.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-dirty {
  color: var(--accent-warning);
  font-size: 8px;
}

.node-children {
  // 子节点缩进由 paddingLeft 控制
}
</style>
