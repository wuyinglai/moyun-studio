<template>
  <a-modal
    :open="visible"
    title="快速打开文件"
    :width="600"
    :footer="null"
    @cancel="close"
    class="quick-open-modal"
  >
    <div class="quick-open-container">
      <a-input-search
        v-model:value="query"
        placeholder="输入文件名..."
        size="large"
        autofocus
        @search="filterFiles"
        @input="filterFiles"
      />
      <div class="file-list">
        <div
          v-for="file in filteredFiles"
          :key="file.path"
          class="file-item"
          :class="{ active: selectedIndex === filteredFiles.indexOf(file) }"
          @click="openFile(file)"
          @mouseenter="selectedIndex = filteredFiles.indexOf(file)"
        >
          <i class="fa-solid fa-file-lines"></i>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-path">{{ file.path }}</span>
        </div>
        <div v-if="filteredFiles.length === 0 && query" class="no-results">
          未找到匹配文件
        </div>
      </div>
      <div class="quick-hint">
        <kbd>↑</kbd><kbd>↓</kbd> 选择 · <kbd>Enter</kbd> 打开 · <kbd>Esc</kbd> 关闭
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { Modal as AModal, InputSearch as AInputSearch } from 'ant-design-vue'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'

const uiStore = useUIStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()

const visible = computed(() => uiStore.modals.quickOpen)
const query = ref('')
const selectedIndex = ref(0)

interface FileItem {
  name: string
  path: string
  type: 'file' | 'directory'
}

const allFiles = ref<FileItem[]>([])

const filteredFiles = computed(() => {
  if (!query.value.trim()) return allFiles.value.slice(0, 20)
  const q = query.value.toLowerCase()
  return allFiles.value.filter(f => f.name.toLowerCase().includes(q)).slice(0, 20)
})

watch(filteredFiles, () => { selectedIndex.value = 0 })

async function loadFiles() {
  if (!projectStore.currentProject) return
  try {
    await fileStore.loadTree(projectStore.currentProject.id)
    allFiles.value = _flattenTree(fileStore.tree || [], '')
  } catch {
    allFiles.value = []
  }
}

function _flattenTree(nodes: any[], prefix: string): FileItem[] {
  const result: FileItem[] = []
  for (const node of nodes) {
    const path = prefix ? `${prefix}/${node.name}` : node.name
    if (node.type === 'file') {
      result.push({ name: node.name, path, type: 'file' })
    } else if (node.children) {
      result.push(..._flattenTree(node.children, path))
    }
  }
  return result
}

function close() {
  uiStore.closeQuickOpen()
  query.value = ''
  selectedIndex.value = 0
}

function openFile(file: FileItem) {
  const node = { name: file.name, path: file.path, type: 'file' as const }
  fileStore.openFile(node)
  editorStore.setCurrentFile(file.path)
  close()
}

function filterFiles() {
  // Input handler for real-time filtering
}

function handleKeydown(e: KeyboardEvent) {
  if (!visible.value) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, filteredFiles.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const file = filteredFiles.value[selectedIndex.value]
    if (file) openFile(file)
  } else if (e.key === 'Escape') {
    close()
  }
}

watch(visible, (val) => {
  if (val) loadFiles()
})

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped lang="scss">
.quick-open-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-list {
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.1s;

  &.active,
  &:hover {
    background: var(--bg-hover);
  }

  i {
    color: var(--accent-primary);
    flex-shrink: 0;
  }

  .file-name {
    flex: 1;
    font-size: 14px;
    color: var(--text-primary);
  }

  .file-path {
    font-size: 12px;
    color: var(--text-muted);
    flex-shrink: 0;
  }
}

.no-results {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
}

.quick-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);

  kbd {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 11px;
    font-family: monospace;
  }
}
</style>
