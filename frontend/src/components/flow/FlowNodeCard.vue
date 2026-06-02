<template>
  <div
    class="flow-node-card"
    :class="[`node-${node.type}`, `status-${node.status}`]"
    @click="toggleExpand"
  >
    <div class="node-header">
      <div class="node-type-icon">
        <i :class="typeIconClass" />
      </div>
      <div class="node-info">
        <span class="node-label">{{ node.label }}</span>
        <span v-if="node.description" class="node-description">{{ node.description }}</span>
      </div>
      <div class="node-status-wrapper">
        <span class="status-badge" :class="node.status">{{ statusLabel }}</span>
        <button
          v-if="hasDetails"
          class="expand-btn"
          @click.stop="toggleExpand"
        >
          <i :class="expanded ? 'fa-chevron-up' : 'fa-chevron-down'" />
        </button>
      </div>
    </div>

    <div v-if="node.durationMs" class="node-meta">
      <span class="duration">{{ formatDuration(node.durationMs) }}</span>
    </div>

    <div v-if="node.error" class="node-error">
      <i class="fa-solid fa-exclamation-circle" />
      <span>{{ node.error }}</span>
    </div>

    <div v-if="expanded && hasDetails" class="node-details">
      <div v-if="node.inputs?.length" class="details-section">
        <span class="section-title">输入</span>
        <div class="artifact-list">
          <div
            v-for="artifact in node.inputs"
            :key="artifact.id"
            class="artifact-item"
          >
            <i :class="artifactIconClass(artifact.kind)" />
            <span class="artifact-label">{{ artifact.label }}</span>
            <span v-if="artifact.path" class="artifact-path">{{ artifact.path }}</span>
            <span v-if="artifact.preview" class="artifact-preview" :title="artifact.preview">
              <i class="fa-solid fa-eye" />
            </span>
          </div>
        </div>
      </div>

      <div v-if="node.outputs?.length" class="details-section">
        <span class="section-title">输出</span>
        <div class="artifact-list">
          <div
            v-for="artifact in node.outputs"
            :key="artifact.id"
            class="artifact-item"
          >
            <i :class="artifactIconClass(artifact.kind)" />
            <span class="artifact-label">{{ artifact.label }}</span>
            <span v-if="artifact.path" class="artifact-path">{{ artifact.path }}</span>
            <span v-if="artifact.preview" class="artifact-preview" :title="artifact.preview">
              <i class="fa-solid fa-eye" />
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FlowNode } from './types'

const props = defineProps<{
  node: FlowNode
}>()

const expanded = ref(false)

const hasDetails = computed(() => {
  return (props.node.inputs?.length || 0) > 0 || (props.node.outputs?.length || 0) > 0 || props.node.error
})

const typeIconClass = computed(() => {
  const icons: Record<string, string> = {
    input: 'fa-solid fa-file-text',
    process: 'fa-solid fa-cog',
    llm: 'fa-solid fa-brain',
    file: 'fa-solid fa-save',
    candidate: 'fa-solid fa-copy',
    memory: 'fa-solid fa-database',
    ui: 'fa-solid fa-eye',
    quality: 'fa-solid fa-check-circle',
  }
  return icons[props.node.type] || 'fa-solid fa-circle'
})

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    pending: '等待',
    running: '运行中',
    success: '成功',
    error: '失败',
    skipped: '跳过',
  }
  return labels[props.node.status] || props.node.status
})

function artifactIconClass(kind: string): string {
  const icons: Record<string, string> = {
    file: 'fa-solid fa-file',
    text: 'fa-solid fa-align-left',
    prompt: 'fa-solid fa-message-square',
    candidate: 'fa-solid fa-copy',
    json: 'fa-solid fa-code',
  }
  return icons[kind] || 'fa-solid fa-circle'
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${((ms % 60000) / 1000).toFixed(0)}s`
}

function toggleExpand() {
  if (hasDetails.value) {
    expanded.value = !expanded.value
  }
}
</script>

<style scoped lang="scss">
.flow-node-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid var(--border-color);

  &:hover {
    background: var(--bg-hover);
  }

  &.status-success {
    border-left-color: var(--accent-success);
  }

  &.status-running {
    border-left-color: var(--accent-primary);
  }

  &.status-error {
    border-left-color: var(--accent-danger);
    background: rgba(239, 68, 68, 0.05);
  }

  &.status-skipped {
    border-left-color: var(--text-muted);
    opacity: 0.6;
  }

  &.status-pending {
    border-left-color: var(--accent-warning);
  }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.node-type-icon {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--text-secondary);
  background: var(--bg-primary);

  .node-input & {
    background: rgba(59, 130, 246, 0.1);
    color: var(--accent-primary);
  }

  .node-process & {
    background: rgba(139, 92, 246, 0.1);
    color: #8b5cf6;
  }

  .node-llm & {
    background: rgba(234, 179, 8, 0.1);
    color: var(--accent-warning);
  }

  .node-file & {
    background: rgba(34, 197, 94, 0.1);
    color: var(--accent-success);
  }

  .node-candidate & {
    background: rgba(236, 72, 153, 0.1);
    color: #ec4899;
  }

  .node-memory & {
    background: rgba(6, 182, 212, 0.1);
    color: #06b6d4;
  }

  .node-ui & {
    background: rgba(156, 163, 175, 0.1);
    color: var(--text-secondary);
  }

  .node-quality & {
    background: rgba(34, 197, 94, 0.1);
    color: var(--accent-success);
  }
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.node-description {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-status-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-muted);

  &.success {
    background: rgba(34, 197, 94, 0.2);
    color: var(--accent-success);
  }

  &.running {
    background: rgba(59, 130, 246, 0.2);
    color: var(--accent-primary);
  }

  &.error {
    background: rgba(239, 68, 68, 0.2);
    color: var(--accent-danger);
  }

  &.pending {
    background: rgba(234, 179, 8, 0.2);
    color: var(--accent-warning);
  }

  &.skipped {
    background: rgba(156, 163, 175, 0.2);
    color: var(--text-muted);
  }
}

.expand-btn {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.node-meta {
  margin-top: 6px;
  padding-left: 38px;
}

.duration {
  font-size: 11px;
  color: var(--text-muted);
}

.node-error {
  margin-top: 8px;
  padding: 8px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--accent-danger);

  i {
    font-size: 12px;
  }
}

.node-details {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.details-section {
  margin-bottom: 10px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
  display: block;
}

.artifact-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.artifact-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;

  i {
    font-size: 11px;
    color: var(--text-muted);
    width: 14px;
  }
}

.artifact-label {
  color: var(--text-primary);
  flex: 1;
}

.artifact-path {
  color: var(--text-muted);
  font-size: 11px;
  flex: 2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.artifact-preview {
  color: var(--accent-primary);
  cursor: pointer;
  font-size: 11px;

  &:hover {
    color: var(--accent-primary-dark);
  }
}
</style>