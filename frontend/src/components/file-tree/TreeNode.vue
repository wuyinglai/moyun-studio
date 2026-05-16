<template>
  <div class="tree-node">
    <div
      class="node-row"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      :class="{ active: isActive }"
      :draggable="node.type === 'file'"
      @dragstart="handleDragStart"
      @click="handleClick"
    >
      <!-- 展开箭头 / 缩进占位 -->
      <span v-if="node.type === 'directory'" class="node-arrow" :class="{ expanded: isExpanded }" @click.stop="toggleExpand">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </span>
      <span v-else class="node-arrow node-arrow--spacer"></span>

      <!-- 文件类型图标 -->
      <span class="node-icon" :class="`icon-${iconType}`">
        <component :is="iconComponent" />
      </span>

      <!-- 文件名 -->
      <span class="node-name" :title="node.name">{{ displayName }}</span>

      <!-- 修改标记 -->
      <span v-if="isDirty" class="node-dirty" title="有未保存的更改"></span>
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
  } catch { return [] }
}

function saveExpandedDirs(dirs: string[]) {
  localStorage.setItem(EXPANDED_KEY, JSON.stringify(dirs))
}

const isExpanded = ref(
  props.depth === 0 ||
  !!props.node.name.match(/^vol-\d+$/) ||
  !!props.node.name.match(/^ch-\d+$/) ||
  getExpandedDirs().includes(props.node.path)
)

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

// 图标类型 — 使用内联 SVG
const iconType = computed(() => {
  if (props.node.type === 'directory') {
    return isExpanded.value ? 'folder-open' : 'folder'
  }
  const ext = props.node.name.split('.').pop()?.toLowerCase()
  if (['md', 'txt', 'markdown'].includes(ext || '')) return 'markdown'
  if (['json'].includes(ext || '')) return 'json'
  if (['yaml', 'yml'].includes(ext || '')) return 'yaml'
  if (['py'].includes(ext || '')) return 'python'
  if (['js'].includes(ext || '')) return 'javascript'
  if (['ts'].includes(ext || '')) return 'typescript'
  if (['css', 'scss', 'less'].includes(ext || '')) return 'css'
  if (['html', 'htm'].includes(ext || '')) return 'html'
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext || '')) return 'image'
  if (['pdf'].includes(ext || '')) return 'pdf'
  return 'file'
})

// 简化处理：用文字标签代替复杂 SVG
const iconComponent = computed(() => {
  const map: Record<string, string> = {
    'folder': 'folder',
    'folder-open': 'folder-open',
    'markdown': 'markdown',
    'json': 'code',
    'yaml': 'code',
    'python': 'code',
    'javascript': 'code',
    'typescript': 'code',
    'css': 'code',
    'html': 'code',
    'image': 'image',
    'pdf': 'pdf',
    'file': 'file',
  }
  return map[iconType.value] || 'file'
})

const isActive = computed(() => fileStore.currentFile?.path === props.node.path)
const isDirty = computed(() => fileStore.unsavedFiles.has(props.node.path))

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

function handleDragStart(e: DragEvent) {
  if (props.node.type === 'file') {
    e.dataTransfer?.setData('text/plain', props.node.path)
    e.dataTransfer!.effectAllowed = 'copy'
  }
}
</script>

<style scoped lang="scss">
.tree-node {
  user-select: none;
  animation: fade-in-up 0.25s ease both;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  margin: 1px 6px;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  font-size: 13px;
  color: var(--text-ink);
  position: relative;

  &:hover {
    background: var(--ink-hover);
    color: var(--text-warm-white);

    .node-arrow { color: var(--text-muted-ink); }
  }

  &.active {
    background: linear-gradient(135deg, rgba(201, 169, 110, 0.12), rgba(201, 169, 110, 0.04));
    color: var(--gold-primary);
    border-left: 2px solid var(--gold-primary);

    .node-name { font-weight: 500; }
  }
}

/* ── 箭头 ── */
.node-arrow {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-faint);
  transition: transform var(--transition-fast);
  flex-shrink: 0;

  &--spacer { visibility: hidden; }

  &.expanded {
    transform: rotate(90deg);
  }
}

/* ── 图标 ── */
.node-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  border-radius: 3px;

  // 用文字图标简化而优雅
  &.icon-folder,
  &.icon-folder-open {
    font-size: 13px;
  }
}

/* 用序列字符替代 Font Awesome 图标 */
.icon-folder::before { content: '📁'; font-size: 12px; }
.icon-folder-open::before { content: '📂'; font-size: 12px; }
.icon-markdown::before { content: '📝'; font-size: 11px; }
.icon-json::before { content: '{ }'; font-size: 9px; color: var(--gold-primary); }
.icon-yaml::before { content: '~'; font-size: 13px; color: var(--vermillion-light); }
.icon-python::before { content: '🐍'; font-size: 11px; }
.icon-javascript::before { content: 'JS'; font-size: 8px; font-weight: 700; color: var(--gold-primary); letter-spacing: 0; }
.icon-typescript::before { content: 'TS'; font-size: 8px; font-weight: 700; color: var(--jade-light); letter-spacing: 0; }
.icon-css::before { content: '# '; font-size: 9px; color: var(--vermillion-light); }
.icon-html::before { content: '<>'; font-size: 8px; font-weight: 700; color: var(--gold-primary); }
.icon-image::before { content: '🖼'; font-size: 11px; }
.icon-pdf::before { content: '📕'; font-size: 11px; }
.icon-file::before { content: '📄'; font-size: 11px; }

/* ── 文件名 ── */
.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 400;
  font-size: 13px;
}

/* ── 脏标记 ── */
.node-dirty {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold-primary);
  flex-shrink: 0;
  animation: dirty-pulse 1.5s ease-in-out infinite;
}

@keyframes dirty-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── 子节点 ── */
.node-children {
  // padding 由样式绑定控制
}
</style>
