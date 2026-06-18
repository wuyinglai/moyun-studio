<template>
  <div
    class="compare-modal"
    data-testid="compare-modal"
    @click.self="$emit('close')"
  >
    <div class="compare-content">
      <div class="compare-header">
        <span class="compare-title">候选稿比较</span>
        <button class="btn-close" @click="$emit('close')">
          <i class="fa-solid fa-x" />
        </button>
      </div>

      <div class="compare-notice">
        <i class="fa-solid fa-shield-halved" />
        比较视图仅用于查看差异，不会修改正文。只有点击采纳后，正文才会更新。
      </div>

      <div class="compare-labels">
        <span class="compare-label compare-label-left" :class="{ 'label-fallback': isFallback }">
          {{ leftLabel }}
        </span>
        <span class="compare-label compare-label-right">
          {{ rightLabel }}
        </span>
      </div>

      <div v-if="loading" class="compare-loading">
        <i class="fa-solid fa-spinner fa-spin" />
        加载中...
      </div>

      <div v-else class="compare-body">
        <div class="compare-diff" data-testid="compare-diff-area">
          <div
            v-for="(line, index) in diffLines"
            :key="index"
            class="diff-line"
            :class="`diff-${line.kind}`"
          >
            <span class="diff-marker">{{ diffMarker(line.kind) }}</span>
            <span class="diff-text">{{ displayText(line) }}</span>
          </div>
          <div
            v-if="diffLines.length === 0"
            class="compare-empty"
          >
            {{ emptyMessage }}
          </div>
        </div>
      </div>

      <div v-if="!loading" class="compare-summary" data-testid="compare-summary">
        <span>左侧：{{ leftChars }}字</span>
        <span>右侧：{{ rightChars }}字</span>
        <span :class="deltaClass">
          {{ deltaText }}
        </span>
        <span v-if="summary?.identical" class="summary-identical">两侧内容完全一致，无差异。</span>
      </div>

      <div class="compare-footer">
        <button class="btn-cancel" @click="$emit('close')">
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { CandidateInfo } from '@/shared/api/types'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import { useFileStore } from '@/stores/file'
import { toUserFacingMessage } from '@/utils/errorMessages'
import {
  computeLineDiff,
  computeSummary,
  candidateActionLabel,
  type CompareDiffLine,
  type CompareSummary,
} from '@/modules/candidate/compareDiff'

const props = defineProps<{
  candidate: CandidateInfo
  projectId: string
  candidates: CandidateInfo[]
}>()

defineEmits<{
  close: []
}>()

const fileStore = useFileStore()

const loading = ref(true)
const leftText = ref('')
const rightText = ref('')
const leftLabel = ref('当前正文')
const rightLabel = ref('当前候选稿')
const isFallback = ref(false)
const emptyMessage = ref('')

const diffLines = computed<CompareDiffLine[]>(() => {
  if (!leftText.value && !rightText.value) return []
  return computeLineDiff(leftText.value, rightText.value)
})

const summary = computed<CompareSummary | null>(() => {
  if (diffLines.value.length === 0) return null
  return computeSummary(leftText.value, rightText.value, diffLines.value)
})

const leftChars = computed(() => summary.value?.leftChars ?? 0)
const rightChars = computed(() => summary.value?.rightChars ?? 0)

const deltaText = computed(() => {
  if (!summary.value) return ''
  const delta = summary.value.deltaChars
  if (delta === 0) return '字数变化：无变化'
  if (delta > 0) return `字数变化：+${delta}字`
  return `字数变化：${delta}字`
})

const deltaClass = computed(() => {
  if (!summary.value) return ''
  if (summary.value.deltaChars > 0) return 'summary-positive'
  if (summary.value.deltaChars < 0) return 'summary-negative'
  return 'summary-neutral'
})

function diffMarker(kind: string): string {
  if (kind === 'added') return '+'
  if (kind === 'removed') return '−'
  if (kind === 'changed') return '~'
  return ' '
}

function displayText(line: CompareDiffLine): string {
  if (line.kind === 'removed') return line.left ?? ''
  if (line.kind === 'added') return line.right ?? ''
  if (line.kind === 'changed') return line.right ?? line.left ?? ''
  return line.left ?? ''
}

function findParentCandidate(): CandidateInfo | null {
  const parentId = props.candidate.parent_candidate_id
  if (!parentId) return null
  return props.candidates.find((c) => c.id === parentId) ?? null
}

async function fetchCandidateContent(candidateId: string): Promise<string> {
  try {
    const data = await api.get<{ content: string }>(
      `/candidates/${props.projectId}/${candidateId}`,
    )
    return data.content || ''
  } catch {
    return ''
  }
}

async function fetchSourceContent(): Promise<string> {
  try {
    const result = await fileStore.readFile(props.projectId, props.candidate.source_path)
    return result.content || ''
  } catch {
    return ''
  }
}

onMounted(async () => {
  loading.value = true
  rightLabel.value = candidateActionLabel(props.candidate.action)

  const parent = findParentCandidate()

  // Determine left source (mode B if parent exists, else mode A)
  if (parent) {
    leftLabel.value = '父候选稿'
    leftText.value = await fetchCandidateContent(parent.id)
    if (!leftText.value) {
      // Parent content missing → fallback to mode A
      leftLabel.value = '当前正文（父候选稿已删除）'
      isFallback.value = true
      leftText.value = await fetchSourceContent()
    }
  } else {
    leftLabel.value = '当前正文'
    leftText.value = await fetchSourceContent()
  }

  // Fetch right side (candidate content)
  rightText.value = await fetchCandidateContent(props.candidate.id)

  // Set empty messages
  if (!leftText.value && !rightText.value) {
    emptyMessage.value = '暂无可比较的内容。'
  } else if (!leftText.value) {
    emptyMessage.value = '暂无可比较的原文。'
  } else if (!rightText.value) {
    emptyMessage.value = '暂无候选稿内容。'
  }

  loading.value = false
})
</script>

<style scoped>
.compare-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.compare-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  width: 94%;
  max-width: 1000px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.compare-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.compare-title {
  font-weight: 600;
  color: var(--text-primary);
}

.btn-close {
  padding: 4px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
  &:hover { background: var(--bg-hover); color: var(--text-primary); }
}

.compare-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(59, 130, 246, 0.06);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  font-size: 11px;
  color: var(--accent-primary);
  line-height: 1.4;

  i { flex-shrink: 0; }
}

.compare-labels {
  display: flex;
  padding: 8px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  gap: 16px;
}

.compare-label {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  padding: 2px 0;

  &.label-fallback {
    color: var(--text-muted);
    font-style: italic;
  }
}

.compare-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 16px;
  color: var(--text-muted);
  font-size: 13px;
}

.compare-body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.compare-diff {
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
}

.diff-line {
  display: flex;
  padding: 1px 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.06);
  min-height: 20px;
}

.diff-marker {
  width: 18px;
  flex-shrink: 0;
  color: var(--text-muted);
  font-weight: 600;
  text-align: center;
  user-select: none;
}

.diff-text {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-same {
  color: var(--text-secondary);
}

.diff-added {
  background: rgba(34, 197, 94, 0.12);
  color: var(--accent-success);

  .diff-marker { color: var(--accent-success); }
}

.diff-removed {
  background: rgba(239, 68, 68, 0.10);
  color: var(--accent-danger);

  .diff-marker { color: var(--accent-danger); }
}

.diff-changed {
  background: rgba(234, 179, 8, 0.10);
  color: var(--accent-warning);

  .diff-marker { color: var(--accent-warning); }
}

.compare-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.compare-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.summary-positive { color: var(--accent-success); }
.summary-negative { color: var(--accent-danger); }
.summary-neutral { color: var(--text-muted); }
.summary-identical {
  color: var(--accent-primary);
  font-weight: 500;
}

.compare-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.btn-cancel {
  padding: 8px 16px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  &:hover { background: var(--border-color); color: var(--text-primary); }
}
</style>
