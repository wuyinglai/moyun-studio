<template>
  <!-- 这是一个示例组件，展示如何扩展右侧面板
  <!-- 不会修改现有代码，仅作参考
  <div class="right-panel-enhanced">
    <!-- Tab 切换 -->
    <div class="panel-tabs-enhanced">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="panel-tab-enhanced"
        :class="{ active: activeTab === tab.id"
        @click="activeTab = tab.id"
      >
        <i :class="tab.icon"></i>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- 内容区域 -->
    <div class="panel-content-enhanced">
      <!-- Prompt 面板 -->
      <div v-show="activeTab === 'prompt'" class="tab-content">
        <PromptPanel />
      </div>

      <!-- 故事状态面板 (已存在但未整合) -->
      <div v-show="activeTab === 'story'" class="tab-content">
        <StoryStatePanel />
      </div>

      <!-- 文风指南面板 (已存在但未整合) -->
      <div v-show="activeTab === 'style'" class="tab-content">
        <StyleGuidePanel />
      </div>

      <!-- 近期上下文面板 (已存在但未整合) -->
      <div v-show="activeTab === 'context'" class="tab-content">
        <RecentContextPanel />
      </div>

      <!-- 执行面板 -->
      <div v-show="activeTab === 'execution'" class="tab-content">
        <ExecutionPanel />
      </div>

      <!-- 历史记录面板 (已存在但未整合) -->
      <div v-show="activeTab === 'history'" class="tab-content">
        <HistoryPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/*
这是一个示例文件，展示了如何扩展现有的功能
不会实际使用，仅为设计参考
*/
import { ref } from 'vue'
import PromptPanel from './right-panel/PromptPanel.vue'
import ExecutionPanel from './right-panel/ExecutionPanel.vue'

// 这些组件需要创建或从现有代码中整合：
// import StoryStatePanel from './global/StoryStatePanel.vue'
// import StyleGuidePanel from './global/StyleGuidePanel.vue'
// import RecentContextPanel from './global/RecentContextPanel.vue'
// import HistoryPanel from './global/HistoryPanel.vue'

const activeTab = ref('prompt')

const tabs = [
  { id: 'prompt', label: '提示词', icon: 'fa-solid fa-terminal' },
  { id: 'story', label: '故事状态', icon: 'fa-solid fa-book-open' },
  { id: 'style', label: '文风指南', icon: 'fa-solid fa-feather' },
  { id: 'context', label: '上下文', icon: 'fa-solid fa-clock-rotate-left' },
  { id: 'execution', label: '执行', icon: 'fa-solid fa-list-check' },
  { id: 'history', label: '历史', icon: 'fa-solid fa-history' }
]
</script>

<style scoped lang="scss">
/* 新设计的 Tab 样式示例 */
.right-panel-enhanced {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

.panel-tabs-enhanced {
  display: flex;
  padding: 8px;
  gap: 6px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
  scrollbar-width: thin;
}

.panel-tab-enhanced {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;

  i {
    font-size: 14px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    color: white;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }
}

.panel-content-enhanced {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-content {
  height: 100%;
  overflow-y: auto;
}
</style>

<!--
设计说明：

这个示例展示了如何充分利用已有的代码库：
1. stores/storyState.ts      → 故事状态
2. stores/styleGuide.ts   → 文风指南
3. stores/recentContext.ts → 近期上下文
4. stores/revisionLog.ts   → 历史记录

这些功能已经在代码中实现，但没有 UI 面板还没有完全整合到主界面

可以为这些功能创建简单的面板组件，然后通过这个新的 Tab 系统来展示

-->
