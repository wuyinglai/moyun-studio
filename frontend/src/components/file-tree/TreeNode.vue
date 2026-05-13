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
      <span class="node-name" :title="node.name">{{ displayName }}</span>

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

const props = defineProps<{
  node: FileNode
  depth: number
}>()

const emit = defineEmits<{
  (e: 'file-click', node: FileNode): void
}>()

const fileStore = useFileStore()

const EXPANDED_KEY = 'moyun-expanded-dirs'

function getExpandedDirs(): string[] {
  try {
    return JSON.parse(localStorage.getItem(EXPANDED_KEY) || '[]')
  } catch {
    return []
  }
}

function saveExpandedDirs(dirs: string[]) {
  localStorage.setItem(EXPANDED_KEY, JSON.stringify(dirs))
}

const isExpanded = ref(
  props.depth === 0 ||
  props.node.name.match(/^vol-\d+$/) !== null ||
  props.node.name.match(/^ch-\d+$/) !== null ||
  getExpandedDirs().includes(props.node.path)
)

// 显示友好的目录名：vol-01 → 第1卷, ch-001 → 第1章, sec-001.md → 第1节
const displayName = computed(() => {
  const name = props.node.name
  if (props.node.type === 'directory') {
    const volMatch = name.match(/^vol-0*(\d+)$/)
    if (volMatch) return `第${volMatch[1]}卷`
    const chMatch = name.match(/^ch-0*(\d+)$/)
    if (chMatch) return `第${chMatch[1]}章`
  } else {
    const secMatch = name.match(/^sec-0*(\d+)\.md$/)
    if (secMatch) return `第${secMatch[1]}节`
  }
  return name
})

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
  const dirs = getExpandedDirs()
  if (isExpanded.value) {
    if (!dirs.includes(props.node.path)) dirs.push(props.node.path)
  } else {
    const idx = dirs.indexOf(props.node.path)
    if (idx !== -1) dirs.splice(idx, 1)
  }
  saveExpandedDirs(dirs)
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
  gap: 8px;
  padding: 7px 12px;
  margin: 0 4px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  font-size: 13px;
  color: var(--text-primary);

  &:hover {
    background: var(--bg-hover);
  }

  &.active {
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    color: white;
    box-shadow: 0 2px 8px rgba(107, 140, 255, 0.3);

    .node-icon,
    .node-arrow {
      color: white;
    }

    .node-dirty {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

.node-arrow {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: var(--text-muted);
  transition: transform 0.2s ease;

  &--spacer {
    visibility: hidden;
  }

  &.expanded {
    transform: rotate(90deg);
  }
}

.node-icon {
  width: 18px;
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color 0.2s ease;
}

:deep(.fa-folder),
:deep(.fa-folder-open) {
  color: var(--accent-warning);
}

.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 400;
}

.node-dirty {
  color: var(--accent-warning);
  font-size: 9px;
  font-weight: bold;
  animation: dirtyPulse 2s ease-in-out infinite;
}

@keyframes dirtyPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.node-children {
  // 子节点缩进由 paddingLeft 控制
}
</style>
