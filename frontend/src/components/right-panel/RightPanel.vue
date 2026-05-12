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
      <ExecutionPanel v-show="activeTab === 'execution'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import PromptPanel from './PromptPanel.vue'
import ExecutionPanel from './ExecutionPanel.vue'

const activeTab = ref('prompt')

const tabs = [
  { id: 'prompt', label: 'Prompt', icon: 'fa-solid fa-terminal' },
  { id: 'execution', label: '执行', icon: 'fa-solid fa-list-check' },
]
</script>

<style scoped lang="scss">
.right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.panel-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;

  i {
    font-size: 12px;
  }

  &:hover {
    color: var(--text-primary);
    background: var(--bg-card);
  }

  &.active {
    color: var(--accent-primary);
    border-bottom-color: var(--accent-primary);
  }
}

.panel-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
