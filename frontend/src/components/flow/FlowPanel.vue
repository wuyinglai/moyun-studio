<template>
  <div class="flow-panel">
    <div class="panel-header">
      <div class="header-title">
        <i class="fa-solid fa-network-wired" />
        <span class="title-text">创作流程</span>
        <span v-if="currentView !== 'realtime'" class="title-badge">Mock</span>
        <span v-else class="title-badge realtime">实时</span>
      </div>
      <div class="header-actions">
        <button
          v-for="option in viewOptions"
          :key="option.value"
          class="view-btn"
          :class="{ active: currentView === option.value }"
          @click="currentView = option.value"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <div v-if="currentView === 'realtime' && !activeFlow" class="panel-intro">
      <p>还没有运行中的创作流程。点击写下一场景后，这里会显示 AI 的处理步骤。</p>
    </div>

    <div v-else class="panel-intro">
      <p>这是创作流程的可视化预览。点击节点可以展开查看详细信息。</p>
      <p v-if="currentView === 'realtime'" class="realtime-hint">
        <i class="fa-solid fa-circle-info" />
        此流程为前端根据现有事件推断，与实际后端执行可能不完全一致。
      </p>
    </div>

    <div v-if="currentView === 'realtime' && activeFlow" class="flow-container">
      <div class="flow-header">
        <h3>{{ activeFlow.title }}</h3>
        <p v-if="activeFlow.description" class="flow-description">{{ activeFlow.description }}</p>
      </div>
      <div class="flow-nodes">
        <div
          v-for="(node, index) in activeFlow.nodes"
          :key="node.id"
          class="node-wrapper"
        >
          <div class="node-number">{{ index + 1 }}</div>
          <FlowNodeCard :node="node" />
        </div>
      </div>
    </div>

    <div v-else-if="currentView !== 'realtime'" class="flow-container">
      <div class="flow-header">
        <h3>{{ currentFlow.title }}</h3>
        <p v-if="currentFlow.description" class="flow-description">{{ currentFlow.description }}</p>
      </div>
      <div class="flow-nodes">
        <div
          v-for="(node, index) in currentFlow.nodes"
          :key="node.id"
          class="node-wrapper"
        >
          <div class="node-number">{{ index + 1 }}</div>
          <FlowNodeCard :node="node" />
        </div>
      </div>
    </div>

    <div class="panel-footer">
      <span class="footer-hint">
        <i class="fa-solid fa-info-circle" />
        <span v-if="currentView === 'realtime'">实时模式，根据前端回调映射。</span>
        <span v-else>当前为演示模式，数据为模拟数据。</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import FlowNodeCard from './FlowNodeCard.vue'
import { mockWriteNextFlow, mockErrorFlow } from './mockFlowData'
import type { FlowRun } from './types'

interface Props {
  activeFlow?: FlowRun | null
}

const props = defineProps<Props>()

const currentView = ref<'realtime' | 'success' | 'error'>('realtime')

const viewOptions = [
  { label: '实时流程', value: 'realtime' as const },
  { label: '成功示例', value: 'success' as const },
  { label: '失败示例', value: 'error' as const },
]

const currentFlow = computed<FlowRun>(() => {
  return currentView.value === 'success' ? mockWriteNextFlow : mockErrorFlow
})
</script>

<style scoped lang="scss">
.flow-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.title-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(234, 179, 8, 0.2);
  color: var(--accent-warning);
  &.realtime {
    background: rgba(34, 197, 94, 0.2);
    color: var(--accent-success);
  }
}

.header-actions {
  display: flex;
  gap: 4px;
}

.view-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }

  &.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: white;
  }
}

.panel-intro {
  padding: 12px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);

  p {
    font-size: 12px;
    color: var(--text-secondary);
    margin: 0;
    &:not(:last-child) {
      margin-bottom: 6px;
    }
  }

  .realtime-hint {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 11px;
    color: var(--text-muted);
  }
}

.flow-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.flow-header {
  margin-bottom: 16px;
}

.flow-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px 0;
}

.flow-description {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.flow-nodes {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.node-wrapper {
  display: flex;
  gap: 8px;
  position: relative;

  &:not(:last-child)::after {
    content: '';
    position: absolute;
    left: 13px;
    top: calc(100% + 4px);
    width: 2px;
    height: 8px;
    background: var(--border-color);
  }
}

.node-number {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--bg-primary);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
  margin-top: 12px;
}

.panel-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-card);
}

.footer-hint {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 6px;

  i {
    font-size: 11px;
  }
}
</style>
