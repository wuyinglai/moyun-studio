<template>
  <div class="flow-artifact-preview">
    <div class="artifact-header">
      <i :class="artifactIconClass" />
      <span class="artifact-type-label">{{ typeLabel }}</span>
      <span v-if="artifact.isMock" class="mock-badge">Mock</span>
    </div>

    <div v-if="artifact.label" class="artifact-label">
      {{ artifact.label }}
    </div>

    <div v-if="artifact.path" class="artifact-path">
      <i class="fa-solid fa-folder" />
      <span>{{ artifact.path }}</span>
    </div>

    <div v-if="artifact.sourcePath" class="artifact-source-path">
      <i class="fa-solid fa-file-arrow-up" />
      <span>源文件: {{ artifact.sourcePath }}</span>
    </div>

    <div v-if="artifact.candidateId" class="artifact-candidate-id">
      <i class="fa-solid fa-tag" />
      <span>Candidate ID: {{ artifact.candidateId }}</span>
    </div>

    <div v-if="artifact.size" class="artifact-size">
      <i class="fa-solid fa-database" />
      <span>{{ formatSize(artifact.size) }}</span>
    </div>

    <div v-if="artifact.preview" class="artifact-preview-wrapper">
      <div class="preview-header">
        <span>预览</span>
        <button v-if="previewLength < artifact.preview.length" class="toggle-btn" @click="toggleExpand">
          {{ previewExpanded ? '收起' : '展开' }}
        </button>
      </div>
      <div class="preview-content" :class="{ expanded: previewExpanded }">
        <pre v-if="artifact.kind === 'json'">{{ formattedPreview }}</pre>
        <div v-else-if="artifact.kind === 'prompt'" class="prompt-preview">{{ formattedPreview }}</div>
        <div v-else class="text-preview">{{ formattedPreview }}</div>
      </div>
    </div>

    <div v-if="artifact.kind === 'candidate'" class="candidate-warning">
      <i class="fa-solid fa-shield-halved" />
      <span>采用前不会覆盖原文</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FlowArtifact } from './types'

const props = defineProps<{
  artifact: FlowArtifact
}>()

const previewExpanded = ref(false)
const previewLength = 300

const artifactIconClass = computed(() => {
  const icons: Record<string, string> = {
    file: 'fa-solid fa-file',
    text: 'fa-solid fa-align-left',
    prompt: 'fa-solid fa-message-square',
    candidate: 'fa-solid fa-copy',
    json: 'fa-solid fa-code',
  }
  return icons[props.artifact.kind] || 'fa-solid fa-circle'
})

const typeLabel = computed(() => {
  const labels: Record<string, string> = {
    file: '文件',
    text: '文本',
    prompt: 'Prompt',
    candidate: '候选稿',
    json: 'JSON',
  }
  return labels[props.artifact.kind] || props.artifact.kind
})

const formattedPreview = computed(() => {
  if (!props.artifact.preview) return ''
  if (previewExpanded) return props.artifact.preview
  return props.artifact.preview.slice(0, previewLength) + (props.artifact.preview.length > previewLength ? '...' : '')
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function toggleExpand() {
  previewExpanded.value = !previewExpanded.value
}
</script>

<style scoped lang="scss">
.flow-artifact-preview {
  padding: 10px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.artifact-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-color);
}

.artifact-header i {
  font-size: 12px;
  color: var(--text-muted);
}

.artifact-type-label {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 11px;
}

.mock-badge {
  font-size: 10px;
  padding: 1px 4px;
  background: rgba(234, 179, 8, 0.2);
  color: var(--accent-warning);
  border-radius: 3px;
  margin-left: auto;
}

.artifact-label {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 6px;
}

.artifact-path,
.artifact-source-path,
.artifact-candidate-id,
.artifact-size {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
  word-break: break-all;

  i {
    font-size: 10px;
  }
}

.artifact-preview-wrapper {
  margin-top: 8px;
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.toggle-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--accent-primary);
  border-radius: 4px;
  cursor: pointer;

  &:hover {
    background: var(--bg-hover);
  }
}

.preview-content {
  max-height: 100px;
  overflow-y: auto;
  background: var(--bg-primary);
  padding: 8px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  line-height: 1.5;

  &.expanded {
    max-height: 300px;
  }

  pre {
    margin: 0;
    font-family: monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .prompt-preview {
    color: var(--accent-warning);
    font-style: italic;
  }

  .text-preview {
    color: var(--text-primary);
  }
}

.candidate-warning {
  margin-top: 8px;
  padding: 6px 8px;
  background: rgba(236, 72, 153, 0.1);
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #ec4899;

  i {
    font-size: 11px;
  }
}
</style>
