<template>
  <div class="tree-node">
    <div
      class="node-row"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      :class="{ active: isActive }"
      :draggable="node.type === 'file'"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
      @contextmenu.prevent.stop="openNodeMenu"
      @click="handleClick"
    >
      <span
        v-if="node.type === 'directory'"
        class="node-arrow"
        :class="{ expanded: isExpanded }"
        @click.stop="toggleExpand"
      >
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </span>
      <span
        v-else
        class="node-arrow node-arrow--spacer"
      />

      <span
        class="node-icon"
        :class="`icon-${iconType}`"
      >
        <component :is="iconComponent" />
      </span>

      <span
        class="node-name"
        :title="node.name"
      >{{ displayName }}</span>
      <span
        v-if="isDirty"
        class="node-dirty"
        title="有未保存的更改"
      />
      <button
        class="node-menu-btn"
        title="更多操作"
        @click.stop="openNodeMenu"
      >
        ⋯
      </button>
    </div>

    <div
      v-if="menuOpen"
      class="node-menu"
      @click.stop
    >
      <button
        v-if="node.type === 'directory'"
        @click="emitAction('create-file')"
      >
        新建文件
      </button>
      <button
        v-if="node.type === 'directory'"
        @click="emitAction('create-directory')"
      >
        新建目录
      </button>
      <button @click="emitAction('rename')">
        重命名
      </button>
      <button
        class="danger"
        @click="emitAction('delete')"
      >
        移入回收站
      </button>
    </div>

    <div
      v-if="node.type === 'directory' && isExpanded"
      class="node-children"
    >
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        @file-click="$emit('file-click', $event)"
        @create-file="$emit('create-file', $event)"
        @create-directory="$emit('create-directory', $event)"
        @rename="$emit('rename', $event)"
        @delete="$emit('delete', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useFileStore } from '@/stores/file'
import type { FileNode } from '@/stores/file'
import { parseVolumeDir, parseChapterDir, parseSceneFileName } from '@/modules/scene/scenePath'

const props = defineProps<{
  node: FileNode
  depth: number
}>()

const emit = defineEmits<{
  (e: 'file-click', node: FileNode): void
  (e: 'create-file', node: FileNode): void
  (e: 'create-directory', node: FileNode): void
  (e: 'rename', node: FileNode): void
  (e: 'delete', node: FileNode): void
}>()

const fileStore = useFileStore()

const EXPANDED_KEY = 'moyun-expanded-dirs'

function getExpandedDirs(): string[] {
  try {
    return JSON.parse(localStorage.getItem(EXPANDED_KEY) || '[]')
  } catch { return [] }
}

function saveExpandedDirs(dirs: string[]) {
  try {
    localStorage.setItem(EXPANDED_KEY, JSON.stringify(dirs))
  } catch { /* localStorage 不可用时忽略 */ }
}

const isExpanded = ref(
  props.depth === 0 ||
  !!props.node.name.match(/^vol-\d+$/) ||
  !!props.node.name.match(/^ch-\d+$/) ||
  getExpandedDirs().includes(props.node.path)
)
const menuOpen = ref(false)

const displayName = computed(() => {
  const name = props.node.name
  if (props.node.type === 'directory') {
    const volNum = parseVolumeDir(name)
    if (volNum !== null) return `第${volNum}卷`
    const chNum = parseChapterDir(name)
    if (chNum !== null) return `第${chNum}章`
  } else {
    const secNum = parseSceneFileName(name)
    if (secNum !== null) return `第${secNum}场景`
  }
  return name
})

const iconType = computed(() => {
  if (props.node.type === 'directory') {
    return isExpanded.value ? 'folder-open' : 'folder'
  }
  const ext = props.node.name.split('.').pop()?.toLowerCase()
  if (['md', 'txt', 'markdown'].includes(ext || '')) return 'markdown'
  if (['json'].includes(ext || '')) return 'json'
  if (['yaml', 'yml'].includes(ext || '')) return 'yaml'
  if (['py', 'js', 'ts', 'css', 'scss', 'less', 'html', 'htm'].includes(ext || '')) return 'code'
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext || '')) return 'image'
  if (['pdf'].includes(ext || '')) return 'pdf'
  return 'file'
})

const iconComponent = computed(() => {
  const map: Record<string, string> = {
    'folder': 'folder',
    'folder-open': 'folder-open',
    'markdown': 'markdown',
    'json': 'code',
    'yaml': 'code',
    'code': 'code',
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

let _dragFlag = false

function handleClick() {
  if (_dragFlag) { _dragFlag = false; return }
  if (props.node.type === 'file') {
    emit('file-click', props.node)
  } else {
    toggleExpand()
  }
}

function handleDragStart(e: DragEvent) {
  if (props.node.type === 'file') {
    _dragFlag = true
    e.dataTransfer?.clearData()
    e.dataTransfer?.setData('text/plain', props.node.path)
    e.dataTransfer!.effectAllowed = 'copy'
  }
}

function handleDragEnd() {
  _dragFlag = false
}

function openNodeMenu() {
  menuOpen.value = true
  window.addEventListener('click', closeMenu, { once: true })
}

function closeMenu() {
  menuOpen.value = false
}

function emitAction(action: 'create-file' | 'create-directory' | 'rename' | 'delete') {
  menuOpen.value = false
  if (action === 'create-file') emit('create-file', props.node)
  else if (action === 'create-directory') emit('create-directory', props.node)
  else if (action === 'rename') emit('rename', props.node)
  else emit('delete', props.node)
}

onBeforeUnmount(() => {
  window.removeEventListener('click', closeMenu)
})
</script>

<style scoped lang="scss">
.tree-node {
  user-select: none;
  animation: fade-in-up 0.25s ease both;
  position: relative;
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
    .node-menu-btn { opacity: 1; }
  }

  &.active {
    background: linear-gradient(135deg, rgba(201, 169, 110, 0.12), rgba(201, 169, 110, 0.04));
    color: var(--gold-primary);
    border-left: 2px solid var(--gold-primary);

    .node-name { font-weight: 500; }
  }
}

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
}

.icon-folder::before { content: '📁'; font-size: 12px; }
.icon-folder-open::before { content: '📂'; font-size: 12px; }
.icon-markdown::before { content: 'MD'; font-size: 8px; color: var(--gold-primary); }
.icon-json::before { content: '{ }'; font-size: 9px; color: var(--gold-primary); }
.icon-yaml::before { content: '~'; font-size: 13px; color: var(--vermillion-light); }
.icon-code::before { content: '</>'; font-size: 8px; font-weight: 700; color: var(--jade-light); }
.icon-image::before { content: '▣'; font-size: 11px; color: var(--gold-primary); }
.icon-pdf::before { content: 'PDF'; font-size: 7px; color: var(--vermillion-light); }
.icon-file::before { content: '□'; font-size: 11px; }

.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 400;
  font-size: 13px;
}

.node-dirty {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold-primary);
  flex-shrink: 0;
  animation: dirty-pulse 1.5s ease-in-out infinite;
}

.node-menu-btn {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--text-muted-ink);
  cursor: pointer;
  opacity: 0;
}

.node-menu-btn:hover {
  border-color: var(--border-ink);
  color: var(--gold-primary);
}

.node-menu {
  position: absolute;
  right: 8px;
  top: 28px;
  z-index: 30;
  min-width: 116px;
  padding: 4px;
  border: 1px solid var(--border-ink);
  border-radius: 6px;
  background: var(--ink-dark);
  box-shadow: 0 8px 24px rgba(0, 0, 0, .28);
}

.node-menu button {
  display: block;
  width: 100%;
  padding: 7px 9px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  font-size: 12px;
}

.node-menu button:hover {
  background: var(--ink-hover);
  color: var(--gold-primary);
}

.node-menu button.danger:hover {
  color: var(--vermillion-light);
}

@keyframes dirty-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
