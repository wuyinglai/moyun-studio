<template>
  <div class="editor-toolbar">
    <!-- 左侧：格式化按钮 -->
    <div class="toolbar-group">
      <button
        v-for="btn in formatButtons"
        :key="btn.action"
        class="toolbar-btn"
        :title="btn.title"
        @click="handleFormat(btn.action)"
      >
        <i :class="btn.icon"></i>
      </button>
    </div>

    <div class="toolbar-divider"></div>

    <!-- 插入按钮 -->
    <div class="toolbar-group">
      <button class="toolbar-btn" title="插入素材" @click="insertMaterial">
        <i class="fa-solid fa-folder-plus"></i>
      </button>
      <button class="toolbar-btn" title="插入时间线" @click="insertTimeline">
        <i class="fa-solid fa-clock"></i>
      </button>
    </div>

    <div class="toolbar-divider"></div>

    <!-- AI 生成 -->
    <div class="toolbar-group">
      <button
        class="toolbar-btn toolbar-btn--primary"
        title="AI 续写"
        :disabled="llmStore.isGenerating"
        @click="aiGenerate"
      >
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        <span>AI续写</span>
      </button>
    </div>

    <div class="toolbar-spacer"></div>

    <!-- 右侧：保存按钮 -->
    <div class="toolbar-group">
      <button
        class="toolbar-btn"
        :class="{ 'toolbar-btn--success': hasUnsaved }"
        title="保存 (Ctrl+S)"
        @click="saveFile"
      >
        <i class="fa-solid fa-floppy-disk"></i>
        <span>保存</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useLLMStore } from '@/stores/llm'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'

const fileStore = useFileStore()
const editorStore = useEditorStore()
const llmStore = useLLMStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()

const formatButtons = [
  { action: 'h1', icon: 'fa-solid fa-heading', title: '一级标题' },
  { action: 'h2', icon: 'fa-solid fa-heading', title: '二级标题' },
  { action: 'bold', icon: 'fa-solid fa-bold', title: '粗体' },
  { action: 'italic', icon: 'fa-solid fa-italic', title: '斜体' },
  { action: 'strikethrough', icon: 'fa-solid fa-strikethrough', title: '删除线' },
  { action: 'quote', icon: 'fa-solid fa-quote-left', title: '引用' },
  { action: 'ul', icon: 'fa-solid fa-list-ul', title: '无序列表' },
  { action: 'ol', icon: 'fa-solid fa-list-ol', title: '有序列表' },
  { action: 'hr', icon: 'fa-solid fa-minus', title: '分隔线' },
]

const hasUnsaved = computed(() => {
  return fileStore.currentFile && fileStore.unsavedFiles.has(fileStore.currentFile.path)
})

function handleFormat(action: string) {
  // 格式化操作会通过事件发送到编辑器
  // 这里可以扩展更多格式化功能
  const formats: Record<string, { before: string; after: string }> = {
    h1: { before: '# ', after: '' },
    h2: { before: '## ', after: '' },
    bold: { before: '**', after: '**' },
    italic: { before: '*', after: '*' },
    strikethrough: { before: '~~', after: '~~' },
    quote: { before: '> ', after: '' },
    ul: { before: '- ', after: '' },
    ol: { before: '1. ', after: '' },
    hr: { before: '\n---\n', after: '' },
  }

  const format = formats[action]
  if (format) {
    // 触发编辑器插入格式化文本
    window.dispatchEvent(new CustomEvent('editor:format', { detail: format }))
  }
}

function insertMaterial() {
  window.dispatchEvent(new CustomEvent('editor:insert-material'))
}

function insertTimeline() {
  const template = `
## 时间线

| 时间 | 事件 | 备注 |
|------|------|------|
|      |      |      |
`
  window.dispatchEvent(new CustomEvent('editor:insert', { detail: template }))
}

async function aiGenerate() {
  if (!llmStore.isConnected) {
    notification.warning('请先连接 LLM')
    return
  }

  if (!projectStore.currentProject || !fileStore.currentFile) {
    notification.warning('请先打开项目和文件')
    return
  }

  // 触发 AI 生成
  window.dispatchEvent(new CustomEvent('editor:ai-generate'))
}

async function saveFile() {
  if (!projectStore.currentProject || !fileStore.currentFile) {
    return
  }

  const content = editorStore.getContent(fileStore.currentFile.path)

  try {
    await fileStore.saveFile(
      projectStore.currentProject.id,
      fileStore.currentFile.path,
      content
    )
    notification.success('文件已保存')
  } catch (e) {
    notification.error('保存失败')
  }
}

// 监听键盘快捷键
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      saveFile()
    }
  })
}
</script>

<style scoped lang="scss">
.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 12px;
  transition: all 0.15s;

  i {
    font-size: 13px;
  }

  &:hover:not(:disabled) {
    background: var(--bg-card);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &--primary {
    background: var(--accent-primary);
    color: white;

    &:hover:not(:disabled) {
      filter: brightness(1.1);
      color: white;
    }
  }

  &--success {
    background: var(--accent-success);
    color: white;

    &:hover {
      filter: brightness(1.1);
      color: white;
    }
  }
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--border-color);
  margin: 0 4px;
}

.toolbar-spacer {
  flex: 1;
}
</style>
