<template>
  <div class="app-layout">
    <!-- 左栏 -->
    <div class="panel-left" :style="{ width: leftWidth }">
      <FileTree />
    </div>

    <!-- 中栏分隔条 -->
    <div class="divider divider-v" @mousedown="startHDrag"></div>

    <!-- 中栏 -->
    <div class="panel-center" :style="{ width: centerWidth }">
      <div class="center-top" :style="{ height: topHeight }">
        <div class="area-editor">
          <EditorTabs />
          <EditorToolbar />
          <MarkdownEditor />
        </div>
      </div>
      <div class="divider divider-h" @mousedown="startVDrag"></div>
      <div class="center-bottom" :style="{ height: bottomHeight }">
        <div class="area-chat">
          <ChatPanel />
        </div>
      </div>
    </div>

    <!-- 右栏分隔条 -->
    <div class="divider divider-v" @mousedown="startRightDrag"></div>

    <!-- 右栏 -->
    <div class="panel-right" :style="{ width: rightWidth }">
      <RightPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileTree from '@/components/file-tree/FileTree.vue'
import EditorTabs from '@/components/editor/EditorTabs.vue'
import EditorToolbar from '@/components/editor/EditorToolbar.vue'
import MarkdownEditor from '@/components/editor/MarkdownEditor.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import RightPanel from '@/components/right-panel/RightPanel.vue'

// ── 布局尺寸状态 ──────────────────────────────────
const DEFAULT_LEFT = 20
const DEFAULT_RIGHT = 25
const DEFAULT_TOP = 75

const leftWidth = ref(`${DEFAULT_LEFT}%`)
const rightWidth = ref(`${DEFAULT_RIGHT}%`)
const centerWidth = ref(`${100 - DEFAULT_LEFT - DEFAULT_RIGHT}%`)
const topHeight = ref(`${DEFAULT_TOP}%`)
const bottomHeight = ref(`${100 - DEFAULT_TOP}%`)

let dragging: 'h-left' | 'h-right' | 'v' | null = null

// ── 拖拽 ──────────────────────────────────────────
function startHDrag(e: MouseEvent) {
  dragging = 'h-left'
  document.addEventListener('mousemove', onHDrag)
  document.addEventListener('mouseup', stopDrag)
  e.preventDefault()
}

function startRightDrag(e: MouseEvent) {
  dragging = 'h-right'
  document.addEventListener('mousemove', onHDrag)
  document.addEventListener('mouseup', stopDrag)
  e.preventDefault()
}

function startVDrag(e: MouseEvent) {
  dragging = 'v'
  document.addEventListener('mousemove', onVDrag)
  document.addEventListener('mouseup', stopDrag)
  e.preventDefault()
}

function stopDrag() {
  dragging = null
  document.removeEventListener('mousemove', onHDrag)
  document.removeEventListener('mousemove', onVDrag)
  document.removeEventListener('mouseup', stopDrag)
}

function onHDrag(e: MouseEvent) {
  if (!dragging || dragging === 'v') return
  const rect = document.querySelector('.app-layout')?.getBoundingClientRect()
  if (!rect) return
  const pct = ((e.clientX - rect.left) / rect.width) * 100
  const MIN_PCT = 10
  const MAX_PCT = 60
  if (dragging === 'h-left') {
    const l = Math.max(MIN_PCT, Math.min(MAX_PCT, pct))
    leftWidth.value = `${l}%`
    centerWidth.value = `${100 - l - parseFloat(rightWidth.value)}%`
  } else {
    const r = Math.max(MIN_PCT, Math.min(MAX_PCT, 100 - pct))
    rightWidth.value = `${r}%`
    centerWidth.value = `${100 - r - parseFloat(leftWidth.value)}%`
  }
}

function onVDrag(e: MouseEvent) {
  if (dragging !== 'v') return
  const rect = document.querySelector('.panel-center')?.getBoundingClientRect()
  if (!rect) return
  const pct = ((e.clientY - rect.top) / rect.height) * 100
  const t = Math.max(15, Math.min(85, pct))
  topHeight.value = `${t}%`
  bottomHeight.value = `${100 - t}%`
}
</script>

<style scoped lang="scss">
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.panel-left {
  height: 100%;
  overflow-y: auto;
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.panel-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.panel-right {
  height: 100%;
  overflow-y: auto;
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.center-top {
  overflow: hidden;
  flex-shrink: 0;
}

.center-bottom {
  overflow: hidden;
  flex-shrink: 0;
}

.area-editor {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.area-chat {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
}

// ── 分隔条 ────────────────────────────────────────
.divider {
  flex-shrink: 0;
  background-color: var(--border-color);
  position: relative;
  transition: background-color 0.15s;
  z-index: 10;

  &:hover {
    background-color: var(--accent-primary);
  }

  &-v {
    width: 6px;
    cursor: col-resize;
  }

  &-h {
    height: 6px;
    cursor: row-resize;
  }
}
</style>
