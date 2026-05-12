<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import NotificationContainer from '@/components/layout/NotificationContainer.vue'
import CreateProjectModal from '@/components/modals/CreateProjectModal.vue'
import OpenProjectModal from '@/components/modals/OpenProjectModal.vue'
import SettingsModal from '@/components/modals/SettingsModal.vue'
import { useAppInit } from '@/composables/useApp'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { sseService } from '@/composables/useSSE'

const { initApp, cleanupApp } = useAppInit()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const router = useRouter()
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
        const fileStore = (await import('@/stores/file')).useFileStore()
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
})

onUnmounted(() => {
  cleanupApp()
})

// beforeunload：刷新/关闭页面时拦截
window.addEventListener('beforeunload', (e) => {
  if (editorStore.isDirty) {
    e.preventDefault()
    e.returnValue = '有未保存的内容，确定要离开吗？'
  }
})

// 路由守卫：路由跳转前拦截（Vue Router beforeEach 已在 router/index.ts 中处理）
</script>

<template>
  <div id="app">
    <AppHeader />
    <router-view />
    <NotificationContainer />
    <CreateProjectModal />
    <OpenProjectModal />
    <SettingsModal />
  </div>
</template>

<style scoped>
#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
