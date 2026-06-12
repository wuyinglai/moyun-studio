<template>
  <div
    class="editor-toolbar"
    data-testid="editor-toolbar"
  >
    <a-space>
      <a-button
        size="small"
        :disabled="!canGoBack"
        title="后退 (没有更早的版本)"
        @click="handleBack"
      >
        <template #icon>
          <i class="fa-solid fa-rotate-left" />
        </template>
        后退
      </a-button>
      <a-button
        size="small"
        :disabled="!canGoForward"
        title="前进 (没有更新的版本)"
        @click="handleForward"
      >
        <template #icon>
          <i class="fa-solid fa-rotate-right" />
        </template>
        前进
      </a-button>
      <a-divider type="vertical" />
      <a-button
        size="small"
        :type="isPreviewMode ? 'primary' : 'default'"
        @click="togglePreview"
      >
        <template #icon>
          <i class="fa-solid fa-eye" />
        </template>
        {{ isPreviewMode ? '编辑' : '预览' }}
      </a-button>
      <a-divider type="vertical" />
      <a-button
        v-if="showStopButton"
        danger
        size="small"
        @click="handleStop"
      >
        <template #icon>
          <i class="fa-solid fa-stop" />
        </template>
        停止
      </a-button>
      <a-button
        v-if="showNextButton"
        size="small"
        type="primary"
        data-testid="write-next-button"
        @click="writeNextScene"
      >
        📄 写下一场景
      </a-button>
      <template v-if="!isGenerating">
        <a-button
          v-if="isChapterFile"
          size="small"
          type="primary"
          ghost
          @click="runPipeline('polish')"
        >
          ✏️ 润色
        </a-button>
        <a-button
          v-if="isChapterFile"
          size="small"
          type="primary"
          ghost
          data-testid="rewrite-button"
          @click="runPipeline('rewrite')"
        >
          📦 精修
        </a-button>
        <a-button
          v-if="isChapterFile"
          size="small"
          type="primary"
          ghost
          @click="runPipeline('extract')"
        >
          🌟 提取
        </a-button>
        <a-divider
          v-if="isChapterFile"
          type="vertical"
        />
        <a-button
          v-if="!isSystemFile"
          size="small"
          title="用原参数重新生成"
          @click="handleRegenerate"
        >
          🔄 重新生成
        </a-button>
        <a-dropdown v-if="!isSystemFile">
          <a-button size="small">
            ➕ 自定义 <i class="fa-solid fa-chevron-down" />
          </a-button>
          <template #overlay>
            <a-menu @click="handleCustomPipeline">
              <a-menu-item
                v-for="p in customPipelines"
                :key="p.name"
              >
                {{ p.label }}
              </a-menu-item>
              <a-menu-item
                v-if="customPipelines.length === 0"
                disabled
              >
                暂无自定义管线
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <a-divider
          v-if="!isSystemFile"
          type="vertical"
        />
        <a-dropdown>
          <a-button size="small">
            更多 <i class="fa-solid fa-chevron-down" />
          </a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="handleTokenCount">
                <i class="fa-solid fa-calculator" /> Token
              </a-menu-item>
              <a-menu-item @click="handleCompare">
                <i class="fa-solid fa-code-compare" /> 对比
              </a-menu-item>
              <a-menu-item @click="handleFeedback">
                <i class="fa-solid fa-comment" /> 反馈
              </a-menu-item>
              <a-menu-item @click="handleRevisionLog">
                <i class="fa-solid fa-clock-rotate-left" /> 修改日志
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item @click="handleExtractModal">
                <i class="fa-solid fa-brain" /> 智能提取
              </a-menu-item>
              <a-menu-item
                data-testid="batch-generate-button"
                @click="handleBatchGenerate"
              >
                <i class="fa-solid fa-wand-magic-sparkles" /> 批量生成
              </a-menu-item>
              <a-menu-item @click="handleQualityReview">
                <i class="fa-solid fa-check-circle" /> 质量审查
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item
                data-testid="scene-plan-button"
                @click="handleScenePlan"
              >
                <i class="fa-solid fa-bullseye" /> 场景计划
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </template>
      <a-divider type="vertical" />
      <span
        class="generation-mode-badge"
        :title="isDevMode
          ? '工具栏生成按钮会调用真实 LLM；模拟运行仅在执行面板测试按钮中可用'
          : '当前生成操作将调用真实 LLM 模型'"
      >
        真实 LLM
      </span>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button as AButton, Space as ASpace, Divider as ADivider, Dropdown as ADropdown, Menu as AMenu, MenuItem as AMenuItem, MenuDivider as AMenuDivider } from 'ant-design-vue'
import { useHistoryStore } from '@/stores/history'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import { useUIStore } from '@/stores/ui'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useMarkdownPreview } from '@/composables/useMarkdownPreview'
import { useSceneGenerationActions } from '@/composables/useSceneGenerationActions'
import { useEditorFileActions } from '@/composables/useEditorFileActions'

const historyStore = useHistoryStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()
const uiStore = useUIStore()
const rightPanelStore = useRightPanelStore()
const { isPreviewMode, togglePreview } = useMarkdownPreview()

// 生成模式提示：isDevMode 仅影响 title 补充说明，badge 始终显示"真实 LLM"
const isDevMode = import.meta.env.DEV

const {
  isGenerating,
  showStopButton,
  showNextButton,
  writeNextScene,
  runPipeline,
  handleCustomPipeline,
  handleRegenerate,
  handleStop,
} = useSceneGenerationActions()

const {
  isChapterFile,
  isSystemFile,
  customPipelines,
} = useEditorFileActions()

function handleBack() {
  const path = editorStore.currentFilePath
  if (!path) return
  const content = historyStore.goBack(path)
  if (content !== null) {
    editorStore.setContent(content)
    notification.info('已恢复到上一个版本')
  } else {
    notification.warning('没有更早的版本')
  }
}

function handleForward() {
  const path = editorStore.currentFilePath
  if (!path) return
  const content = historyStore.goForward(path)
  if (content !== null) {
    editorStore.setContent(content)
    notification.info('已恢复到下一个版本')
  } else {
    notification.warning('没有更新的版本')
  }
}

const canGoBack = computed(() => {
  return historyStore.canGoBack(editorStore.currentFilePath || undefined)
})

const canGoForward = computed(() => {
  return historyStore.canGoForward(editorStore.currentFilePath || undefined)
})

function handleTokenCount() { uiStore.openTokenCount() }
function handleCompare() { uiStore.openCompare() }
function handleFeedback() { uiStore.openFeedback() }
function handleRevisionLog() { uiStore.openRevisionLog() }
function handleExtractModal() { uiStore.openExtract() }
function handleBatchGenerate() { uiStore.openBatchGenerate() }
function handleQualityReview() { uiStore.openQualityReview() }
function handleScenePlan() { rightPanelStore.setActiveTab('scene-plan') }
</script>

<style scoped lang="scss">
.editor-toolbar {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: var(--ink-mid);
  border-bottom: 1px solid var(--border-ink);
  flex-shrink: 0;
  gap: 2px;
}

.editor-toolbar :deep(.ant-btn) {
  color: var(--text-ink);
  background: transparent;
  border: 1px solid var(--border-ink);
  font-size: 12px;
  height: 30px;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover:not(:disabled) {
    color: var(--gold-primary);
    border-color: var(--gold-primary);
    background: rgba(201, 169, 110, 0.06);
  }

  &:disabled {
    color: var(--text-faint);
    opacity: 0.4;
  }

  &.ant-btn-primary {
    color: var(--ink-deepest);
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
    border-color: var(--gold-primary);

    &:hover {
      box-shadow: 0 4px 12px rgba(201, 169, 110, 0.25);
    }
  }

  &.ant-btn-dangerous {
    color: var(--vermillion-light);
    border-color: rgba(192, 57, 43, 0.3);

    &:hover {
      background: rgba(192, 57, 43, 0.1) !important;
      color: var(--vermillion-light) !important;
      border-color: var(--vermillion-light) !important;
    }
  }
}

.editor-toolbar :deep(.ant-divider-vertical) {
  border-color: var(--border-ink);
  height: 18px;
  top: 0;
  margin: 0 4px;
}

.editor-toolbar :deep(.ant-dropdown-trigger) {
  // 自定义管线按钮样式继承 ant-btn
}

.generation-mode-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
  cursor: default;
  flex-shrink: 0;
  background: rgba(59, 130, 246, 0.12);
  color: var(--accent-primary, #3b82f6);
}
</style>
