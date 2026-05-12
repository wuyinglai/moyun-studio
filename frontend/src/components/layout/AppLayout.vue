<template>
  <div class="app-layout">
    <!-- Split.js 会在这三个 div 之间插入 gutter -->
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
import { onMounted, onBeforeUnmount } from 'vue'
import Split from 'split.js'
// CSS 已通过 index.html CDN 引入

import FileTree from '@/components/file-tree/FileTree.vue'
import EditorTabs from '@/components/editor/EditorTabs.vue'
import EditorToolbar from '@/components/editor/EditorToolbar.vue'
import MarkdownEditor from '@/components/editor/MarkdownEditor.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import RightPanel from '@/components/right-panel/RightPanel.vue'

let hSplit: InstanceType<typeof Split> | null = null   // 水平分隔：左|中|右
let vSplit: InstanceType<typeof Split> | null = null   // 垂直分隔：编辑区|聊天区

onMounted(() => {
  // 第一层：水平三栏（左 | 中 | 右）
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

  // 第二层：中间面板垂直分隔（编辑区 | 聊天区）
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
  background: var(--bg-primary);
  color: var(--text-primary);
}

.panel-left {
  overflow-y: auto;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
}

.panel-center {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.area-editor {
  overflow-y: auto;
  flex: 1;
}

.area-chat {
  overflow-y: auto;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.panel-right {
  overflow-y: auto;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
}
</style>
