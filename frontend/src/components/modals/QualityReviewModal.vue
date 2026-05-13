<template>
  <a-modal
    :open="visible"
    title="质量审查"
    :width="640"
    @cancel="close"
    :footer="null"
    :destroy-on-close="true"
  >
    <div class="quality-review-modal">
      <!-- 选择文件 -->
      <a-form layout="vertical">
        <a-form-item label="审查文件">
          <a-input v-model:value="targetFile" placeholder="选择或输入文件路径">
            <template #addonAfter>
              <a-tooltip title="使用当前文件">
                <i class="fa-solid fa-file" style="cursor: pointer;" @click="useCurrentFile" />
              </a-tooltip>
            </template>
          </a-input>
        </a-form-item>
      </a-form>

      <!-- 操作按钮 -->
      <div class="actions">
        <a-button @click="close">关闭</a-button>
        <a-button type="primary" :loading="isReviewing" :disabled="!targetFile" @click="handleReview">
          <template #icon><i class="fa-solid fa-check-circle"></i></template>
          {{ isReviewing ? '审查中...' : '开始审查' }}
        </a-button>
      </div>

      <!-- 审查结果 -->
      <div v-if="result" class="result-area">
        <a-divider />

        <!-- 总体评价 -->
        <a-alert type="info" show-icon class="summary-alert">
          <template #message>
            <strong>{{ result.summary || '审查完成' }}</strong>
          </template>
        </a-alert>

        <!-- 评分面板 -->
        <div class="scores-grid">
          <div v-for="item in scoreItems" :key="item.key" class="score-item">
            <div class="score-label">
              <span>{{ item.label }}</span>
              <span class="score-value" :class="scoreColorClass(item.value)">{{ item.value }}/10</span>
            </div>
            <a-progress
              :percent="item.value * 10"
              :stroke-color="scoreColor(item.value)"
              :show-info="false"
              size="small"
            />
          </div>
        </div>

        <!-- 问题列表 -->
        <div v-if="result.issues.length > 0" class="section">
          <h4 class="section-title">
            <i class="fa-solid fa-triangle-exclamation"></i>
            问题 ({{ result.issues.length }})
          </h4>
          <div v-for="(issue, i) in result.issues" :key="i" class="issue-item">
            <a-tag :color="severityColor(issue.severity)" class="severity-tag">
              {{ severityLabel(issue.severity) }}
            </a-tag>
            <span class="issue-desc">{{ issue.description }}</span>
            <span v-if="issue.location" class="issue-loc">{{ issue.location }}</span>
          </div>
        </div>

        <!-- 优点 -->
        <div v-if="result.strengths.length > 0" class="section">
          <h4 class="section-title">
            <i class="fa-solid fa-star"></i>
            优点
          </h4>
          <ul class="strength-list">
            <li v-for="(s, i) in result.strengths" :key="i">{{ s }}</li>
          </ul>
        </div>

        <!-- 改进建议 -->
        <div v-if="result.suggestions.length > 0" class="section">
          <h4 class="section-title">
            <i class="fa-solid fa-lightbulb"></i>
            改进建议
          </h4>
          <ul class="suggestion-list">
            <li v-for="(s, i) in result.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>

      <!-- 错误 -->
      <div v-else-if="error" class="result-area">
        <a-divider />
        <a-alert type="error" show-icon :message="error" />
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useNotificationStore } from '@/stores/notification'
import type { QualityReviewResult } from '@/types/chat'

const uiStore = useUIStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.qualityReview)

const targetFile = ref('')
const isReviewing = ref(false)
const result = ref<QualityReviewResult | null>(null)
const error = ref('')

const currentFilePath = computed(() => editorStore.currentFilePath)

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

watch(visible, (v) => {
  if (v) {
    targetFile.value = currentFilePath.value || ''
    isReviewing.value = false
    result.value = null
    error.value = ''
  }
})

function useCurrentFile() {
  if (currentFilePath.value) {
    targetFile.value = currentFilePath.value
  }
}

async function handleReview() {
  if (!projectStore.currentProject || !targetFile.value) return

  isReviewing.value = true
  result.value = null
  error.value = ''

  try {
    const res = await fileStore.reviewChapter({
      project_id: projectStore.currentProject.id,
      target_file: targetFile.value,
    })
    result.value = res.result
    notification.success('审查完成')
  } catch (e: any) {
    error.value = e?.message || '审查失败'
    notification.error('审查失败')
  } finally {
    isReviewing.value = false
  }
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

  .strength-list, .suggestion-list {
    padding-left: 20px;
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.8;
  }
}
</style>
