<template>
  <div class="markdown-editor" ref="editorContainer">
    <div v-if="!fileStore.currentFile" class="editor-welcome">
      <div class="welcome-card">
        <div class="welcome-icon">
          <i class="fa-solid fa-feather-pointed"></i>
        </div>
        <h1 class="welcome-title">欢迎使用墨韵</h1>
        <p class="welcome-desc">AI 辅助小说创作工具，从零开始创作你的第一部小说</p>
        <div class="welcome-actions">
          <a-button type="primary" size="large" @click="uiStore.openCreateProject()">
            <template #icon><i class="fa-solid fa-plus"></i></template>
            开始创作
          </a-button>
          <a-button size="large" @click="uiStore.openOpenProject()">
            <template #icon><i class="fa-solid fa-folder-open"></i></template>
            打开项目
          </a-button>
        </div>
        <div class="welcome-features">
          <div class="feature-item">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            <span>AI 自动生成</span>
          </div>
          <div class="feature-item">
            <i class="fa-solid fa-pen-nib"></i>
            <span>全流程写作</span>
          </div>
          <div class="feature-item">
            <i class="fa-solid fa-sliders"></i>
            <span>灵活控制</span>
          </div>
        </div>
      </div>
    </div>

    <div v-show="fileStore.currentFile && !isPreviewMode" ref="codemirrorEl" class="codemirror-container"></div>
    <div v-show="fileStore.currentFile && isPreviewMode" class="preview-container" v-html="previewHtml"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, undo, redo } from '@codemirror/commands'
import { markdown } from '@codemirror/lang-markdown'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useUIStore } from '@/stores/ui'
import { useAutoSave } from '@/composables/useAutoSave'
import { useMarkdownPreview } from '@/composables/useMarkdownPreview'
import { semanticHighlight } from '@/utils/semanticHighlight'

const fileStore = useFileStore()
const editorStore = useEditorStore()
const uiStore = useUIStore()
const { triggerAutoSave, cleanup: cleanupAutoSave } = useAutoSave()
const { isPreviewMode, previewHtml, updatePreview } = useMarkdownPreview()

const codemirrorEl = ref<HTMLElement | null>(null)
let editorView: EditorView | null = null

const moyunTheme = EditorView.theme({
  '&': {
    height: '100%',
    background: 'var(--ink-deep)',
    color: 'var(--text-ink)',
    fontSize: '15px',
  },
  '.cm-content': {
    fontFamily: "'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    lineHeight: '1.85',
    padding: '24px 32px',
    caretColor: 'var(--gold-primary)',
  },
  '.cm-cursor': {
    borderLeftColor: 'var(--gold-primary)',
    borderLeftWidth: '2px',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(201, 169, 110, 0.04)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'rgba(201, 169, 110, 0.04)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--ink-dark)',
    color: 'var(--text-faint)',
    borderRight: '1px solid var(--border-ink)',
  },
  '.cm-lineNumbers .cm-gutterElement': {
    padding: '0 14px 0 10px',
    fontSize: '13px',
  },
  '.cm-selectionBackground': {
    backgroundColor: 'rgba(201, 169, 110, 0.2) !important',
  },
  '&.cm-focused .cm-selectionBackground': {
    backgroundColor: 'rgba(201, 169, 110, 0.2) !important',
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
      moyunTheme,
      keymap.of([...defaultKeymap, ...historyKeymap] as unknown as import('@codemirror/view').KeyBinding[]),
      semanticHighlight(),
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
  editorStore.markLocalEdit()

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

watch(
  () => fileStore.currentFile ? editorStore.contents[fileStore.currentFile.path] : undefined,
  (content) => {
    if (content === undefined || !editorView) return
    if (editorStore.contentSource !== 'external') return
    const current = editorView.state.doc.toString()
    if (current !== content) {
      const scroller = editorView.scrollDOM
      const prevScrollTop = scroller.scrollTop

      editorView.dispatch({
        changes: { from: 0, to: current.length, insert: content },
      })
      editorStore.markLocalEdit()

      // AI 生成时保持滚动位置不变，防止编辑框跳动
      requestAnimationFrame(() => {
        scroller.scrollTop = prevScrollTop
      })
    }
  }
)

watch(
  () => fileStore.currentFile ? editorStore.getContent(fileStore.currentFile.path) : undefined,
  () => {
    if (isPreviewMode.value) {
      updatePreview()
    }
  }
)

onMounted(() => {
  window.addEventListener('editor:undo', handleUndo)
  window.addEventListener('editor:redo', handleRedo)
  window.addEventListener('editor:jump-to-line', handleJumpToLine)
  if (fileStore.currentFile) {
    const content = editorStore.getContent(fileStore.currentFile.path) || ''
    createEditor(content)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('editor:undo', handleUndo)
  window.removeEventListener('editor:redo', handleRedo)
  window.removeEventListener('editor:jump-to-line', handleJumpToLine)
  cleanupAutoSave()

  if (editorView) {
    editorView.destroy()
  }
})

function handleUndo() {
  if (editorView) undo(editorView)
}

function handleRedo() {
  if (editorView) redo(editorView)
}

function handleJumpToLine(e: Event) {
  const detail = (e as CustomEvent).detail
  const line = detail?.line
  if (!editorView || !line) return
  try {
    const lineInfo = editorView.state.doc.line(Math.min(line, editorView.state.doc.lines))
    editorView.dispatch({
      selection: { anchor: lineInfo.from },
      scrollIntoView: true,
    })
    editorView.focus()
  } catch {}
}
</script>

<style scoped lang="scss">
.markdown-editor {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ink-deep);
  overflow: hidden;
}

.editor-welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
}

.welcome-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 480px;
  text-align: center;
  animation: fade-in-up 0.5s ease;
}

.welcome-icon {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--gold-primary);
  background: linear-gradient(135deg, rgba(201, 169, 110, 0.12), rgba(201, 169, 110, 0.03));
  border: 1px solid rgba(201, 169, 110, 0.1);
  border-radius: 20px;
  margin-bottom: 8px;
}

.welcome-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-warm-white);
  margin: 0;
  font-family: var(--font-display);
  letter-spacing: 2px;
}

.welcome-desc {
  font-size: 14px;
  color: var(--text-muted-ink);
  margin: 0 0 16px 0;
  line-height: 1.6;
}

.welcome-actions {
  display: flex;
  gap: 12px;
}

.welcome-actions:deep(.ant-btn) {
  height: 40px;
  padding: 0 24px;
  border-radius: var(--radius-md);
  font-size: 14px;
}

.welcome-features {
  display: flex;
  gap: 32px;
  margin-top: 20px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-faint);
}

.feature-item i {
  font-size: 20px;
  color: var(--gold-primary);
  opacity: 0.5;
}

.codemirror-container {
  flex: 1;
  overflow: hidden;
}

.codemirror-container:deep(.cm-editor) { height: 100%; }
.codemirror-container:deep(.cm-scroller) { overflow: auto; }

.codemirror-container:deep(.cm-semantic-dialogue) { color: var(--jade-light) !important; }
.codemirror-container:deep(.cm-semantic-character) { color: var(--gold-primary) !important; }
.codemirror-container:deep(.cm-semantic-scene) { color: #c084fc !important; }

.preview-container {
  flex: 1;
  overflow: auto;
  padding: 32px 40px;
  background: var(--ink-deep);
  color: var(--text-ink);
  font-family: var(--font-body);
  line-height: 1.85;
  font-size: 15px;
}

.preview-container:deep(h1) {
  font-family: var(--font-display);
  font-size: 1.8em;
  font-weight: 700;
  margin: 0.8em 0;
  border-bottom: 1px solid var(--border-ink);
  padding-bottom: 0.3em;
  color: var(--text-warm-white);
  letter-spacing: 1px;
}

.preview-container:deep(h2) {
  font-size: 1.4em;
  font-weight: 600;
  margin: 0.8em 0;
  color: var(--text-warm-white);
}

.preview-container:deep(h3) {
  font-size: 1.2em;
  font-weight: 600;
  margin: 0.6em 0;
  color: var(--text-warm-white);
}

.preview-container:deep(p) { margin: 0.8em 0; }

.preview-container:deep(blockquote) {
  border-left: 2px solid var(--gold-primary);
  padding-left: 1em;
  margin: 1em 0;
  color: var(--text-muted-ink);
  font-style: italic;
}

.preview-container:deep(code) {
  background: var(--ink-mid);
  padding: 0.2em 0.4em;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  color: var(--gold-primary);
}

.preview-container:deep(pre) {
  background: var(--ink-dark);
  padding: 1em;
  border-radius: var(--radius-md);
  overflow-x: auto;
  border: 1px solid var(--border-ink);
}

.preview-container:deep(pre) code {
  background: none;
  padding: 0;
  color: var(--text-ink);
}

.preview-container:deep(a) {
  color: var(--gold-primary);
}
</style>
