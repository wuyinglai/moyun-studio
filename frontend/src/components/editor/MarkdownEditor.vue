<template>
  <div class="markdown-editor" ref="editorContainer">
    <!-- 空状态 -->
    <div v-if="!fileStore.currentFile" class="editor-empty">
      <i class="fa-solid fa-file-lines"></i>
      <h3>暂无打开的文件</h3>
      <p>从左侧文件树选择一个文件开始编辑</p>
    </div>

    <!-- 编辑器 -->
    <div v-show="fileStore.currentFile" ref="codemirrorEl" class="codemirror-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { markdown } from '@codemirror/lang-markdown'
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'

const fileStore = useFileStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()

const codemirrorEl = ref<HTMLElement | null>(null)
let editorView: EditorView | null = null
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

// 主题样式
const moyunTheme = EditorView.theme({
  '&': {
    height: '100%',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    fontSize: '15px',
  },
  '.cm-content': {
    fontFamily: "'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    lineHeight: '1.8',
    padding: '20px',
    caretColor: 'var(--accent-primary)',
  },
  '.cm-cursor': {
    borderLeftColor: 'var(--accent-primary)',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-muted)',
    borderRight: '1px solid var(--border-color)',
  },
  '.cm-lineNumbers .cm-gutterElement': {
    padding: '0 12px 0 8px',
  },
  '.cm-selectionBackground': {
    backgroundColor: 'rgba(59, 130, 246, 0.3) !important',
  },
  '&.cm-focused .cm-selectionBackground': {
    backgroundColor: 'rgba(59, 130, 246, 0.3) !important',
  },
  '.cm-scroller': {
    overflow: 'auto',
  },
})

function createEditor(content: string) {
  if (!codemirrorEl.value) return

  // 销毁旧实例
  if (editorView) {
    editorView.destroy()
  }

  const updateListener = EditorView.updateListener.of((update) => {
    if (update.docChanged) {
      const newContent = update.state.doc.toString()
      handleContentChange(newContent)
    }
    if (update.selectionSet) {
      const pos = update.state.selection.main.head
      const line = update.state.doc.lineAt(pos)
      editorStore.cursorPosition = {
        line: line.number,
        col: pos - line.from + 1,
      }
    }
  })

  const state = EditorState.create({
    doc: content,
    extensions: [
      lineNumbers(),
      highlightActiveLine(),
      drawSelection(),
      history(),
      markdown(),
      syntaxHighlighting(defaultHighlightStyle),
      moyunTheme,
      keymap.of([...defaultKeymap, ...historyKeymap]),
      updateListener,
      EditorView.lineWrapping,
    ],
  })

  editorView = new EditorView({
    state,
    parent: codemirrorEl.value,
  })
}

function handleContentChange(content: string) {
  if (!fileStore.currentFile) return

  // 更新 store
  editorStore.updateContent(fileStore.currentFile.path, content)

  // 标记脏
  fileStore.markDirty(fileStore.currentFile.path)

  // 防抖自动保存（3秒后）
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
  autoSaveTimer = setTimeout(async () => {
    await saveCurrentFile()
  }, 3000)
}

async function saveCurrentFile() {
  if (!projectStore.currentProject || !fileStore.currentFile) return

  const path = fileStore.currentFile.path
  if (!fileStore.unsavedFiles.has(path)) return

  const content = editorStore.getContent(path)
  try {
    await fileStore.saveFile(projectStore.currentProject.id, path, content)
  } catch (e) {
    notification.error('自动保存失败')
  }
}

// 监听当前文件切换
watch(
  () => fileStore.currentFile,
  async (file) => {
    await nextTick()
    if (file) {
      const content = editorStore.getContent(file.path) || ''
      if (!editorView || editorView.state.doc.toString() !== content) {
        createEditor(content)
      }
    }
  }
)

// 监听格式化事件
function handleFormatEvent(e: Event) {
  const customEvent = e as CustomEvent<{ before: string; after: string }>
  if (!editorView) return

  const { before, after } = customEvent.detail
  const { from, to } = editorView.state.selection.main
  const selectedText = editorView.state.doc.sliceString(from, to)

  editorView.dispatch({
    changes: {
      from,
      to,
      insert: before + selectedText + after,
    },
  })
  editorView.focus()
}

// 监听插入事件
function handleInsertEvent(e: Event) {
  const customEvent = e as CustomEvent<string>
  if (!editorView) return

  const { from, to } = editorView.state.selection.main
  editorView.dispatch({
    changes: { from, to, insert: customEvent.detail },
  })
  editorView.focus()
}

// 监听 AI 生成事件
function handleAIGenerateEvent() {
  // 通知 ChatPanel 开始生成
  window.dispatchEvent(new CustomEvent('chat:request-generate'))
}

onMounted(() => {
  window.addEventListener('editor:format', handleFormatEvent)
  window.addEventListener('editor:insert', handleInsertEvent)
  window.addEventListener('editor:ai-generate', handleAIGenerateEvent)

  // 初始创建
  if (fileStore.currentFile) {
    const content = editorStore.getContent(fileStore.currentFile.path) || ''
    createEditor(content)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('editor:format', handleFormatEvent)
  window.removeEventListener('editor:insert', handleInsertEvent)
  window.removeEventListener('editor:ai-generate', handleAIGenerateEvent)

  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }

  if (editorView) {
    editorView.destroy()
  }
})
</script>

<style scoped lang="scss">
.markdown-editor {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.editor-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);

  i {
    font-size: 64px;
    opacity: 0.3;
  }

  h3 {
    font-size: 18px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  p {
    font-size: 14px;
  }
}

.codemirror-container {
  flex: 1;
  overflow: hidden;

  :deep(.cm-editor) {
    height: 100%;
  }

  :deep(.cm-scroller) {
    overflow: auto;
  }
}
</style>
