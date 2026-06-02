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
          :class="{ expanded: expanded }"
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
      <div v-if="hasInputs" class="details-section">
        <span class="section-title">
          <i class="fa-solid fa-arrow-right-to-bracket" />
          输入
        </span>
        <div class="artifacts-list">
          <template v-for="artifact in node.inputs" :key="artifact.id">
            <div
              class="artifact-item"
              @click.stop="toggleArtifactPreview(artifact.id)"
            >
              <i :class="artifactIconClass(artifact.kind)" />
              <div class="artifact-info">
                <span class="artifact-label">{{ artifact.label }}</span>
                <span v-if="artifact.path" class="artifact-path">{{ artifact.path }}</span>
              </div>
              <i class="fa-solid fa-chevron-down toggle-preview-icon" :class="{ flipped: artifactPreviewOpen === artifact.id }" />
            </div>
            <div
              v-if="artifactPreviewOpen === artifact.id"
              class="artifact-preview-wrapper"
            >
              <FlowArtifactPreview :artifact="artifact" />
            </div>
          </template>
        </div>
      </div>

      <div v-if="hasOutputs" class="details-section">
        <span class="section-title">
          <i class="fa-solid fa-arrow-right-from-bracket" />
          输出
        </span>
        <div class="artifacts-list">
          <template v-for="artifact in node.outputs" :key="artifact.id">
            <div
              class="artifact-item"
              @click.stop="toggleArtifactPreview(artifact.id)"
            >
              <i :class="artifactIconClass(artifact.kind)" />
              <div class="artifact-info">
                <span class="artifact-label">{{ artifact.label }}</span>
                <span v-if="artifact.path" class="artifact-path">{{ artifact.path }}</span>
              </div>
              <i class="fa-solid fa-chevron-down toggle-preview-icon" :class="{ flipped: artifactPreviewOpen === artifact.id }" />
            </div>
            <div
              v-if="artifactPreviewOpen === artifact.id"
              class="artifact-preview-wrapper"
            >
              <FlowArtifactPreview :artifact="artifact" />
            </div>
          </template>
        </div>
      </div>

      <div v-if="!hasInputs && !hasOutputs" class="empty-state">
        <i class="fa-solid fa-circle-info" />
        <span>该节点无输入输出信息</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import FlowArtifactPreview from './FlowArtifactPreview.vue'
import type { FlowNode } from './types'

const props = defineProps<{
  node: FlowNode
}>()

const expanded = ref(false)
const artifactPreviewOpen = ref<string | null>(null)

const hasDetails = computed(() => {
  return (props.node.inputs?.length || 0) > 0 || (props.node.outputs?.length || 0) > 0 || props.node.error
})

const hasInputs = computed(() => {
  return props.node.inputs && props.node.inputs.length > 0
})

const hasOutputs = computed(() => {
  return props.node.outputs && props.node.outputs.length > 0
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
    if (!expanded.value) {
      artifactPreviewOpen.value = null
    }
  }
}

function toggleArtifactPreview(artifactId: string) {
  if (artifactPreviewOpen.value === artifactId) {
    artifactPreviewOpen.value = null
  } else {
    artifactPreviewOpen.value = artifactId
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
  color: var(--text-muted);
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
  transition: all 0.2s;

  &.expanded {
    color: var(--accent-primary);
  }

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
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;

  i {
    font-size: 10px;
  }
}

.artifacts-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.artifact-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-hover);
  }

  i {
    font-size: 11px;
    color: var(--text-muted);
    width: 14px;
  }
}

.artifact-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.artifact-label {
  color: var(--text-primary);
  font-size: 12px;
}

.artifact-path {
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toggle-preview-icon {
  color: var(--text-muted);
  font-size: 10px;
  transition: transform 0.2s;

  &.flipped {
    transform: rotate(180deg);
  }
}

.artifact-preview-wrapper {
  margin-bottom: 8px;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-state {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--text-muted);

  i {
    font-size: 11px;
  }
}
</style>
