<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
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
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useFileGeneration } from '@/composables/useFileGeneration'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useLLMStore } from '@/stores/llm'
import { useFileMetaStore } from '@/stores/fileMeta'
import { guessPromptType } from '@/utils/promptTypes'

const { initApp, cleanupApp } = useAppInit()
useKeyboardShortcuts()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const fileGen = useFileGeneration()
const rightPanelStore = useRightPanelStore()
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

// 路由守卫：路由跳转前拦截（Vue Router beforeEach 已在 router/index.ts 中处理）

// 监听 pendingGeneration：项目创建后自动触发流式生成
watch(
  () => projectStore.pendingGeneration,
  async (pending) => {
    if (!pending || !projectStore.currentProject) return

    // 检查 LLM 是否已配置
    const llmStore = useLLMStore()
    if (!llmStore.isConnected) {
      useNotificationStore().warning('LLM 未配置，跳过自动生成')
      projectStore.setPendingGeneration(null)
      return
    }

    const projectId = projectStore.currentProject.id
    const { filePath, prompt } = pending

    // 等待路由导航完成 + 文件树加载
    await new Promise(resolve => setTimeout(resolve, 500))

    // 打开文件（需先保存 prompt，以便右侧面板能立即加载）
    editorStore.setFilePrompt(filePath, prompt)
    const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
    fileStore.openFile(node)
    editorStore.setCurrentFile(filePath)

    try {
      // 读取文件（刚创建的空文件），并加载到编辑器
      const fileContent = await fileStore.readFile(projectId, filePath)
      if (fileContent) {
        editorStore.loadContent(filePath, fileContent.content || '')
      }
    } catch {
      // 文件可能尚未在后端就绪，忽略
    }

    // 触发流式生成
    useNotificationStore().info('正在生成创意...')
    try {
      await fileGen.generateToFile(projectId, filePath, prompt, pending.extraVars, pending.promptType)

      // 生成成功后保存元数据
      if (pending.promptType) {
        useFileMetaStore().saveMeta(projectId, filePath, {
          promptType: pending.promptType,
          extraVars: { ...(pending.extraVars || {}) },
          generatedAt: new Date().toISOString(),
        })
      }

      // 生成完成后，从磁盘重新加载内容到编辑器
      try {
        const result = await fileStore.readFile(projectId, filePath)
        if (result && result.content) {
          editorStore.loadContent(filePath, result.content)
        }
      } catch {}
    } catch (e: any) {
      console.error('自动生成失败:', e)
    }

    // 清除 pending 标记
    projectStore.setPendingGeneration(null)
  },
)

// 切换文件时，在右侧面板显示该文件关联的 prompt
watch(
  () => editorStore.currentFilePath,
  async (path) => {
    if (path) {
      const saved = editorStore.getFilePrompt(path)
      if (saved) {
        rightPanelStore.updatePrompt(saved)
        return
      }
      // 没有已保存的 prompt，根据文件类型加载默认模板
      const promptType = guessPromptType(path)
      if (!promptType) return
      try {
        const res = await fetch(`/api/prompts/${promptType}?project_id=${projectStore.currentProject?.id || ''}`)
        const json = await res.json()
        if (json?.data?.content) {
          editorStore.setFilePrompt(path, json.data.content)
          rightPanelStore.updatePrompt(json.data.content)
        }
      } catch {
        // 静默失败，右侧面板保持空白
      }
    }
  },
)

/** 根据文件路径推测对应的 Prompt 模板类型 —— 见 utils/promptTypes.ts */
</script>

<template>
  <div class="app-shell">
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
</style>
