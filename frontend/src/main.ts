import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPersistedstate from 'pinia-plugin-persistedstate'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import router from './router'
import './assets/styles/base.css'
import App from './App.vue'
import { useUIStore } from './stores/ui'
import { useNotificationStore } from './stores/notification'
import { restoreInterruptedTasks } from './composables/useTaskQueue'
import { sseService } from './composables/useSSE'

const pinia = createPinia()
pinia.use(piniaPersistedstate)

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(Antd)

// ── 全局错误处理 ──────────────────────────────────────────────
// 1. Vue runtime error handler
app.config.errorHandler = (err, instance, info) => {
  const msg = sanitizeErrorMessage(err)
  const componentName = instance?.$options?.name || instance?.$options?.__name || '<Anonymous>'
  console.error(`[Vue Error] ${componentName} (${info}):`, msg)

  try {
    useNotificationStore().error(`页面组件出现错误，请刷新或返回项目列表`)
  } catch {
    // 通知 store 不可用时忽略
  }
}

// 2. 未处理的 Promise rejection
window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
  const msg = sanitizeErrorMessage(event.reason)
  console.error('[Unhandled Rejection]:', msg)

  // 避免通知过多（ResizeObserver 等无害错误）
  if (!isIgnorableError(event.reason)) {
    try {
      useNotificationStore().error(`异步操作出错: ${truncate(msg, 100)}`)
    } catch {
      // 忽略
    }
  }
})

// 3. 全局资源/脚本错误
window.addEventListener('error', (event: ErrorEvent) => {
  const msg = sanitizeErrorMessage(event.error || event.message)
  console.error('[Global Error]:', msg)

  if (!isIgnorableError(event.error || event.message)) {
    try {
      useNotificationStore().error(`页面出现错误，请刷新重试`)
    } catch {
      // 忽略
    }
  }
})

// ── 辅助函数 ──────────────────────────────────────────────────

/** 清理错误消息：移除敏感信息 */
function sanitizeErrorMessage(err: unknown): string {
  let msg = err instanceof Error ? err.message : String(err)

  // 移除 API Key 模式
  msg = msg.replace(/sk-[a-zA-Z0-9]{10,}/g, 'sk-***')
  msg = msg.replace(/api[_-]?key[=:]\s*\S+/gi, 'api_key=***')

  // 截断过长内容（避免正文全文泄露到错误日志）
  return truncate(msg, 500)
}

/** 截断字符串 */
function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.substring(0, maxLen) + '...'
}

/** 判断是否为可忽略的无害错误 */
function isIgnorableError(err: unknown): boolean {
  if (!err) return false
  const msg = err instanceof Error ? err.message : String(err)
  // ResizeObserver 循环、Script error 等无害错误
  return msg.includes('ResizeObserver') || msg === 'Script error.'
}

// ── 初始化 ────────────────────────────────────────────────────

// 初始化主题（Pinia persist 恢复后自动 applyTheme）
useUIStore()

app.mount('#app')

// 恢复页面刷新前中断的任务
restoreInterruptedTasks()

// 开发/测试环境：暴露 sseService 到 window 供测试使用
if (import.meta.env.DEV) {
  ;(window as any).sseService = sseService
}
