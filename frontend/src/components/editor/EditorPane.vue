<template>
  <div ref="containerRef" class="editor-pane"></div>
</template>

<script setup lang="ts">
/**
 * EditorPane.vue - CodeMirror 6 编辑区
 * 由 MarkdownEditor.vue 使用，不单独渲染
 */
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { EditorState } from '@codemirror/state'
import {
  EditorView,
  keymap,
  lineNumbers,
  highlightActiveLine,
  drawSelection,
} from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { markdown } from '@codemirror/lang-markdown'
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'

const props = defineProps<{
  content: string
  theme?: 'dark' | 'light'
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'change', content: string): void
  (e: 'cursor', pos: { line: number; col: number }): void
}>()

const containerRef = ref<HTMLElement | null>(null)
let editorView: EditorView | null = null

// CodeMirror 主题
const moyunTheme = EditorView.theme({
  '&': {
    height: '100%',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    fontSize: '15px',
  },
  '.cm-content': {
    fontFamily: "'Source Han Sans SC', 'PingFang SC', sans-serif",
    lineHeight: '1.8',
    padding: '20px',
    caretColor: 'var(--accent-primary)',
  },
  '.cm-cursor': { borderLeftColor: 'var(--accent-primary)' },
  '.cm-activeLine': { backgroundColor: 'rgba(59,130,246,0.08)' },
  '.cm-gutters': {
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-muted)',
    borderRight: '1px solid var(--border-color)',
  },
  '.cm-selectionBackground': { backgroundColor: 'rgba(59,130,246,0.25) !important' },
  '&.cm-focused .cm-selectionBackground': { backgroundColor: 'rgba(59,130,246,0.25) !important' },
  '.cm-scroller': { overflow: 'auto' },
})

function createEditor(content: string) {
  if (!containerRef.value) return

  if (editorView) {
    editorView.destroy()
    editorView = null
  }

  const extensions = [
    lineNumbers(),
    highlightActiveLine(),
    drawSelection(),
    history(),
    markdown(),
    syntaxHighlighting(defaultHighlightStyle),
    moyunTheme,
    keymap.of([...defaultKeymap, ...historyKeymap]),
    EditorView.lineWrapping,
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        emit('change', update.state.doc.toString())
      }
      if (update.selectionSet) {
        const pos = update.state.selection.main.head
        const line = update.state.doc.lineAt(pos)
        emit('cursor', { line: line.number, col: pos - line.from + 1 })
      }
    }),
  ]

  if (props.readonly) {
    extensions.push(EditorState.readOnly.of(true))
  }

  const state = EditorState.create({ doc: content, extensions })
  editorView = new EditorView({ state, parent: containerRef.value })
}

function getValue(): string {
  return editorView?.state.doc.toString() || ''
}

function setValue(content: string) {
  if (!editorView) return
  editorView.dispatch({
    changes: {
      from: 0,
      to: editorView.state.doc.length,
      insert: content,
    },
  })
}

function insertText(text: string, at?: number) {
  if (!editorView) return
  const pos = at ?? editorView.state.doc.length
  editorView.dispatch({ changes: { from: pos, insert: text } })
}

function focus() {
  editorView?.focus()
}

defineExpose({ getValue, setValue, insertText, focus })

watch(
  () => props.content,
  (newContent) => {
    if (editorView && editorView.state.doc.toString() !== newContent) {
      setValue(newContent)
    }
  }
)

onMounted(() => {
  createEditor(props.content)
})

onBeforeUnmount(() => {
  editorView?.destroy()
  editorView = null
})
</script>

<style scoped>
.editor-pane {
  height: 100%;
  width: 100%;
}

.editor-pane :deep(.cm-editor) {
  height: 100%;
}
</style>
