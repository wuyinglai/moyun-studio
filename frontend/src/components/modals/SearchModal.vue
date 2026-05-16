<template>
  <a-modal
    :open="visible"
    title="全文搜索"
    :width="700"
    :footer="null"
    @cancel="close"
    class="search-modal"
  >
    <div class="search-container">
      <a-input-search
        v-model:value="query"
        placeholder="输入搜索内容..."
        size="large"
        autofocus
        @search="doSearch"
        @pressEnter="doSearch"
      />
      <div class="search-options">
        <a-checkbox v-model:checked="caseSensitive">区分大小写</a-checkbox>
        <a-checkbox v-model:checked="regexMode">正则表达式</a-checkbox>
      </div>
      <div v-if="isSearching" class="search-loading">
        <a-spin /> 搜索中...
      </div>
      <div v-else-if="results.length > 0" class="search-results">
        <div class="results-count">找到 {{ results.length }} 个匹配</div>
        <div
          v-for="(result, idx) in results"
          :key="idx"
          class="result-item"
          @click="jumpToResult(result)"
        >
          <div class="result-file">
            <i class="fa-solid fa-file-lines"></i>
            {{ result.file }}
          </div>
          <div class="result-line">
            <span class="line-num">第 {{ result.line }} 行</span>
            <span class="line-content" v-html="highlight(result.content)"></span>
          </div>
        </div>
      </div>
      <div v-else-if="searched && query" class="search-empty">
        未找到匹配结果
      </div>
      <div v-else class="search-hint">
        输入内容后按 Enter 或点击搜索
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Modal as AModal, InputSearch as AInputSearch, Checkbox as ACheckbox, Spin as ASpin } from 'ant-design-vue'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useEditorStore } from '@/stores/editor'
import { useFileStore } from '@/stores/file'
import api from '@/services/api'

const uiStore = useUIStore()
const projectStore = useProjectStore()
const editorStore = useEditorStore()
const fileStore = useFileStore()

const visible = computed(() => uiStore.modals.search)
const query = ref('')
const caseSensitive = ref(false)
const regexMode = ref(false)
const isSearching = ref(false)
const searched = ref(false)

interface SearchResult {
  file: string
  line: number
  content: string
}
const results = ref<SearchResult[]>([])

function close() {
  uiStore.closeSearch()
  query.value = ''
  results.value = []
  searched.value = false
}

async function doSearch() {
  if (!query.value.trim()) return
  if (!projectStore.currentProject) return

  isSearching.value = true
  searched.value = false
  results.value = []

  try {
    const res = await api.post<SearchResult[]>('/files/search', {
      query: query.value,
      project_id: projectStore.currentProject.id,
      case_sensitive: caseSensitive.value,
      regex: regexMode.value,
    })
    results.value = res || []
  } catch {
    results.value = []
  } finally {
    isSearching.value = false
    searched.value = true
  }
}

function highlight(content: string): string {
  // 简单的高亮：将匹配文字包裹在 <mark> 中
  if (!query.value) return content
  const escaped = query.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const flag = caseSensitive.value ? 'g' : 'gi'
  try {
    const re = new RegExp(escaped, flag)
    return content.replace(re, '<mark>$&</mark>')
  } catch {
    return content
  }
}

async function jumpToResult(result: SearchResult) {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const node = { name: result.file.split('/').pop() || '', path: result.file, type: 'file' as const }
  const fileData = await fileStore.readFile(projectId, result.file)
  fileStore.openFile(node)
  editorStore.loadContent(result.file, fileData.content || '')
  editorStore.setCurrentFile(result.file)
  // 通知编辑器滚动到对应行
  window.dispatchEvent(new CustomEvent('editor:jump-to-line', { detail: { line: result.line } }))
  close()
}
</script>

<style scoped lang="scss">
.search-modal :deep(.ant-modal-body) {
  padding: 16px;
}

.search-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-options {
  display: flex;
  gap: 16px;
}

.search-loading,
.search-empty,
.search-hint {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
}

.search-results {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.results-count {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}

.result-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: var(--bg-hover);
  }
}

.result-file {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;

  i {
    margin-right: 6px;
    color: var(--accent-primary);
  }
}

.result-line {
  display: flex;
  gap: 8px;
  font-size: 13px;
  font-family: 'Fira Code', monospace;
}

.line-num {
  color: var(--text-muted);
  flex-shrink: 0;
}

.line-content {
  color: var(--text-primary);
  word-break: break-all;

  :deep(mark) {
    background: rgba(255, 200, 0, 0.4);
    border-radius: 2px;
    padding: 0 2px;
  }
}
</style>
