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
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useUIStore } from '@/stores/ui'
import { useAutoSave } from '@/composables/useAutoSave'
import { useMarkdownPreview } from '@/composables/useMarkdownPreview'

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
  // 标记本地编辑，防止外部更新覆盖
  editorStore.markLocalEdit()

  triggerAutoSave(fileStore.currentFile.path)
}

// 监听文件切换：打开文件时创建编辑器
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

// 监听外部内容变更（流式生成等），更新编辑器
// 只有 contentSource === 'external' 时才更新，防止覆盖用户正在编辑的内容
watch(
  () => fileStore.currentFile ? editorStore.contents[fileStore.currentFile.path] : undefined,
  (content) => {
    if (content === undefined || !editorView) return
    // 只有外部更新才触发编辑器更新
    if (editorStore.contentSource !== 'external') return
    const current = editorView.state.doc.toString()
    if (current !== content) {
      editorView.dispatch({
        changes: { from: 0, to: current.length, insert: content },
      })
      // 更新完成后标记为本地来源
      editorStore.markLocalEdit()
    }
  }
)

// 预览模式下，内容变化时更新预览
watch(
  () => editorStore.currentFile ? editorStore.getContent(editorStore.currentFile.path) : undefined,
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

// 监听外部 undo/redo 请求（来自 EditorToolbar）
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
  background: var(--bg-primary);
  overflow: hidden;
}

.editor-welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.welcome-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 480px;
  text-align: center;
}

.welcome-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(107, 140, 255, 0.15), rgba(168, 85, 247, 0.15));
  border-radius: 24px;
  margin-bottom: 8px;
  font-size: 36px;
  color: var(--accent-primary);
}

.welcome-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.welcome-desc {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0 0 16px 0;
  line-height: 1.6;
}

.welcome-actions {
  display: flex;
  gap: 12px;
}

.welcome-features {
  display: flex;
  gap: 32px;
  margin-top: 24px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);

  i {
    font-size: 20px;
    color: var(--accent-primary);
    opacity: 0.7;
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

.preview-container {
  flex: 1;
  overflow: auto;
  padding: 24px 32px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  line-height: 1.85;
  font-size: 15px;

  :deep(h1) {
    font-size: 1.8em;
    font-weight: 700;
    margin: 0.8em 0;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.3em;
  }

  :deep(h2) {
    font-size: 1.5em;
    font-weight: 600;
    margin: 0.8em 0;
  }

  :deep(h3) {
    font-size: 1.25em;
    font-weight: 600;
    margin: 0.6em 0;
  }

  :deep(p) {
    margin: 0.8em 0;
  }

  :deep(blockquote) {
    border-left: 4px solid var(--accent-primary);
    padding-left: 1em;
    margin: 1em 0;
    color: var(--text-secondary);
  }

  :deep(code) {
    background: var(--bg-secondary);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Fira Code', monospace;
  }

  :deep(pre) {
    background: var(--bg-secondary);
    padding: 1em;
    border-radius: 6px;
    overflow-x: auto;

    :deep(code) {
      background: none;
      padding: 0;
    }
  }
}
</style>
