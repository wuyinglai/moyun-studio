import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { Modal } from 'ant-design-vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import LiteWritingView from '@/views/LiteWritingView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/lite',
    name: 'lite-home',
    component: LiteWritingView,
  },
  {
    path: '/',
    name: 'home',
    component: AppLayout,
    children: [],
    beforeEnter: async () => {
      const projectStore = useProjectStore()
      const fileStore = useFileStore()
      const projectId = projectStore.currentProject?.id
      if (projectId) {
        try {
          await projectStore.openProject(projectId)
          await fileStore.loadTree(projectId)
        } catch {
          // 项目可能已被删除或后端不可用，清除过期数据
          projectStore.closeProject()
        }
      }
    },
  },
  {
    path: '/project/:projectId',
    name: 'project',
    component: AppLayout,
    children: [],
    beforeEnter: async (to) => {
      const projectStore = useProjectStore()
      const fileStore = useFileStore()
      const projectId = to.params.projectId as string
      try {
        if (!projectStore.currentProject || projectStore.currentProject.id !== projectId) {
          await projectStore.openProject(projectId)
        }
        if (projectStore.currentProject) {
          await fileStore.loadTree(projectId)
        }
      } catch (e) {
        console.warn('项目加载失败（页面仍可渲染）:', e)
      }
    },
  },
  {
    path: '/project/:projectId/lite',
    name: 'project-lite',
    component: LiteWritingView,
    beforeEnter: async (to) => {
      const projectStore = useProjectStore()
      const fileStore = useFileStore()
      const projectId = to.params.projectId as string
      try {
        if (!projectStore.currentProject || projectStore.currentProject.id !== projectId) {
          await projectStore.openProject(projectId)
        }
        if (projectStore.currentProject) {
          await fileStore.loadTree(projectId)
        }
      } catch (e) {
        console.warn('爽文项目加载失败（页面仍可渲染）:', e)
      }
    },
  },
  {
    path: '/project/:projectId/file/:pathMatch(.*)*',
    name: 'file',
    component: AppLayout,
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

      try {
        if (!projectStore.currentProject || projectStore.currentProject.id !== projectId) {
          await projectStore.openProject(projectId)
          await fileStore.loadTree(projectId)
        }
      } catch (e) {
        console.warn('项目加载失败:', e)
      }

      const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
      fileStore.openFile(node)
      editorStore.setCurrentFile(filePath)

      try {
        const content = await fileStore.readFile(projectId, filePath)
        editorStore.loadContent(filePath, content.content || '')
      } catch {
        console.warn('读取文件失败:', filePath)
      }
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
