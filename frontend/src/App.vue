<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import NotificationContainer from '@/components/layout/NotificationContainer.vue'
import CreateProjectModal from '@/components/modals/CreateProjectModal.vue'
import OpenProjectModal from '@/components/modals/OpenProjectModal.vue'
import SettingsModal from '@/components/modals/SettingsModal.vue'
import TokenCountModal from '@/components/modals/TokenCountModal.vue'
import CompareModal from '@/components/modals/CompareModal.vue'
import FeedbackModal from '@/components/modals/FeedbackModal.vue'
import RevisionLogModal from '@/components/modals/RevisionLogModal.vue'
import BatchGenerateModal from '@/components/modals/BatchGenerateModal.vue'
import ExtractModal from '@/components/modals/ExtractModal.vue'
import QualityReviewModal from '@/components/modals/QualityReviewModal.vue'
import SearchModal from '@/components/modals/SearchModal.vue'
import QuickOpenModal from '@/components/modals/QuickOpenModal.vue'
import { useNotificationStore } from '@/stores/notification'
import { useAppInit } from '@/composables/useApp'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useBackendCheck } from '@/composables/useBackendCheck'
import { useGenerationOrchestrator } from '@/composables/useGenerationOrchestrator'
import { usePromptSync } from '@/composables/usePromptSync'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useUIStore } from '@/stores/ui'

const { initApp, cleanupApp } = useAppInit()
useKeyboardShortcuts()
useGenerationOrchestrator()
usePromptSync()
const { backendReachable, checking, checkBackend, customUrl } = useBackendCheck()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const route = useRoute()

// 初始化应用
onMounted(async () => {
  await initApp()

  // URL 恢复：刷新时从 URL 恢复项目/文件
  if (route.params.projectId) {
    const projectId = route.params.projectId as string
    try {
      await projectStore.openProject(projectId)
      if (projectStore.currentProject) {
        await fileStore.loadTree(projectId)
      }
    } catch (e) {
      console.warn('从 URL 恢复项目失败', e)
    }

    if (route.params.pathMatch) {
      const filePath = '/' + (route.params.pathMatch as string[]).join('/')
      editorStore.setCurrentFile(filePath)
    } else {
      await openDefaultProjectFile(projectId)
    }
  }

  // beforeunload：刷新/关闭页面时拦截
  window.addEventListener('beforeunload', handleBeforeUnload)
  // G0114 全局错误捕获
  window.addEventListener('error', handleGlobalError)
  window.addEventListener('unhandledrejection', handlePromiseRejection)
})

onUnmounted(() => {
  cleanupApp()
  window.removeEventListener('beforeunload', handleBeforeUnload)
  window.removeEventListener('error', handleGlobalError)
  window.removeEventListener('unhandledrejection', handlePromiseRejection)
})

function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (editorStore.isDirty) {
    e.preventDefault()
    e.returnValue = '有未保存的内容，确定要离开吗？'
  }
}

// G0114 全局错误处理
function handleGlobalError(event: ErrorEvent) {
  console.error('未捕获的错误:', event.error || event.message)
  // 避免通知过多，只对非调试错误进行提示
  if (event.error && !event.message.includes('ResizeObserver')) {
    try {
      useNotificationStore().error(`发生错误: ${event.message}`)
    } catch {}
  }
}

function handlePromiseRejection(event: PromiseRejectionEvent) {
  console.error('未捕获的 Promise 错误:', event.reason)
  try {
    useNotificationStore().error(`异步错误: ${(event.reason as any)?.message || '未知错误'}`)
  } catch {}
}

function settingsBtn() {
  useUIStore().openSettings()
}

async function openDefaultProjectFile(projectId: string) {
  if (fileStore.openFiles.length > 0 && editorStore.currentFilePath) return
  const node = findFile(fileStore.tree, 'outline.md') || findFirstMarkdown(fileStore.tree)
  if (!node) return
  try {
    const fileData = await fileStore.readFile(projectId, node.path)
    fileStore.openFile(node)
    editorStore.loadContent(node.path, fileData.content || '', fileData.frontmatter)
    editorStore.setCurrentFile(node.path)
  } catch (e) {
    console.warn('默认文件打开失败', e)
  }
}

function findFile(nodes: Array<{ name: string; path: string; type: string; children?: any[] }>, name: string): any | null {
  for (const node of nodes) {
    if (node.type === 'file' && node.name === name) return node
    if (node.children) {
      const found = findFile(node.children, name)
      if (found) return found
    }
  }
  return null
}

function findFirstMarkdown(nodes: Array<{ name: string; path: string; type: string; children?: any[] }>): any | null {
  for (const node of nodes) {
    if (node.type === 'file' && node.name.endsWith('.md')) return node
    if (node.children) {
      const found = findFirstMarkdown(node.children)
      if (found) return found
    }
  }
  return null
}

// 路由守卫：路由跳转前拦截（Vue Router beforeEach 已在 router/index.ts 中处理）

</script>

<template>
  <div class="app-shell">
    <!-- 后端连通性告警横幅 -->
    <div
      v-if="!checking && !backendReachable"
      class="backend-warning"
    >
      <div class="backend-warning-content">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>无法连接到后端服务</span>
        <code v-if="customUrl">{{ customUrl }}</code>
        <code v-else>/api → Vite proxy</code>
        <button class="retry-btn" @click="checkBackend">
          <i class="fa-solid fa-rotate"></i> 重试
        </button>
        <button class="settings-btn" @click="settingsBtn">
          <i class="fa-solid fa-gear"></i> 配置
        </button>
      </div>
    </div>
    <AppHeader />
    <router-view />
    <NotificationContainer />
    <CreateProjectModal />
    <OpenProjectModal />
    <SettingsModal />
    <TokenCountModal />
    <CompareModal />
    <FeedbackModal />
    <RevisionLogModal />
    <BatchGenerateModal />
    <ExtractModal />
    <QualityReviewModal />
    <SearchModal />
    <QuickOpenModal />
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.backend-warning {
  background: #e74c3c;
  color: #fff;
  padding: 8px 16px;
  font-size: 13px;
  flex-shrink: 0;
}

.backend-warning-content {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 1200px;
  margin: 0 auto;
}

.backend-warning-content code {
  background: rgba(255,255,255,0.2);
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
}

.backend-warning-content button {
  background: rgba(255,255,255,0.2);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.3);
  padding: 2px 10px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.backend-warning-content button:hover {
  background: rgba(255,255,255,0.35);
}

</style>

<style>
/* ── Ant Design Modal 暗色主题适配（全局样式，非 scoped） ── */
.ant-modal-confirm-title,
.ant-modal-confirm-content {
  color: var(--text-warm-white) !important;
}
.ant-modal-content {
  background: var(--ink-dark) !important;
}
.ant-modal-confirm-body > .anticon {
  color: var(--gold-primary) !important;
}
</style>
