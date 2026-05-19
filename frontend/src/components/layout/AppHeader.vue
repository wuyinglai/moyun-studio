<template>
  <header class="app-header">
    <!-- 左侧：Logo + 项目名 -->
    <div class="header-left">
      <div class="logo">
        <span
          class="logo-icon"
          aria-hidden="true"
        >墨</span>
        <span class="logo-text">墨韵</span>
      </div>

      <div class="header-divider" />

      <div
        v-if="projectStore.currentProject"
        class="project-name"
      >
        <input
          v-if="isEditingName"
          ref="nameInputRef"
          v-model="editingName"
          class="project-name-input"
          @blur="confirmNameEdit"
          @keydown.enter="confirmNameEdit"
          @keydown.escape="cancelNameEdit"
        >
        <span
          v-else
          class="project-name-text"
          :title="projectStore.currentProject.name"
          @click="startNameEdit"
        >
          {{ projectStore.currentProject.name }}
        </span>
        <span
          class="project-name-hint"
          title="点击编辑项目名"
        >✎</span>
        <button
          class="mode-link"
          @click="switchWritingMode"
        >
          {{ isLiteRoute ? '专业模式' : '爽文模式' }}
        </button>
      </div>
      <div
        v-else
        class="project-name project-name--empty"
      >
        <span class="project-name-placeholder">未打开项目</span>
      </div>
    </div>

    <!-- 中：通知位 -->
    <div
      id="header-notifications"
      class="header-center"
    />

    <!-- 右侧：状态 + 按钮 -->
    <div class="header-right">
      <!-- LLM 连接状态 -->
      <button
        class="llm-status"
        :class="{ 'llm-status--connected': llmStore.isConnected }"
        :title="`LLM: ${connectionStatus}`"
        @click="uiStore.openSettings()"
      >
        <span class="status-dot">
          <span class="status-dot-inner" />
        </span>
        <span class="status-text">{{ llmStore.isConnected ? '已连接' : '未连接' }}</span>
        <span
          v-if="sseConnected"
          class="sse-indicator"
          title="SSE已连接"
        >SSE</span>
      </button>

      <!-- LLM 调用中 -->
      <div
        v-if="llmStore.isGenerating"
        class="llm-generating"
      >
        <span class="generating-dots">
          <span /><span /><span />
        </span>
        <span class="generating-text">{{ generatingLabel }}<span
          v-if="llmStore.currentStepLabel"
          class="step-label"
        > — {{ llmStore.currentStepLabel }}</span></span>
      </div>

      <!-- Thinking 开关 -->
      <div
        v-if="llmStore.config && llmStore.config.apiType"
        class="thinking-toggle"
      >
        <span class="thinking-label">Thinking</span>
        <button
          class="toggle-btn"
          :class="{ 'toggle-btn--on': llmStore.config.thinking }"
          aria-label="切换思考模式"
          @click="toggleThinking"
        >
          <span class="toggle-knob" />
        </button>
      </div>

      <!-- L1/L2 模式切换 -->
      <div
        v-if="projectStore.currentProject"
        class="auto-mode-switch"
      >
        <button
          class="mode-btn"
          :class="{ 'mode-btn--active': autoMode === 'L1' }"
          title="L1 半自动：每完成一个文件后暂停，需手动点「写下一部分」继续"
          @click="setAutoMode('L1')"
        >
          L1
        </button>
        <button
          class="mode-btn"
          :class="{ 'mode-btn--active': autoMode === 'L2' }"
          title="L2 自动：生成完成后自动继续下一个文件，可随时点「停止」暂停"
          @click="setAutoMode('L2')"
        >
          L2
        </button>
        <span class="auto-mode-label">{{ autoMode === 'L1' ? '半自动' : '自动' }}</span>
      </div>

      <!-- 操作按钮组 -->
      <div class="action-buttons">
        <button
          class="btn btn-ghost"
          title="打开项目"
          @click="openProjectWithGuard"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span class="btn-label">打开</span>
        </button>

        <button
          v-if="projectStore.currentProject"
          class="btn btn-ghost"
          title="项目备份"
          @click="uiStore.openBackup()"
        >
          <i class="fa-solid fa-box-archive" />
          <span class="btn-label">备份</span>
        </button>

        <button
          class="btn btn-primary"
          title="新建项目"
          @click="createProjectWithGuard"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line
              x1="12"
              y1="5"
              x2="12"
              y2="19"
            /><line
              x1="5"
              y1="12"
              x2="19"
              y2="12"
            />
          </svg>
          <span class="btn-label">新建</span>
        </button>

        <button
          class="btn btn-icon"
          title="设置"
          @click="uiStore.openSettings()"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle
              cx="12"
              cy="12"
              r="3"
            /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import { useProjectStore } from '@/stores/project'
import { useLLMStore } from '@/stores/llm'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useFileStore } from '@/stores/file'
import { useSSE } from '@/composables/useSSE'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'

const projectStore = useProjectStore()
const llmStore = useLLMStore()
const uiStore = useUIStore()
const editorStore = useEditorStore()
const fileStore = useFileStore()
const notification = useNotificationStore()
const chatStore = useChatStore()
const { isConnected: sseConnected, isReconnecting } = useSSE()
const route = useRoute()
const router = useRouter()

const isEditingName = ref(false)
const editingName = ref('')
const nameInputRef = ref<HTMLInputElement | null>(null)

function startNameEdit() {
  editingName.value = projectStore.currentProject?.name || ''
  isEditingName.value = true
  nextTick(() => nameInputRef.value?.focus())
}

async function confirmNameEdit() {
  if (!projectStore.currentProject) return
  const newName = editingName.value.trim()
  if (newName && newName !== projectStore.currentProject.name) {
    try {
      await projectStore.updateProject(projectStore.currentProject.id, { name: newName })
      notification.success('项目名已更新')
    } catch {
      notification.error('更新项目名失败')
    }
  }
  isEditingName.value = false
}

function cancelNameEdit() {
  isEditingName.value = false
}

const generatingLabel = computed(() => {
  if (!llmStore.isGenerating) return ''
  const mode = chatStore.generationMode
  if (mode === 'continue') return '续写章节中'
  if (mode === 'rewrite') return '重写章节中'
  return 'AI 创作中'
})

const connectionStatus = computed(() => {
  if (isReconnecting.value) return '重连中...'
  if (llmStore.isConnected && sseConnected.value) return '已连接'
  return '未连接'
})

const isLiteRoute = computed(() => route.name === 'project-lite' || route.name === 'lite-home')

const autoMode = computed(() => localStorage.getItem('moyun-auto-mode') || 'L1')

function setAutoMode(mode: 'L1' | 'L2') {
  localStorage.setItem('moyun-auto-mode', mode)
}

async function toggleThinking() {
  llmStore.config.thinking = !llmStore.config.thinking
  await llmStore.saveConfig({ thinking: llmStore.config.thinking })
}

async function confirmUnsavedSwitch(): Promise<boolean> {
  if (!editorStore.isDirty) return true
  return await new Promise((resolve) => {
    Modal.confirm({
      title: '有未保存的内容',
      content: '当前项目仍有未保存内容，确定要继续切换吗？',
      okText: '继续',
      cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
}

async function openProjectWithGuard() {
  if (await confirmUnsavedSwitch()) {
    uiStore.openOpenProject()
  }
}

async function createProjectWithGuard() {
  if (!(await confirmUnsavedSwitch())) return
  if (isLiteRoute.value) {
    projectStore.closeProject()
    editorStore.setCurrentFile(null)
    fileStore.unsavedFiles.clear()
    router.push('/lite')
  } else {
    uiStore.openCreateProject()
  }
}

async function switchWritingMode() {
  if (!projectStore.currentProject) return
  if (!(await confirmUnsavedSwitch())) return
  const projectId = projectStore.currentProject.id
  if (isLiteRoute.value) {
    router.push(`/project/${projectId}`)
  } else {
    router.push(`/project/${projectId}/lite`)
  }
}
</script>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 20px;
  background: var(--ink-dark);
  border-bottom: 1px solid var(--border-ink);
  flex-shrink: 0;
  gap: 12px;
  position: relative;
  z-index: 100;
  user-select: none;

  /* 底部金线 */
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 80px;
    right: 80px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
    opacity: 0.15;
  }
}

/* ── 左侧区域 ── */
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 200px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: default;
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-family: var(--font-kai);
  font-size: 18px;
  font-weight: 700;
  color: var(--ink-deepest);
  background: linear-gradient(135deg, var(--gold-primary), var(--gold-light));
  border-radius: 6px;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--text-warm-white), var(--gold-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
}

.header-divider {
  width: 1px;
  height: 24px;
  background: linear-gradient(180deg, transparent, var(--border-ink), transparent);
}

/* ── 项目名 ── */
.project-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 280px;

  &--empty {
    color: var(--text-muted-ink);
  }
}

.project-name-text {
  cursor: pointer;
  border-bottom: 1px dashed transparent;
  transition: all var(--transition-fast);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  &:hover {
    border-bottom-color: var(--text-muted-ink);
  }
}

.project-name-hint {
  font-size: 12px;
  color: var(--text-faint);
  opacity: 0;
  transition: opacity var(--transition-fast);
  cursor: pointer;
}

.project-name:hover .project-name-hint {
  opacity: 1;
}

.project-name-placeholder {
  color: var(--text-faint);
  font-style: italic;
  font-size: 13px;
}

.project-name-input {
  background: var(--ink-light);
  border: 1px solid var(--gold-primary);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  padding: 3px 8px;
  outline: none;
  width: 220px;
  box-shadow: 0 0 0 3px rgba(201, 169, 110, 0.1);
}

.mode-link {
  margin-left: 8px;
  padding: 4px 9px;
  border: 1px solid rgba(201, 169, 110, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(201, 169, 110, 0.08);
  color: var(--gold-primary);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.mode-link:hover {
  background: rgba(201, 169, 110, 0.14);
}

/* ── 中间 ── */
.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── 右侧区域 ── */
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── LLM 连接状态 ── */
.llm-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted-ink);
  padding: 6px 14px 6px 10px;
  border-radius: var(--radius-pill);
  background: var(--ink-mid);
  border: 1px solid var(--border-ink);
  transition: all var(--transition-normal);
  cursor: pointer;

  &:hover {
    border-color: var(--gold-primary);
    background: var(--ink-light);
  }
}

.status-dot {
  position: relative;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--vermillion);
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-dot-inner {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: inherit;
  animation: ink-pulse 2s ease-out infinite;
}

.llm-status--connected .status-dot {
  background: var(--jade-light);
}

.status-text {
  font-size: 12px;
}

.sse-indicator {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: rgba(45, 138, 110, 0.15);
  color: var(--jade-light);
  letter-spacing: 0.5px;
}

/* ── LLM 生成中动画 ── */
.llm-generating {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--gold-primary);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  background: rgba(201, 169, 110, 0.06);
  border: 1px solid rgba(201, 169, 110, 0.15);
}

.generating-dots {
  display: flex;
  gap: 3px;

  span {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--gold-primary);
    animation: dot-bounce 1.4s ease-in-out infinite both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
    &:nth-child(3) { animation-delay: 0s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.generating-text {
  white-space: nowrap;
}

/* ── Thinking 开关 ── */
.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 8px;

  .thinking-label {
    font-size: 12px;
    color: var(--text-muted-ink);
    font-weight: 500;
  }

  .toggle-btn {
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background: var(--ink-light);
    border: 1px solid var(--border-ink);
    position: relative;
    cursor: pointer;
    transition: all var(--transition-normal);

    .toggle-knob {
      position: absolute;
      top: 2px;
      left: 2px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: var(--text-muted-ink);
      transition: all var(--transition-normal);
    }

    &--on {
      background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
      border-color: var(--gold-primary);

      .toggle-knob {
        transform: translateX(16px);
        background: white;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
      }
    }
  }
}

/* ── 操作按钮 ── */
.action-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 4px;
  padding-left: 12px;
  border-left: 1px solid var(--border-ink);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition-normal);
  cursor: pointer;
  white-space: nowrap;

  &:active {
    transform: scale(0.97);
  }

  svg {
    flex-shrink: 0;
  }
}

.btn-primary {
  background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
  color: var(--ink-deepest);
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(201, 169, 110, 0.2);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(201, 169, 110, 0.3);
  }
}

.btn-ghost {
  background: var(--ink-mid);
  color: var(--text-ink);
  border: 1px solid var(--border-ink);

  &:hover {
    background: var(--ink-hover);
    border-color: var(--gold-primary);
    color: var(--gold-primary);
  }
}

.btn-icon {
  width: 34px;
  height: 34px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-muted-ink);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--ink-hover);
    color: var(--gold-primary);
  }
}

/* ── L1/L2 模式切换 ── */
.auto-mode-switch {
  display: flex;
  align-items: center;
  gap: 0;
  margin: 0 4px;
  border: 1px solid var(--border-ink);
  border-radius: 4px;
  overflow: hidden;

  .mode-btn {
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    line-height: 20px;
    border: none;
    background: transparent;
    color: var(--text-muted-ink);
    cursor: pointer;
    transition: all var(--transition-normal);
    letter-spacing: 0.5px;

    &--active {
      background: var(--gold-primary);
      color: var(--ink-deep);
    }

    &:not(&--active):hover {
      color: var(--text-warm-white);
    }
  }
  .auto-mode-label {
    font-size: 10px;
    color: var(--text-muted-ink);
    padding: 0 6px;
    white-space: nowrap;
  }
}

/* ── 响应式：窄屏隐藏文字标签 ── */
@media (max-width: 900px) {
  .btn-label {
    display: none;
  }
}
</style>
