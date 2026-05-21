<script setup lang="ts">
/**
 * ErrorBoundary — 捕获子组件运行时错误，显示 fallback UI
 *
 * 使用 Vue onErrorCaptured 钩子，阻止错误向上冒泡导致整页白屏。
 * 提供"重试"和"返回项目列表"操作。
 */
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

withDefaults(defineProps<{
  title?: string
  description?: string
}>(), {
  title: '组件加载出错',
  description: '该区域发生了意外错误，你可以重试或返回项目列表。',
})

const emit = defineEmits<{
  retry: []
}>()

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err: Error, _instance, info) => {
  // 过滤敏感信息：截断过长的 message，移除 API Key
  let msg = err.message || String(err)
  // 移除可能的 API Key 模式
  msg = msg.replace(/sk-[a-zA-Z0-9]{10,}/g, 'sk-***')
  msg = msg.replace(/api[_-]?key[=:]\s*\S+/gi, 'api_key=***')
  // 截断过长内容（避免正文全文泄露到错误日志）
  if (msg.length > 200) {
    msg = msg.substring(0, 200) + '...'
  }

  console.error('[ErrorBoundary]', info, msg)
  errorMessage.value = msg
  hasError.value = true

  // 阻止错误继续向上冒泡
  return false
})

const router = useRouter()

function handleRetry() {
  hasError.value = false
  errorMessage.value = ''
  emit('retry')
}

function handleGoHome() {
  router.push('/').catch(() => {
    // 路由跳转失败时刷新页面
    window.location.href = '/'
  })
}

function handleRefresh() {
  window.location.reload()
}
</script>

<template>
  <div
    v-if="hasError"
    class="error-boundary"
    data-testid="error-boundary"
  >
    <div class="error-content">
      <div class="error-icon">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
          />
          <line
            x1="12"
            y1="8"
            x2="12"
            y2="12"
          />
          <line
            x1="12"
            y1="16"
            x2="12.01"
            y2="16"
          />
        </svg>
      </div>
      <h3 class="error-title">{{ title }}</h3>
      <p class="error-desc">{{ description }}</p>
      <p
        v-if="errorMessage"
        class="error-detail"
      >
        {{ errorMessage }}
      </p>
      <div class="error-actions">
        <button
          class="retry-btn"
          data-testid="error-boundary-retry"
          @click="handleRetry"
        >
          重试
        </button>
        <button
          class="refresh-btn"
          @click="handleRefresh"
        >
          刷新页面
        </button>
        <button
          class="home-btn"
          @click="handleGoHome"
        >
          返回项目列表
        </button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<style scoped lang="scss">
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 120px;
  padding: 24px;
  background: var(--ink-deep, #1a1a2e);
  color: var(--text-warm-white, #e8e0d0);
}

.error-content {
  text-align: center;
  max-width: 400px;
}

.error-icon {
  color: var(--vermillion, #e74c3c);
  margin-bottom: 12px;
  opacity: 0.8;
}

.error-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-warm-white, #e8e0d0);
}

.error-desc {
  font-size: 13px;
  color: var(--text-muted-ink, #8a8578);
  line-height: 1.5;
  margin-bottom: 8px;
}

.error-detail {
  font-size: 11px;
  color: var(--text-faint, #6a6558);
  background: rgba(255, 255, 255, 0.03);
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  word-break: break-all;
  max-height: 80px;
  overflow-y: auto;
}

.error-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.error-actions button {
  font-size: 12px;
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid var(--border-ink, #3a3a4a);
  background: transparent;
  color: var(--text-ink, #c8c0b0);
  transition: all 0.2s;
}

.error-actions button:hover {
  background: rgba(255, 255, 255, 0.05);
}

.retry-btn {
  border-color: var(--gold-primary, #c9a96e) !important;
  color: var(--gold-primary, #c9a96e) !important;
}

.retry-btn:hover {
  background: rgba(201, 169, 110, 0.1) !important;
}
</style>
