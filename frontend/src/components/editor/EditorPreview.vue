<template>
  <div class="editor-preview" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
}>()

const renderedHtml = computed(() => renderMarkdown(props.content))
</script>

<style scoped>
.editor-preview {
  height: 100%;
  overflow-y: auto;
  padding: 20px 24px;
  font-family: var(--font-family-ch);
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
}

.editor-preview :deep(h1),
.editor-preview :deep(h2),
.editor-preview :deep(h3),
.editor-preview :deep(h4) {
  color: var(--text-primary);
  margin: 1.5em 0 0.5em;
  font-weight: 600;
  line-height: 1.3;
}

.editor-preview :deep(h1) { font-size: 1.8em; }
.editor-preview :deep(h2) { font-size: 1.5em; }
.editor-preview :deep(h3) { font-size: 1.25em; }

.editor-preview :deep(p) {
  margin: 0.8em 0;
}

.editor-preview :deep(ul),
.editor-preview :deep(ol) {
  padding-left: 1.5em;
  margin: 0.8em 0;
}

.editor-preview :deep(blockquote) {
  border-left: 3px solid var(--accent-primary);
  padding-left: 1em;
  margin: 1em 0;
  color: var(--text-secondary);
}

.editor-preview :deep(code) {
  font-family: var(--font-family-mono);
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

.editor-preview :deep(pre) {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin: 1em 0;
}

.editor-preview :deep(pre code) {
  background: none;
  padding: 0;
}

.editor-preview :deep(a) {
  color: var(--accent-primary);
}

.editor-preview :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 2em 0;
}
</style>
