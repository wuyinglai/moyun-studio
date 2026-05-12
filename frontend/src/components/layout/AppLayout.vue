<template>
  <div class="app-layout">
    <div id="panel-left" class="panel-left">
      <FileTree />
    </div>

    <div id="panel-center" class="panel-center">
      <div id="area-editor" class="area-editor">
        <EditorTabs />
        <EditorToolbar />
        <MarkdownEditor />
      </div>
      <div id="area-chat" class="area-chat">
        <ChatPanel />
      </div>
    </div>

    <div id="panel-right" class="panel-right">
      <RightPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import Split from 'split.js'

const FileTree = defineAsyncComponent(() => import('@/components/file-tree/FileTree.vue'))
const EditorTabs = defineAsyncComponent(() => import('@/components/editor/EditorTabs.vue'))
const EditorToolbar = defineAsyncComponent(() => import('@/components/editor/EditorToolbar.vue'))
const MarkdownEditor = defineAsyncComponent(() => import('@/components/editor/MarkdownEditor.vue'))
const ChatPanel = defineAsyncComponent(() => import('@/components/chat/ChatPanel.vue'))
const RightPanel = defineAsyncComponent(() => import('@/components/right-panel/RightPanel.vue'))

let hSplit: any = null
let vSplit: any = null

onMounted(() => {
  const savedSizes = localStorage.getItem('layout-sizes')
  const sizes = savedSizes ? JSON.parse(savedSizes) : [20, 55, 25]

  hSplit = Split(['#panel-left', '#panel-center', '#panel-right'], {
    sizes,
    minSize: [200, 400, 280],
    gutterSize: 6,
    onDrag: (s: number[]) => {
      localStorage.setItem('layout-sizes', JSON.stringify(s))
    }
  })

  const savedVSizes = localStorage.getItem('editor-chat-sizes')
  const vSizes = savedVSizes ? JSON.parse(savedVSizes) : [75, 25]

  vSplit = Split(['#area-editor', '#area-chat'], {
    direction: 'vertical',
    sizes: vSizes,
    minSize: [200, 100],
    gutterSize: 6,
    onDrag: (s: number[]) => {
      localStorage.setItem('editor-chat-sizes', JSON.stringify(s))
    }
  })
})

onBeforeUnmount(() => {
  hSplit?.destroy()
  vSplit?.destroy()
})
</script>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-primary);
  color: var(--text-primary);
  display: flex;
}

.panel-left {
  height: 100%;
  overflow-y: auto;
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.panel-center {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
  min-width: 0;
}

.area-editor {
  height: 100%;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.area-chat {
  height: 100%;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.panel-right {
  height: 100%;
  overflow-y: auto;
  background: var(--bg-secondary);
  flex-shrink: 0;
}

:deep(.gutter) {
  background-color: var(--border-color);
  background-repeat: no-repeat;
  background-position: 50%;
  transition: background-color 0.2s;
}

:deep(.gutter:hover) {
  background-color: var(--accent-primary);
}

:deep(.gutter.gutter-horizontal) {
  cursor: col-resize;
  width: 6px !important;
}

:deep(.gutter.gutter-vertical) {
  cursor: row-resize;
  height: 6px !important;
}
</style>
