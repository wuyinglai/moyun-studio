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
        <span>{{ tab.label }}</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PromptPanel from './PromptPanel.vue'
import PipelineEditor from './PipelineEditor.vue'
import WorkflowPanel from './WorkflowPanel.vue'
import ExecutionPanel from './ExecutionPanel.vue'
import StoryStatePanel from '../global/StoryStatePanel.vue'
import StyleGuidePanel from '../global/StyleGuidePanel.vue'

const activeTab = ref('prompt')

const storyPanelRef = ref<InstanceType<typeof StoryStatePanel>>()
const styleGuidePanelRef = ref<InstanceType<typeof StyleGuidePanel>>()

const tabs = [
  { id: 'prompt', label: '⚡ 快捷' },
  { id: 'pipeline', label: '🔧 管线编辑' },
  { id: 'workflow', label: '📋 工作流' },
  { id: 'story', label: '📖 故事状态' },
  { id: 'style', label: '🪶 文风' },
  { id: 'execution', label: '📋 执行' },
]

onMounted(() => {
  storyPanelRef.value?.loadState()
  styleGuidePanelRef.value?.loadGuide()
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
