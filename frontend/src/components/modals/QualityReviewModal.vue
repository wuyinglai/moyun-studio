<template>
  <a-modal
    :open="visible"
    title="质量审查"
    :width="760"
    :footer="null"
    :destroy-on-close="true"
    @cancel="close"
  >
    <div class="quality-review-modal">
      <a-form layout="vertical">
        <a-form-item label="审查文件">
          <a-input
            v-model:value="targetFile"
            placeholder="选择或输入文件路径"
          >
            <template #addonAfter>
              <a-tooltip title="使用当前文件">
                <i
                  class="fa-solid fa-file"
                  style="cursor: pointer;"
                  @click="useCurrentFile"
                />
              </a-tooltip>
            </template>
          </a-input>
        </a-form-item>
      </a-form>

      <div class="actions">
        <a-button
          :loading="isLoadingHistory"
          @click="loadHistory"
        >
          刷新历史
        </a-button>
        <a-button
          :loading="isBatchReviewing"
          :disabled="chapterFiles.length === 0"
          @click="handleBatchReview"
        >
          批量审查章节
        </a-button>
        <a-button
          type="primary"
          :loading="isReviewing"
          :disabled="!targetFile"
          @click="handleReview"
        >
          <template #icon>
            <i class="fa-solid fa-check-circle" />
          </template>
          {{ isReviewing ? '审查中...' : '审查当前文件' }}
        </a-button>
      </div>

      <a-alert
        v-if="batchSummary"
        class="batch-alert"
        type="success"
        show-icon
        :message="batchSummary"
      />

      <div
        v-if="result"
        class="result-area"
      >
        <a-divider />
        <a-alert
          type="info"
          show-icon
          class="summary-alert"
        >
          <template #message>
            <strong>{{ result.summary || '审查完成' }}</strong>
          </template>
        </a-alert>

        <div class="scores-grid">
          <div
            v-for="item in scoreItems"
            :key="item.key"
            class="score-item"
          >
            <div class="score-label">
              <span>{{ item.label }}</span>
              <span
                class="score-value"
                :class="scoreColorClass(item.value)"
              >{{ item.value }}/10</span>
            </div>
            <a-progress
              :percent="item.value * 10"
              :stroke-color="scoreColor(item.value)"
              :show-info="false"
              size="small"
            />
          </div>
        </div>

        <div
          v-if="result.issues.length > 0"
          class="section"
        >
          <h4 class="section-title">
            <i class="fa-solid fa-triangle-exclamation" />
            问题 ({{ result.issues.length }})
          </h4>
          <div
            v-for="(issue, i) in result.issues"
            :key="i"
            class="issue-item"
          >
            <a-tag
              :color="severityColor(issue.severity)"
              class="severity-tag"
            >
              {{ severityLabel(issue.severity) }}
            </a-tag>
            <span class="issue-desc">{{ issue.description }}</span>
            <span
              v-if="issue.location"
              class="issue-loc"
            >{{ issue.location }}</span>
          </div>
        </div>

        <div
          v-if="result.strengths.length > 0"
          class="section"
        >
          <h4 class="section-title">
            <i class="fa-solid fa-star" />
            优点
          </h4>
          <ul class="strength-list">
            <li
              v-for="(s, i) in result.strengths"
              :key="i"
            >
              {{ s }}
            </li>
          </ul>
        </div>

        <div
          v-if="result.suggestions.length > 0"
          class="section"
        >
          <h4 class="section-title">
            <i class="fa-solid fa-lightbulb" />
            改进建议
          </h4>
          <ul class="suggestion-list">
            <li
              v-for="(s, i) in result.suggestions"
              :key="i"
            >
              {{ s }}
            </li>
          </ul>
        </div>
      </div>

      <div
        v-else-if="error"
        class="result-area"
      >
        <a-divider />
        <a-alert
          type="error"
          show-icon
          :message="error"
        />
      </div>

      <div class="history-area">
        <a-divider />
        <div class="history-head">
          <h4>审查历史</h4>
          <span>{{ reviews.length }} 条</span>
        </div>
        <a-empty
          v-if="reviews.length === 0"
          description="暂无审查记录"
        />
        <div
          v-else
          class="history-list"
        >
          <button
            v-for="review in reviews"
            :key="review.review_id || `${review.target_file}-${review.created_at}`"
            class="history-item"
            type="button"
            @click="selectHistory(review)"
          >
            <span class="history-title">{{ review.target_file || '未知文件' }}</span>
            <span class="history-meta">
              {{ formatTime(review.created_at) }}
              <template v-if="review.result?.summary"> · {{ review.result.summary }}</template>
            </span>
          </button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useReviewStore } from '@/stores/review'
import { useNotificationStore } from '@/stores/notification'
import { useLLMStore } from '@/stores/llm'
import { useFileStore, type FileNode } from '@/stores/file'
import type { QualityReviewResult } from '@/types/chat'

interface ReviewHistoryItem {
  review_id?: string
  target_file?: string
  created_at?: string
  result?: QualityReviewResult
}

const uiStore = useUIStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const reviewStore = useReviewStore()
const notification = useNotificationStore()
const llmStore = useLLMStore()
const fileStore = useFileStore()

const visible = computed(() => uiStore.modals.qualityReview)
const currentFilePath = computed(() => editorStore.currentFilePath)

const targetFile = ref('')
const isReviewing = ref(false)
const isBatchReviewing = ref(false)
const isLoadingHistory = ref(false)
const result = ref<QualityReviewResult | null>(null)
const error = ref('')
const reviews = ref<ReviewHistoryItem[]>([])
const batchSummary = ref('')

const chapterFiles = computed(() => collectChapterFiles(fileStore.tree))

const scoreItems = computed(() => {
  if (!result.value) return []
  const s = result.value.scores
  return [
    { key: 'coherence', label: '连贯性', value: s.coherence },
    { key: 'character_consistency', label: '角色一致性', value: s.character_consistency },
    { key: 'setting_consistency', label: '设定一致性', value: s.setting_consistency },
    { key: 'writing_quality', label: '写作质量', value: s.writing_quality },
    { key: 'logic', label: '逻辑合理性', value: s.logic },
    { key: 'style_compliance', label: '文风符合度', value: s.style_compliance },
  ]
})

watch(visible, async (v) => {
  if (v) {
    targetFile.value = currentFilePath.value || ''
    isReviewing.value = false
    isBatchReviewing.value = false
    result.value = null
    error.value = ''
    batchSummary.value = ''
    await loadHistory()
  }
})

function collectChapterFiles(nodes: FileNode[]): string[] {
  const files: string[] = []
  for (const node of nodes) {
    if (node.type === 'file' && /^chapters\/.+\/sec-\d+\.md$/.test(node.path)) {
      files.push(node.path)
    }
    if (node.children?.length) {
      files.push(...collectChapterFiles(node.children))
    }
  }
  return files
}

function useCurrentFile() {
  if (currentFilePath.value) {
    targetFile.value = currentFilePath.value
  }
}

async function loadHistory() {
  if (!projectStore.currentProject) return
  isLoadingHistory.value = true
  try {
    const data = await reviewStore.listReviews(projectStore.currentProject.id)
    reviews.value = (data.reviews || []) as ReviewHistoryItem[]
  } catch {
    reviews.value = []
  } finally {
    isLoadingHistory.value = false
  }
}

async function handleReview() {
  if (!projectStore.currentProject || !targetFile.value) return
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    return
  }

  isReviewing.value = true
  result.value = null
  error.value = ''
  batchSummary.value = ''

  try {
    const res = await reviewStore.reviewChapter({
      project_id: projectStore.currentProject.id,
      target_file: targetFile.value,
    })
    result.value = res.result
    notification.success('审查完成')
    await loadHistory()
  } catch (e: any) {
    error.value = e?.message || '审查失败'
    notification.error('审查失败')
  } finally {
    isReviewing.value = false
  }
}

async function handleBatchReview() {
  if (!projectStore.currentProject || chapterFiles.value.length === 0) return
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    return
  }

  isBatchReviewing.value = true
  batchSummary.value = ''
  error.value = ''

  try {
    const res = await reviewStore.reviewBatch({
      project_id: projectStore.currentProject.id,
      target_files: chapterFiles.value,
    })
    batchSummary.value = `批量审查完成：成功 ${res.succeeded}，失败 ${res.failed}，共 ${res.total} 个章节。`
    notification.success('批量审查完成')
    await loadHistory()
  } catch (e: any) {
    error.value = e?.message || '批量审查失败'
    notification.error('批量审查失败')
  } finally {
    isBatchReviewing.value = false
  }
}

function selectHistory(review: ReviewHistoryItem) {
  if (review.target_file) {
    targetFile.value = review.target_file
  }
  if (review.result) {
    result.value = review.result
    error.value = ''
  }
}

function formatTime(value?: string) {
  if (!value) return '未知时间'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function scoreColor(score: number): string {
  if (score >= 8) return '#52c41a'
  if (score >= 5) return '#faad14'
  return '#ff4d4f'
}

function scoreColorClass(score: number): string {
  if (score >= 8) return 'score-high'
  if (score >= 5) return 'score-mid'
  return 'score-low'
}

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'red'
    case 'major': return 'orange'
    case 'minor': return 'blue'
    default: return 'default'
  }
}

function severityLabel(severity: string): string {
  switch (severity) {
    case 'critical': return '严重'
    case 'major': return '主要'
    case 'minor': return '轻微'
    default: return severity
  }
}

function close() {
  uiStore.closeQualityReview()
}
</script>

<style scoped lang="scss">
.quality-review-modal {
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-bottom: 8px;
  }

  .batch-alert {
    margin-top: 12px;
  }

  .result-area {
    margin-top: 8px;
  }

  .summary-alert {
    margin-bottom: 16px;
  }

  .scores-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
    padding: 16px;
    background: var(--bg-card);
    border-radius: var(--radius-md);
  }

  .score-item {
    .score-label {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: var(--text-primary);
      margin-bottom: 4px;
    }

    .score-value {
      font-weight: 600;

      &.score-high { color: var(--accent-success); }
      &.score-mid { color: var(--accent-warning); }
      &.score-low { color: var(--accent-danger); }
    }
  }

  .section {
    margin-bottom: 16px;

    .section-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
  }

  .issue-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 12px;
    margin-bottom: 6px;
    background: var(--bg-primary);
    border-radius: var(--radius-sm);
    font-size: 13px;

    .severity-tag {
      flex-shrink: 0;
      margin-right: 4px;
    }

    .issue-desc {
      flex: 1;
      color: var(--text-primary);
    }

    .issue-loc {
      font-size: 11px;
      color: var(--text-muted);
      flex-shrink: 0;
    }
  }

  .strength-list,
  .suggestion-list {
    padding-left: 20px;
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.8;
  }

  .history-area {
    margin-top: 8px;
  }

  .history-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;

    h4 {
      margin: 0;
      font-size: 14px;
      color: var(--text-primary);
    }

    span {
      font-size: 12px;
      color: var(--text-muted);
    }
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 180px;
    overflow: auto;
  }

  .history-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 12px;
    text-align: left;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    cursor: pointer;
  }

  .history-title {
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 600;
  }

  .history-meta {
    color: var(--text-muted);
    font-size: 12px;
  }
}
</style>
