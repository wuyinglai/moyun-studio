import { createRouter, createWebHistory, type RouteRecordRaw, type NavigationGuardNext } from 'vue-router'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [],
  },
  {
    path: '/project/:projectId',
    name: 'project',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [],
    beforeEnter: async (to) => {
      const projectStore = useProjectStore()
      const fileStore = useFileStore()
      const projectId = to.params.projectId as string
      if (!projectStore.currentProject || projectStore.currentProject.id !== projectId) {
        await projectStore.openProject(projectId)
      }
      if (projectStore.currentProject) {
        await fileStore.loadTree(projectId)
      }
    },
  },
  {
    path: '/project/:projectId/file/*',
    name: 'file',
    component: () => import('@/components/layout/AppLayout.vue'),
    beforeEnter: async (to) => {
      const projectStore = useProjectStore()
      const fileStore = useFileStore()
      const editorStore = useEditorStore()
      const projectId = to.params.projectId as string
      const filePath = '/' + (to.params.pathMatch as string[]).join('/')

      // 脏状态检查：路由跳转前确认
      if (editorStore.isDirty) {
        const confirmed = window.confirm('有未保存的内容，确定要离开吗？')
        if (!confirmed) return false
        // 用户确认后，保存或丢弃
        // 这里只阻止路由，保存由用户自行决定
      }

      if (!projectStore.currentProject || projectStore.currentProject.id !== projectId) {
        await projectStore.openProject(projectId)
        await fileStore.loadTree(projectId)
      }

      const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
      fileStore.openFile(node)
      editorStore.setCurrentFile(filePath)

      const content = await fileStore.readFile(projectId, filePath)
      editorStore.loadContent(filePath, content.content || '')
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
