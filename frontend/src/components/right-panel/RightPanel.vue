<template>
  <div class="right-panel">
    <!-- Tab 切换 -->
    <div class="panel-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="panel-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        <i :class="tab.icon"></i>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- 内容区域 -->
    <div class="panel-content">
      <PromptPanel v-show="activeTab === 'prompt'" />
      <StoryStatePanel v-show="activeTab === 'story'" ref="storyPanelRef" />
      <StyleGuidePanel v-show="activeTab === 'style'" ref="styleGuidePanelRef" />
      <RecentContextPanel v-show="activeTab === 'context'" ref="recentContextPanelRef" />
      <ExecutionPanel v-show="activeTab === 'execution'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PromptPanel from './PromptPanel.vue'
import ExecutionPanel from './ExecutionPanel.vue'
import StoryStatePanel from '../global/StoryStatePanel.vue'
import StyleGuidePanel from '../global/StyleGuidePanel.vue'
import RecentContextPanel from '../global/RecentContextPanel.vue'

const activeTab = ref('prompt')

const storyPanelRef = ref<InstanceType<typeof StoryStatePanel>>()
const styleGuidePanelRef = ref<InstanceType<typeof StyleGuidePanel>>()
const recentContextPanelRef = ref<InstanceType<typeof RecentContextPanel>>()

const tabs = [
  { id: 'prompt', label: '提示词', icon: 'fa-solid fa-terminal' },
  { id: 'story', label: '故事状态', icon: 'fa-solid fa-book-open' },
  { id: 'style', label: '文风指南', icon: 'fa-solid fa-feather' },
  { id: 'context', label: '上下文', icon: 'fa-solid fa-clock-rotate-left' },
  { id: 'execution', label: '执行', icon: 'fa-solid fa-list-check' },
]

onMounted(() => {
  storyPanelRef.value?.loadState()
  styleGuidePanelRef.value?.loadGuide()
  recentContextPanelRef.value?.loadContext()
})
</script>

<style scoped lang="scss">
.right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-tabs {
  display: flex;
  padding: 8px;
  gap: 6px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
  scrollbar-width: thin;
}

.panel-tab {
  flex: 1;
  min-width: max-content;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 10px;
  transition: all 0.25s ease;
  white-space: nowrap;

  i {
    font-size: 14px;
  }

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: white;
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }
}

.panel-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
