<template>
  <div class="right-panel">
    <!-- 未打开项目：空状态 -->
    <div v-if="!projectStore.currentProject" class="panel-empty">
      <div class="empty-icon">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="9" y1="21" x2="9" y2="9"/>
        </svg>
      </div>
      <span class="empty-text">未打开项目</span>
      <span class="empty-hint">打开项目后可使用辅助工具</span>
    </div>
    <template v-else>
      <!-- Tab 导航 -->
      <div class="panel-tabs" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="panel-tab"
          :class="{ active: activeTab === tab.id }"
          @click="rightPanelStore.setActiveTab(tab.id)"
          :title="tab.label"
          role="tab"
          :aria-selected="activeTab === tab.id"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
      </div>

      <!-- 内容区域 -->
      <div class="panel-content">
        <PromptPanel v-show="activeTab === 'prompt'" />
        <PipelineEditor v-show="activeTab === 'pipeline'" />
        <WorkflowPanel v-show="activeTab === 'workflow'" />
        <StoryStatePanel v-show="activeTab === 'story'" ref="storyPanelRef" />
        <StyleGuidePanel v-show="activeTab === 'style'" ref="styleGuidePanelRef" />
        <ExecutionPanel v-show="activeTab === 'execution'" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useRightPanelStore } from '@/stores/rightPanel'
import PromptPanel from './PromptPanel.vue'
import PipelineEditor from './PipelineEditor.vue'
import WorkflowPanel from './WorkflowPanel.vue'
import ExecutionPanel from './ExecutionPanel.vue'
import StoryStatePanel from '../global/StoryStatePanel.vue'
import StyleGuidePanel from '../global/StyleGuidePanel.vue'

const projectStore = useProjectStore()
const rightPanelStore = useRightPanelStore()

const activeTab = computed(() => rightPanelStore.activeTab)

const storyPanelRef = ref<InstanceType<typeof StoryStatePanel>>()
const styleGuidePanelRef = ref<InstanceType<typeof StyleGuidePanel>>()

const tabs = [
  { id: 'prompt', label: '快捷', icon: '⚡' },
  { id: 'pipeline', label: '管线', icon: '🔧' },
  { id: 'workflow', label: '工作流', icon: '📋' },
  { id: 'story', label: '故事', icon: '📖' },
  { id: 'style', label: '文风', icon: '🪶' },
  { id: 'execution', label: '执行', icon: '📋' },
]

onMounted(() => {
  storyPanelRef.value?.loadState()
  styleGuidePanelRef.value?.loadGuide()
})

// 切换到"文风"tab 时重新加载内容（pipeline 可能刚写完 style-guide.md）
watch(activeTab, (tab) => {
  if (tab === 'style') styleGuidePanelRef.value?.loadGuide()
  if (tab === 'story') storyPanelRef.value?.loadState()
})
</script>

<style scoped lang="scss">
.right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--ink-dark);
}

.panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 24px;
  text-align: center;
  color: var(--text-muted-ink);

  .empty-icon {
    opacity: 0.3;
    margin-bottom: 4px;
  }

  .empty-text {
    font-size: 14px;
    font-weight: 500;
  }

  .empty-hint {
    font-size: 12px;
    color: var(--text-faint);
    line-height: 1.5;
    max-width: 180px;
  }
}

/* ── Tab 导航 ── */
.panel-tabs {
  display: flex;
  padding: 8px 8px 0;
  gap: 2px;
  background: var(--ink-deep);
  position: relative;

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 8px;
    right: 8px;
    height: 1px;
    background: linear-gradient(90deg, var(--gold-primary), var(--border-ink), transparent);
    opacity: 0.15;
  }
}

.panel-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 6px 7px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-muted-ink);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  transition: all var(--transition-normal);
  position: relative;
  white-space: nowrap;
  letter-spacing: 0.3px;

  .tab-icon {
    font-size: 13px;
    opacity: 0.6;
    transition: opacity var(--transition-fast);
  }

  .tab-label {
    transition: color var(--transition-fast);
  }

  &:hover {
    color: var(--text-ink);
    background: rgba(255, 255, 255, 0.02);

    .tab-icon { opacity: 0.8; }
  }

  &.active {
    color: var(--gold-primary);
    background: linear-gradient(180deg, rgba(201, 169, 110, 0.08), transparent);

    .tab-icon { opacity: 1; }

    // 底部活动指示条（毛笔笔触感）
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 20%;
      right: 20%;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
      border-radius: 1px;
      animation: brush-stroke 0.3s ease-out;
    }
  }
}

/* ── 内容区域 ── */
.panel-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--ink-dark);
}
</style>
