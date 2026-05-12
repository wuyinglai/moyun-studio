import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { Modal } from 'ant-design-vue'

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

      // 脏状态检查：使用 Ant Design Modal，不阻塞 UI 线程
      if (editorStore.isDirty) {
        const confirmed = await new Promise<boolean>((resolve) => {
          Modal.confirm({
            title: '未保存的内容',
            content: '有未保存的内容，确定要离开吗？',
            okText: '确定',
            cancelText: '取消',
            onOk: () => resolve(true),
            onCancel: () => resolve(false),
          })
        })
        if (!confirmed) return false
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
