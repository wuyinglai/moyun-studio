<template>
  <div class="app-layout" data-testid="main-entry-root">
    <!-- 左栏：文件导航 -->
    <nav
      class="panel-left"
      :style="{ width: leftWidth }"
      aria-label="文件导航"
    >
      <FileTree />
    </nav>

    <!-- 中栏分隔条 -->
    <div
      class="divider divider-v"
      @mousedown="startHDrag"
    />

    <!-- 中栏：主编辑区 -->
    <main
      class="panel-center"
      :style="{ width: centerWidth }"
      data-testid="editor-panel"
    >
      <div
        class="center-top"
        :style="{ height: topHeight }"
      >
        <ErrorBoundary
          title="编辑器加载出错"
          description="编辑器发生了意外错误，你可以重试或刷新页面。"
        >
          <div class="area-editor">
            <EditorTabs />
            <EditorToolbar />
            <MarkdownEditor />
          </div>
        </ErrorBoundary>
      </div>
      <div
        class="divider divider-h"
        @mousedown="startVDrag"
      />
      <div
        class="center-bottom"
        :style="{ height: bottomHeight }"
      >
        <ErrorBoundary
          title="对话面板出错"
          description="对话面板发生了意外错误，你可以重试或刷新页面。"
        >
          <div class="area-chat">
            <ChatPanel />
          </div>
        </ErrorBoundary>
      </div>
    </main>

    <!-- 右栏分隔条 -->
    <div
      class="divider divider-v"
      @mousedown="startRightDrag"
    />

    <!-- 右栏：辅助面板 -->
    <aside
      class="panel-right"
      :style="{ width: rightWidth }"
      aria-label="辅助面板"
    >
      <ErrorBoundary
        title="辅助面板出错"
        description="辅助面板发生了意外错误，你可以重试或刷新页面。"
      >
        <RightPanel />
      </ErrorBoundary>
    </aside>
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
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import { getStorage, setStorage, STORAGE_KEYS } from '@/utils/storage'
import { saveConfig as saveRemoteConfig } from '@/services/configService'

// ── 布局尺寸状态 ──────────────────────────────────
const DEFAULT_LEFT = 20
const DEFAULT_RIGHT = 25
const DEFAULT_TOP = 75

function loadSavedSizes() {
  const saved = getStorage<{ left: number; right: number; top: number } | null>(STORAGE_KEYS.LAYOUT_SIZES, null)
  if (saved) {
    return {
      left: Math.max(10, Math.min(60, saved.left)),
      right: Math.max(10, Math.min(60, saved.right)),
      top: Math.max(15, Math.min(85, saved.top)),
    }
  }
  return { left: DEFAULT_LEFT, right: DEFAULT_RIGHT, top: DEFAULT_TOP }
}

const saved = loadSavedSizes()
const leftWidth = ref(`${saved.left}%`)
const rightWidth = ref(`${saved.right}%`)
const centerWidth = ref(`${100 - saved.left - saved.right}%`)
const topHeight = ref(`${saved.top}%`)
const bottomHeight = ref(`${100 - saved.top}%`)

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

  // 持久化布局尺寸 M0704 / G0104
  setStorage(STORAGE_KEYS.LAYOUT_SIZES, {
    left: Math.round(parseFloat(leftWidth.value) * 100) / 100,
    right: Math.round(parseFloat(rightWidth.value) * 100) / 100,
    top: Math.round(parseFloat(topHeight.value) * 100) / 100,
  })
  // 同步到后端 .config.json
  saveRemoteConfig({
    layout: {
      left: Math.round(parseFloat(leftWidth.value) * 100) / 100,
      right: Math.round(parseFloat(rightWidth.value) * 100) / 100,
      editorChat: Math.round(parseFloat(topHeight.value) * 100) / 100,
    },
  }).catch(() => {}) // 静默失败，localStorage 兜底
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
  background: var(--ink-dark);
  flex-shrink: 0;
  border-right: 1px solid var(--border-ink);
}

.panel-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background: var(--ink-deep);
}

.panel-right {
  height: 100%;
  overflow-y: auto;
  background: var(--ink-dark);
  flex-shrink: 0;
  border-left: 1px solid var(--border-ink);
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
  border-top: 1px solid var(--border-ink);
  background: var(--ink-deep);
}

// ── 分隔条 ────────────────────────────────────────
.divider {
  flex-shrink: 0;
  background: var(--border-ink);
  position: relative;
  transition: all var(--transition-normal);
  z-index: 10;

  &::before {
    content: '';
    position: absolute;
    transition: opacity var(--transition-normal);
    opacity: 0;
  }

  &:hover {
    background: var(--gold-primary);

    &::before {
      opacity: 1;
    }
  }

  &-v {
    width: 5px;
    cursor: col-resize;

    &::before {
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 2px;
      height: 24px;
      background: linear-gradient(180deg, transparent, var(--gold-primary), transparent);
    }
  }

  &-h {
    height: 5px;
    cursor: row-resize;

    &::before {
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      height: 2px;
      width: 40px;
      background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
    }
  }
}
</style>
