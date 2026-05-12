<template>
  <div class="prompt-panel">
    <!-- 编辑工具栏 -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">发送给LLM的Prompt</span>
      </div>
      <div class="toolbar-row">
        <a-button-group>
          <a-button size="small" @click="goBack" :disabled="!canGoBack">
            <template #icon><i class="fa-solid fa-chevron-left"></i></template>
            后退
          </a-button>
          <a-button size="small" @click="goForward" :disabled="!canGoForward">
            <template #icon><i class="fa-solid fa-chevron-right"></i></template>
            前进
          </a-button>
        </a-button-group>
        <a-select
          v-model:value="selectedTemplate"
          placeholder="加载模板..."
          size="small"
          style="min-width: 120px;"
          :loading="isLoadingTemplate"
          @change="loadTemplate"
        >
          <a-select-option v-for="t in templateList" :key="t.name" :value="t.name">
            {{ t.name }}
          </a-select-option>
        </a-select>
        <a-button type="primary" size="small" @click="sendToAI">
          <template #icon><i class="fa-solid fa-paper-plane"></i></template>
          发送
        </a-button>
      </div>
      <a-textarea
        v-model:value="localPrompt"
        placeholder="在此输入您的 Prompt..."
        :auto-size="{ minRows: 10, maxRows: 20 }"
        @input="handleInput"
        class="prompt-editor"
      />
      <div class="save-status" :class="{ saving: isSaving }">
        {{ isSaving ? '保存中...' : '已保存' }}
      </div>
      <!-- M0402-3 引用文件链接 -->
      <div v-if="fileReferences.length > 0" class="file-references">
        <span class="ref-title">引用文件：</span>
        <a
          v-for="ref in fileReferences"
          :key="ref.path"
          class="ref-link"
          @click="openReferencedFile(ref.path)"
        >
          <i class="fa-solid fa-file-lines"></i>
          {{ ref.name }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Button as AButton, ButtonGroup as AButtonGroup } from 'ant-design-vue'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import api from '@/services/api'

const rightPanelStore = useRightPanelStore()
const notification = useNotificationStore()
const chatStore = useChatStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()

const localPrompt = ref('')
const isSaving = ref(false)
let saveTimeout: ReturnType<typeof setTimeout> | null = null

// G0106: Prompt 模板加载
interface PromptTemplate {
  name: string
  category: string
  exists: boolean
}
const templateList = ref<PromptTemplate[]>([])
const selectedTemplate = ref<string | null>(null)
const isLoadingTemplate = ref(false)

onMounted(async () => {
  try {
    const data = await api.get<{ prompts: PromptTemplate[]; total: number }>('/prompts')
    templateList.value = data?.prompts || []
  } catch {
    // 静默失败，模板加载是可选的
  }
})

async function loadTemplate(fullName: string) {
  if (!fullName) return
  isLoadingTemplate.value = true
  selectedTemplate.value = fullName
  try {
    const [category, ...nameParts] = fullName.split('/')
    const name = nameParts.join('/')
    const data = await api.get<{ name: string; category: string; content: string }>(`/prompts/${category}/${name}`)
    if (data?.content) {
      localPrompt.value = data.content
      rightPanelStore.loadPromptTemplate(data.content)
      notification.success(`已加载模板: ${fullName}`)
    }
  } catch {
    notification.error('加载模板失败')
  } finally {
    isLoadingTemplate.value = false
  }
}

// M0402-3 — 解析 @{文件路径} 引用
const fileReferences = computed(() => {
  const refs: { path: string; name: string }[] = []
  const regex = /@\{([^}]+)\}/g
  let match
  while ((match = regex.exec(localPrompt.value)) !== null) {
    const path = match[1].trim()
    if (path && !refs.find(r => r.path === path)) {
      refs.push({ path, name: path.split('/').pop() || path })
    }
  }
  return refs
})

function openReferencedFile(path: string) {
  if (!projectStore.currentProject) return
  fileStore.openFile({ name: path.split('/').pop() || '', path, type: 'file' })
  editorStore.setCurrentFile(path)
  fileStore.readFile(projectStore.currentProject.id, path).then(data => {
    editorStore.loadContent(path, data.content || '')
  })
}

const currentHistoryIndex = computed(() => rightPanelStore.currentHistoryIndex)
const canGoBack = computed(() => currentHistoryIndex.value < rightPanelStore.promptHistory.length - 1)
const canGoForward = computed(() => currentHistoryIndex.value >= 0)

watch(
  () => rightPanelStore.promptContent,
  (newVal) => {
    localPrompt.value = newVal
  },
  { immediate: true }
)

function handleInput() {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }
  isSaving.value = true
  saveTimeout = setTimeout(() => {
    savePrompt()
  }, 500)
}

function savePrompt() {
  rightPanelStore.updatePrompt(localPrompt.value)
  isSaving.value = false
}

function goBack() {
  rightPanelStore.goPromptHistoryBack()
  localPrompt.value = rightPanelStore.promptContent
}

function goForward() {
  rightPanelStore.goPromptHistoryForward()
  localPrompt.value = rightPanelStore.promptContent
}

async function sendToAI() {
  if (!localPrompt.value) {
    notification.warning('暂无 Prompt 内容')
    return
  }
  try {
    await chatStore.sendMessage(localPrompt.value)
  } catch (e) {
    notification.error('发送失败')
  }
}
</script>

<style scoped lang="scss">
.prompt-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-section {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}

.prompt-editor {
  width: 100%;
  flex: 1;
}

.save-status {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;

  &.saving {
    color: var(--accent-warning);
  }
}

.prompt-panel :deep(.ant-btn) {
  color: var(--text-primary);
  background: transparent;
  border: 1px solid var(--border-color);
  
  &:hover:not(:disabled) {
    color: var(--accent-primary);
    border-color: var(--accent-primary);
    background: var(--bg-hover);
  }
  
  &:disabled {
    color: var(--text-muted);
    opacity: 0.5;
  }
}

.file-references {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
}

.ref-title {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.ref-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--accent-primary);
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;

  &:hover {
    background: var(--accent-primary);
    color: white;
    border-color: var(--accent-primary);
  }
}
</style>
