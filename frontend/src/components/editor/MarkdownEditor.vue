<template>
  <div class="markdown-editor" ref="editorContainer">
    <div v-if="!fileStore.currentFile" class="editor-empty">
      <i class="fa-solid fa-file-lines"></i>
      <h3>暂无打开的文件</h3>
      <p>从左侧文件树选择一个文件开始编辑</p>
    </div>

    <div v-show="fileStore.currentFile" ref="codemirrorEl" class="codemirror-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, undo, redo } from '@codemirror/commands'
import { markdown } from '@codemirror/lang-markdown'
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useAutoSave } from '@/composables/useAutoSave'

const fileStore = useFileStore()
const editorStore = useEditorStore()
const { triggerAutoSave, cleanup: cleanupAutoSave } = useAutoSave()

const codemirrorEl = ref<HTMLElement | null>(null)
let editorView: EditorView | null = null

const moyunTheme = EditorView.theme({
  '&': {
    height: '100%',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    fontSize: '15px',
  },
  '.cm-content': {
    fontFamily: "'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    lineHeight: '1.85',
    padding: '24px 32px',
    caretColor: 'var(--accent-primary)',
  },
  '.cm-cursor': {
    borderLeftColor: 'var(--accent-primary)',
    borderLeftWidth: '2px',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(107, 140, 255, 0.08)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'rgba(107, 140, 255, 0.08)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-muted)',
    borderRight: '1px solid var(--border-color)',
  },
  '.cm-lineNumbers .cm-gutterElement': {
    padding: '0 14px 0 10px',
    fontSize: '13px',
  },
  '.cm-selectionBackground': {
    backgroundColor: 'rgba(107, 140, 255, 0.25) !important',
  },
  '&.cm-focused .cm-selectionBackground': {
    backgroundColor: 'rgba(107, 140, 255, 0.25) !important',
  },
  '.cm-scroller': {
    overflow: 'auto',
  },
})

function createEditor(content: string) {
  if (!codemirrorEl.value) return

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
      keymap.of([...defaultKeymap, ...historyKeymap] as unknown as import('@codemirror/view').KeyBinding[]),
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

  editorStore.updateContent(fileStore.currentFile.path, content)
  fileStore.markDirty(fileStore.currentFile.path)

  triggerAutoSave(fileStore.currentFile.path)
}

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

onMounted(() => {
  window.addEventListener('editor:undo', handleUndo)
  window.addEventListener('editor:redo', handleRedo)
  if (fileStore.currentFile) {
    const content = editorStore.getContent(fileStore.currentFile.path) || ''
    createEditor(content)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('editor:undo', handleUndo)
  window.removeEventListener('editor:redo', handleRedo)
  cleanupAutoSave()

  if (editorView) {
    editorView.destroy()
  }
})

// 监听外部 undo/redo 请求（来自 EditorToolbar）
function handleUndo() {
  if (editorView) undo(editorView)
}

function handleRedo() {
  if (editorView) redo(editorView)
}
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
  gap: 20px;
  color: var(--text-muted);
  padding: 40px;

  i {
    font-size: 72px;
    opacity: 0.3;
    color: var(--accent-primary);
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-secondary);
    margin: 0;
  }

  p {
    font-size: 14px;
    margin: 0;
    opacity: 0.8;
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
