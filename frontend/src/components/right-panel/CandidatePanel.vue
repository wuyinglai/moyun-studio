<template>
  <div
    class="candidate-panel"
    data-testid="candidate-panel"
  >
    <div class="panel-header">
      <span class="panel-title">候选稿</span>
      <button
        class="btn-refresh"
        :disabled="loading"
        @click="refreshCandidates"
      >
        <i class="fa-solid fa-rotate" />
      </button>
    </div>

    <div class="candidate-notice">
      <i class="fa-solid fa-circle-info" />
      候选稿不会自动覆盖正文。你可以先预览，再决定是否采用。
    </div>

    <!-- 候选稿列表 -->
    <div
      v-if="candidates.length === 0"
      class="empty-state"
    >
      <i class="fa-solid fa-file-text" />
      <span>{{ loading ? '加载中...' : '暂无候选稿' }}</span>
    </div>

    <div
      v-else
      class="candidate-list"
    >
      <div
        v-for="candidate in candidates"
        :key="candidate.id"
        class="candidate-card"
        :class="{ active: selectedId === candidate.id }"
        @click="selectCandidate(candidate)"
      >
        <div class="card-header">
          <span class="candidate-action" :class="`action-${candidate.action}`">
            {{ actionLabel(candidate.action) }}
          </span>
          <span
            v-if="candidate.source_type"
            class="source-type-badge"
            :class="`source-${candidate.source_type}`"
          >
            {{ candidate.source_type === 'dry-run' ? '模拟运行' : 'AI 生成' }}
          </span>
          <span class="candidate-status" :class="`status-${candidate.status}`">
            {{ statusLabel(candidate.status) }}
          </span>
        </div>
        <!-- Quality Summary - MVP 3 dimensions -->
        <div
          v-if="candidate.quality"
          class="quality-summary"
          data-testid="candidate-quality-summary"
        >
          <span
            class="quality-badge"
            :class="qualityBadgeClass(candidate.quality.instruction_following)"
            :title="`指令遵守: ${candidate.quality.instruction_following}`"
          >
            <i :class="qualityBadgeIcon(candidate.quality.instruction_following)" />
            {{ qualityLabel('instruction', candidate.quality.instruction_following) }}
          </span>
          <span
            class="quality-badge"
            :class="qualityBadgeClass(candidate.quality.continuity)"
            :title="`连续性: ${candidate.quality.continuity}`"
          >
            <i :class="qualityBadgeIcon(candidate.quality.continuity)" />
            {{ qualityLabel('continuity', candidate.quality.continuity) }}
          </span>
          <span
            class="quality-badge quality-badge-scope"
            :class="scopeBadgeClass(candidate.quality.change_scope)"
            :title="`改动幅度: ${candidate.quality.change_scope}`"
          >
            <i :class="scopeBadgeIcon(candidate.quality.change_scope)" />
            {{ candidate.quality.change_scope }}
          </span>
        </div>
        <!-- T10.1 Quality Explanation Collapsible Area -->
        <div
          class="quality-explanation"
          data-testid="candidate-quality-explanation"
        >
          <button
            class="quality-explanation-toggle"
            :aria-expanded="isQualityExpanded(candidate)"
            data-testid="candidate-quality-explanation-toggle"
            @click.stop="toggleQualityExpanded(candidate.id)"
          >
            <i :class="isQualityExpanded(candidate) ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" />
            <span>{{ getQualityExplanation(candidate).collapsedText }}</span>
          </button>
          <div
            v-if="isQualityExpanded(candidate)"
            class="quality-explanation-body"
            data-testid="candidate-quality-explanation-body"
          >
            <div
              v-if="getQualityExplanation(candidate).dimensions.length === 0"
              class="quality-explanation-empty"
              data-testid="candidate-quality-explanation-empty"
            >
              当前候选稿没有质量解释数据。
            </div>
            <div
              v-for="dim in getQualityExplanation(candidate).dimensions"
              :key="dim.key"
              class="quality-dimension"
              :data-testid="`quality-dimension-${dim.key}`"
            >
              <div class="quality-dimension-header">
                <span class="quality-dimension-label">{{ dim.label }}</span>
                <span class="quality-dimension-status" :class="dim.cssClass">{{ dim.statusLabel }}</span>
              </div>
              <div class="quality-dimension-description">{{ dim.description }}</div>
            </div>
            <!-- Repair explanation (T10.1a §9) -->
            <div
              v-if="showRepairExplanation(candidate)"
              class="quality-repair-explanation"
              data-testid="candidate-repair-explanation"
            >
              <i class="fa-solid fa-bandaid" />
              <div>
                <strong>修复候选稿</strong>
                <span>{{ getRepairExplanation(candidate) }}</span>
                <span class="quality-repair-note">修复会生成新的候选稿，不会自动采纳，也不会覆盖正文。</span>
              </div>
            </div>
            <!-- Candidate-only safety text (T10.1a §10) -->
            <div
              class="quality-safety-text"
              data-testid="candidate-safety-text"
            >
              <i class="fa-solid fa-shield-halved" />
              {{ candidateSafetyText }}
            </div>
          </div>
        </div>
        <!-- 质量检查区 -->
        <div
          v-if="hasQualityInfo(candidate)"
          class="card-quality"
          data-testid="candidate-quality-section"
        >
          <div
            v-if="candidate.beat_validation && candidate.beat_validation.status === 'pass'"
            class="quality-item quality-pass"
          >
            <i class="fa-solid fa-circle-check" />
            <span>信息点检查通过</span>
          </div>
          <div
            v-if="candidate.beat_validation && candidate.beat_validation.status === 'warning'"
            class="quality-item quality-warning"
          >
            <i class="fa-solid fa-triangle-exclamation" />
            <span>信息点有警告</span>
          </div>
          <div
            v-if="candidate.beat_validation && candidate.beat_validation.status === 'unknown'"
            class="quality-item quality-unknown"
          >
            <i class="fa-solid fa-circle-question" />
            <span>信息点未确认 — 不影响采用，请预览确认</span>
          </div>
          <div
            v-if="candidate.continuity && candidate.continuity.has_warning"
            class="quality-item quality-continuity"
            :class="`continuity-${candidate.continuity.severity || 'medium'}`"
          >
            <i class="fa-solid fa-triangle-exclamation" />
            <span>连续性警告</span>
          </div>
          <div
            v-if="continuityAnchorUsedCount(candidate) > 0"
            class="quality-item quality-anchor"
            data-testid="candidate-continuity-anchor-count"
          >
            <i class="fa-solid fa-link" />
            <span>连续性锚点：已使用 {{ continuityAnchorUsedCount(candidate) }} 条</span>
          </div>
          <div
            v-if="candidate.warning_message"
            class="quality-detail quality-warning-detail"
          >
            <i class="fa-solid fa-circle-info" />
            {{ candidate.warning_message }}
          </div>
          <div
            v-else-if="candidate.continuity && candidate.continuity.has_warning && candidate.continuity.anchors_missing && candidate.continuity.anchors_missing.length > 0"
            class="quality-detail quality-continuity-detail"
          >
            <i class="fa-solid fa-circle-info" />
            可能与前文设定不一致：缺少「{{ candidate.continuity.anchors_missing.slice(0, 3).join('、') }}」等关键元素，建议先预览再采纳。
          </div>
          <div
            v-if="beatValidationMessage(candidate)"
            class="quality-detail candidate-warning-message"
            :class="`beat-message-${candidate.beat_validation?.status || 'unknown'}`"
          >
            <i :class="beatValidationIcon(candidate)" />
            <div class="beat-message-content">
              <strong>{{ beatValidationMessage(candidate) }}</strong>
              <ul
                v-if="beatValidationDetails(candidate).length > 0"
                class="beat-detail-list"
              >
                <li
                  v-for="detail in beatValidationDetails(candidate)"
                  :key="detail"
                >
                  {{ detail }}
                </li>
              </ul>
            </div>
          </div>
        </div>
        <!-- 修订来源区 -->
        <div
          v-if="isFeedbackRevision(candidate)"
          class="card-revision"
          data-testid="candidate-revision-section"
        >
          <div
            class="candidate-revision-summary"
            data-testid="candidate-revision-summary"
          >
            <i class="fa-solid fa-code-branch" />
            <div>
              <strong>反馈修订稿 · 第 {{ revisionIndexLabel(candidate) }} 版</strong>
              <span v-if="revisionParentLabel(candidate)">来自 {{ revisionParentLabel(candidate) }}</span>
              <span v-if="revisionFeedbackSummary(candidate)">反馈：{{ revisionFeedbackSummary(candidate) }}</span>
            </div>
          </div>
        </div>
        <div
          class="card-body"
          data-testid="candidate-content"
        >
          <div class="candidate-filename">{{ candidate.source_filename }}</div>
          <div class="candidate-meta">
            <span class="meta-item">{{ formatTime(candidate.created_at) }}</span>
            <span class="meta-item">{{ candidate.word_count }} 字</span>
          </div>
        </div>
        <div class="card-actions">
          <div class="card-actions-primary">
            <button
              class="action-btn"
              title="预览"
              @click.stop="previewCandidate(candidate)"
            >
              <i class="fa-solid fa-eye" />
            </button>
            <button
              class="action-btn"
              title="比较差异"
              data-testid="candidate-compare-button"
              @click.stop="openCompare(candidate)"
            >
              <i class="fa-solid fa-code-compare" />
            </button>
            <button
              v-if="candidate.status === 'pending'"
              class="action-btn action-adopt"
              title="采用"
              data-testid="candidate-adopt-button"
              @click.stop="adoptCandidate(candidate)"
            >
              <i class="fa-solid fa-check" />
            </button>
            <button
              class="action-btn action-delete"
              title="删除"
              data-testid="candidate-reject-button"
              @click.stop="deleteCandidate(candidate)"
            >
              <i class="fa-solid fa-trash-can" />
            </button>
          </div>
          <button
            v-if="candidate.status === 'pending'"
            class="action-btn action-revise"
            title="按反馈再生成"
            data-testid="candidate-revise-button"
            @click.stop="openRevisionModal(candidate)"
          >
            <i class="fa-solid fa-wand-magic-sparkles" />
            <span class="action-revise-label">按反馈再生成</span>
          </button>
          <!-- 修复候选稿按钮：仅 pending 且有警告时显示 -->
          <button
            v-if="candidate.status === 'pending' && hasRepairableWarning(candidate)"
            class="action-btn action-repair"
            title="基于警告修复候选稿"
            data-testid="candidate-repair-button"
            @click.stop="repairCandidate(candidate)"
          >
            <i class="fa-solid fa-bandaid" />
            <span class="action-repair-label">修复候选稿</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <div
      v-if="previewing"
      class="preview-modal"
      @click.self="closePreview"
    >
      <div class="preview-content">
        <div class="preview-header">
          <span class="preview-title">预览候选稿</span>
          <button class="btn-close" @click="closePreview">
            <i class="fa-solid fa-x" />
          </button>
        </div>
        <div class="preview-notice">
          <i class="fa-solid fa-circle-info" />
          预览只用于查看内容，不会修改正文。
        </div>
        <div class="preview-meta">
          <span class="meta-label">源文件:</span>
          <span class="meta-value">{{ previewCandidateInfo?.source_filename }}</span>
          <span class="meta-label">动作:</span>
          <span class="meta-value action-badge" :class="`action-${previewCandidateInfo?.action}`">
            {{ actionLabel(previewCandidateInfo?.action || '') }}
          </span>
          <span
            v-if="previewCandidateInfo?.source_type"
            class="meta-value source-type-badge"
            :class="`source-${previewCandidateInfo?.source_type}`"
          >
            {{ previewCandidateInfo.source_type === 'dry-run' ? '模拟运行' : 'AI 生成' }}
          </span>
        </div>
        <div
          v-if="getPreviewWarning(previewCandidateInfo)"
          class="preview-warning"
        >
          <i class="fa-solid fa-triangle-exclamation" />
          {{ getPreviewWarning(previewCandidateInfo) }}
        </div>
        <div class="preview-body">
          <textarea
            v-model="previewContent"
            readonly
            class="preview-textarea"
            placeholder="加载中..."
          />
        </div>
        <div class="preview-footer">
          <button
            v-if="previewCandidateInfo?.status === 'pending'"
            class="btn-adopt"
            @click="adoptFromPreview"
          >
            <i class="fa-solid fa-check" /> 采用候选稿
          </button>
          <button class="btn-cancel" @click="closePreview">
            关闭
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="revisioning"
      class="revision-modal"
      @click.self="closeRevisionModal"
    >
      <div class="revision-content">
        <div class="revision-header">
          <span class="revision-title">按反馈再生成</span>
          <button
            class="btn-close"
            :disabled="revisionSubmitting"
            @click="closeRevisionModal"
          >
            <i class="fa-solid fa-x" />
          </button>
        </div>
        <div class="revision-notice">
          <i class="fa-solid fa-shield-halved" />
          告诉 AI 你想怎么改这个候选稿。新内容会作为新的候选稿生成，不会覆盖正文。
        </div>
        <div class="revision-parent">
          <span>父候选稿</span>
          <strong>{{ revisionParent?.id }}</strong>
          <em>{{ revisionParent ? actionLabel(revisionParent.action) : '' }}</em>
        </div>
        <div
          v-if="beatValidationMessage(revisionParent)"
          class="revision-parent-warning"
        >
          <i :class="beatValidationIcon(revisionParent)" />
          {{ beatValidationMessage(revisionParent) }}
        </div>
        <div
          v-if="revisionBeatCounts.total > 0"
          class="revision-parent-beats"
          data-testid="candidate-revision-beat-inheritance"
        >
          <i class="fa-solid fa-list-check" />
          将继续检查 {{ revisionBeatCounts.required }} 个必须信息点、{{ revisionBeatCounts.forbidden }} 个禁止项。
        </div>
        <div class="revision-quick-actions">
          <span>快捷反馈</span>
          <button
            v-for="action in revisionQuickActionOptions"
            :key="action.value"
            type="button"
            :class="{ active: revisionQuickActions.includes(action.value) }"
            :disabled="revisionSubmitting"
            @click="toggleRevisionQuickAction(action.value)"
          >
            {{ action.label }}
          </button>
        </div>
        <label class="revision-field">
          <span>告诉 AI 你想怎么改</span>
          <textarea
            v-model="revisionFeedback"
            data-testid="candidate-revision-feedback"
            rows="5"
            :disabled="revisionSubmitting"
            maxlength="1000"
            placeholder="例如：补上缺失信息点；保留开头，只改结尾；不要新增人物或组织；加强冲突但保持原文风格。"
          />
          <small
            class="revision-length-hint"
            :class="{ warning: revisionFeedbackLength > 900 }"
          >
            {{ revisionFeedbackLength }}/1000。反馈越具体，新候选稿越容易沿着你的意图修。
          </small>
        </label>
        <label class="revision-field">
          <span>修改范围</span>
          <select
            v-model="revisionScope"
            :disabled="revisionSubmitting"
          >
            <option value="full_candidate">整个候选稿</option>
            <option value="keep_opening">保留开头</option>
            <option value="ending_only">只改结尾</option>
          </select>
        </label>
        <div class="revision-footer">
          <button
            class="btn-cancel"
            :disabled="revisionSubmitting"
            @click="closeRevisionModal"
          >
            取消
          </button>
          <button
            class="btn-revision-submit"
            data-testid="candidate-revision-submit"
            :disabled="revisionSubmitting || !canSubmitRevision"
            @click="submitRevision"
          >
            <i class="fa-solid fa-wand-magic-sparkles" />
            {{ revisionSubmitting ? '生成中...' : '生成新候选稿' }}
          </button>
        </div>
      </div>
    </div>

    <!-- T10.2 Compare Modal -->
    <CompareModal
      v-if="comparing && compareCandidateInfo"
      :candidate="compareCandidateInfo"
      :project-id="projectStore.currentProject?.id || ''"
      :candidates="candidates"
      @close="closeCompare"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import { useFileStore, type FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useSSE } from '@/composables/useSSE'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { CandidateAdoptResult, CandidateInfo, CandidateRevisionRequest } from '@/shared/api/types'
import { getApiErrorCode, toUserFacingMessage } from '@/utils/errorMessages'
import {
  buildQualityExplanation,
  shouldShowRepairExplanation,
  repairExplanation,
  CANDIDATE_SAFETY_TEXT,
  type QualityExplanationSummary,
} from '@/modules/candidate/qualityExplanation'
import CompareModal from './CompareModal.vue'

const projectStore = useProjectStore()
const notification = useNotificationStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const sse = useSSE()

const candidates = ref<CandidateInfo[]>([])
const loading = ref(false)
const selectedId = ref<string | null>(null)
const previewing = ref(false)
const previewCandidateInfo = ref<CandidateInfo | null>(null)
const previewContent = ref('')
const revisioning = ref(false)
const revisionParent = ref<CandidateInfo | null>(null)
const revisionFeedback = ref('')
const revisionQuickActions = ref<string[]>([])
const revisionScope = ref<'full_candidate' | 'keep_opening' | 'ending_only'>('full_candidate')
const revisionSubmitting = ref(false)
const comparing = ref(false)
const compareCandidateInfo = ref<CandidateInfo | null>(null)
let disposeCandidateCreated: (() => void) | null = null
let disposeCandidateAdopted: (() => void) | null = null
const expandedQuality = ref<Set<string>>(new Set())

function toggleQualityExpanded(id: string) {
  const next = new Set(expandedQuality.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedQuality.value = next
}

function getQualityExplanation(candidate: CandidateInfo): QualityExplanationSummary {
  return buildQualityExplanation(candidate)
}

function isQualityExpanded(candidate: CandidateInfo): boolean {
  return expandedQuality.value.has(candidate.id)
}

function showRepairExplanation(candidate: CandidateInfo): boolean {
  return shouldShowRepairExplanation(candidate)
}

function getRepairExplanation(candidate: CandidateInfo): string {
  return repairExplanation(candidate)
}

const candidateSafetyText = CANDIDATE_SAFETY_TEXT

const revisionQuickActionOptions = [
  { value: 'fix_missing_beats', label: '补上缺失信息点' },
  { value: 'avoid_new_entities', label: '不要新增人物' },
  { value: 'keep_style', label: '保持原文风格' },
  { value: 'increase_conflict', label: '加强冲突' },
  { value: 'reduce_exposition', label: '减少解释' },
  { value: 'enhance_imagery', label: '增强画面感' },
]

const revisionFeedbackLength = computed(() => revisionFeedback.value.length)
const canSubmitRevision = computed(() => (
  revisionFeedback.value.trim().length > 0 || revisionQuickActions.value.length > 0
) && revisionFeedbackLength.value <= 1000)

const revisionBeatCounts = computed(() => getInheritedBeatCounts(revisionParent.value))

function hasQualityInfo(candidate: CandidateInfo): boolean {
  const bv = candidate.beat_validation
  const hasBeatValidation = !!bv && !!bv.status
  const hasContinuity = !!(candidate.continuity && candidate.continuity.has_warning)
  const hasContinuityAnchors = continuityAnchorUsedCount(candidate) > 0
  const hasWarningMsg = !!candidate.warning_message
  return hasBeatValidation || hasContinuity || hasContinuityAnchors || hasWarningMsg
}

function continuityAnchorUsedCount(candidate: CandidateInfo | null): number {
  const raw = candidate?.continuity_anchors?.used_count
  const count = Number(raw || 0)
  return Number.isFinite(count) ? count : 0
}

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    rewrite: '重写',
    continue: '续写',
    modify: '修改',
    chat: '聊天改稿',
    expand: '扩写',
    shrink: '缩写',
    polish: '润色',
    repair: '修复版',
    fallback_draft: '备用草稿',
    feedback_revision: '反馈再生成',
  }
  return labels[action] || action
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '待处理',
    adopted: '已采用',
    discarded: '已放弃',
  }
  return labels[status] || status
}

function qualityBadgeClass(value: string): string {
  if (value === 'pass') return 'badge-pass'
  if (value === 'warning') return 'badge-warning'
  return 'badge-unknown'
}

function qualityBadgeIcon(value: string): string {
  if (value === 'pass') return 'fa-solid fa-check'
  if (value === 'warning') return 'fa-solid fa-exclamation'
  return 'fa-solid fa-question'
}

function qualityLabel(type: 'instruction' | 'continuity', value: string): string {
  if (type === 'instruction') {
    if (value === 'pass') return '指令✓'
    if (value === 'warning') return '指令⚠'
    return '指令?'
  }
  if (type === 'continuity') {
    if (value === 'pass') return '连续✓'
    return '连续?'
  }
  return value
}

function scopeBadgeClass(value: string): string {
  if (value === 'small') return 'badge-pass'
  if (value === 'medium') return 'badge-warning'
  if (value === 'large') return 'badge-danger'
  return 'badge-unknown'
}

function scopeBadgeIcon(value: string): string {
  if (value === 'small') return 'fa-solid fa-minus'
  if (value === 'medium') return 'fa-solid fa-equals'
  if (value === 'large') return 'fa-solid fa-plus'
  return 'fa-solid fa-question'
}

function formatTime(timeStr: string): string {
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return timeStr
  }
}

async function fetchCandidates(silent = false) {
  if (!projectStore.currentProject?.id) return
  
  loading.value = true
  try {
    const data = await api.get<{ candidates: CandidateInfo[] }>(`/candidates/${projectStore.currentProject.id}`)
    candidates.value = data.candidates.map((c: CandidateInfo) => ({
      ...c,
      source_filename: c.source_path.split('/').pop() || c.source_path,
      filename: c.candidate_path.split('/').pop() || c.candidate_path,
    }))
  } catch (error: unknown) {
    if (!silent) {
      notification.error(toUserFacingMessage(error, '获取候选稿列表失败'))
    }
  } finally {
    loading.value = false
  }
}

function refreshCandidates() {
  fetchCandidates(false)
}

function selectCandidate(candidate: CandidateInfo) {
  selectedId.value = candidate.id
}

async function previewCandidate(candidate: CandidateInfo) {
  previewCandidateInfo.value = candidate
  previewing.value = true
  previewContent.value = ''
  
  try {
    const data = await api.get<{ content: string }>(`/candidates/${projectStore.currentProject?.id}/${candidate.id}`)
    previewContent.value = data.content || ''
  } catch (error: unknown) {
    notification.error(toUserFacingMessage(error, '获取候选稿内容失败'))
    closePreview()
  }
}

function closePreview() {
  previewing.value = false
  previewCandidateInfo.value = null
  previewContent.value = ''
}

function openCompare(candidate: CandidateInfo) {
  compareCandidateInfo.value = candidate
  comparing.value = true
}

function closeCompare() {
  comparing.value = false
  compareCandidateInfo.value = null
}

async function syncAdoptedSource(sourcePath: string) {
  const projectId = projectStore.currentProject?.id
  if (!projectId || !sourcePath) return

  fileStore.refreshTree()
  if (editorStore.currentFilePath === sourcePath) {
    const latest = await fileStore.readFile(projectId, sourcePath)
    const node: FileNode = {
      name: sourcePath.split('/').pop() || sourcePath,
      path: sourcePath,
      type: 'file',
    }
    fileStore.openFile(node)
    editorStore.setCurrentFile(sourcePath)
    editorStore.loadContent(sourcePath, latest.content)
    fileStore.unsavedFiles.delete(sourcePath)
  }
}

function beatValidationIcon(candidate: CandidateInfo | null): string {
  const status = candidate?.beat_validation?.status
  if (status === 'pass') return 'fa-solid fa-circle-check'
  if (status === 'warning') return 'fa-solid fa-triangle-exclamation'
  return 'fa-solid fa-circle-question'
}

function beatValidationDetails(candidate: CandidateInfo | null): string[] {
  const validation = candidate?.beat_validation
  if (!validation) return []
  const required = validation.required_beats || []
  const forbidden = validation.forbidden_beats || []
  const missing = required
    .filter((item) => item.status === 'missing')
    .map((item) => `缺失：${item.text}`)
  const partial = required
    .filter((item) => item.status === 'partial' || item.status === 'unknown')
    .map((item) => `不确定：${item.text}${item.evidence ? `（证据：${item.evidence}）` : ''}`)
  const violations = forbidden
    .filter((item) => item.violated)
    .map((item) => `禁止项疑似出现：${item.text}${item.evidence ? `（证据：${item.evidence}）` : ''}`)
  return [...missing, ...partial, ...violations].slice(0, 5)
}

function beatValidationWarning(candidate: CandidateInfo | null): string {
  const validation = candidate?.beat_validation
  if (!validation || validation.status !== 'warning') return ''
  const details = beatValidationDetails(candidate)
  if (details.length > 0) return '信息点检查发现风险，采用前建议先预览确认。'
  return validation.summary || '信息点检查发现风险，采用前建议先预览确认。'
}

function beatValidationMessage(candidate: CandidateInfo | null): string {
  const validation = candidate?.beat_validation
  if (!validation?.status) return ''
  if (validation.status === 'pass') return validation.summary || '信息点检查通过。'
  if (validation.status === 'warning') return beatValidationWarning(candidate)
  return validation.summary || '信息点检查未完成，不影响采用，请自行预览确认。'
}

function getPreviewWarning(candidate: CandidateInfo | null): string {
  if (!candidate) return ''
  const beatWarning = beatValidationWarning(candidate)
  if (beatWarning) return beatWarning
  if (candidate.warning_message) return candidate.warning_message
  if (candidate.continuity && candidate.continuity.has_warning) {
    const missing = (candidate.continuity.anchors_missing || []).slice(0, 3)
    if (missing.length > 0) {
      return `可能与前文设定不一致：缺少「${missing.join('、')}」等关键元素，建议先预览再采纳。`
    }
    return '可能与前文设定不一致，建议先预览再采纳。'
  }
  return ''
}

function getGenerationContext(candidate: CandidateInfo | null): Record<string, unknown> {
  return (candidate?.generation_context || {}) as Record<string, unknown>
}

function isFeedbackRevision(candidate: CandidateInfo | null): boolean {
  if (!candidate) return false
  return candidate.action === 'feedback_revision' || getGenerationContext(candidate).revision_type === 'feedback_revision'
}

function revisionIndexLabel(candidate: CandidateInfo): number {
  const contextIndex = getGenerationContext(candidate).revision_index
  const value = candidate.revision_index || contextIndex || 1
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 1
}

function revisionParentLabel(candidate: CandidateInfo): string {
  const parentId = candidate.parent_candidate_id || String(getGenerationContext(candidate).parent_candidate_id || '')
  if (!parentId) return ''
  return parentId.length > 14 ? `${parentId.slice(0, 14)}...` : parentId
}

function revisionFeedbackSummary(candidate: CandidateInfo): string {
  const feedback = String(getGenerationContext(candidate).feedback_text || '').trim()
  if (!feedback) return ''
  return feedback.length > 42 ? `${feedback.slice(0, 42)}...` : feedback
}

function normalizeBeatList(value: unknown): unknown[] {
  return Array.isArray(value) ? value.filter(Boolean) : []
}

function getInheritedBeatCounts(candidate: CandidateInfo | null): { required: number; forbidden: number; total: number } {
  if (!candidate) return { required: 0, forbidden: 0, total: 0 }
  const context = getGenerationContext(candidate)
  const validation = (candidate.beat_validation || {}) as NonNullable<CandidateInfo['beat_validation']>
  const required = normalizeBeatList(context.required_beats_input || context.inherited_required_beats || validation.required_beats)
  const forbidden = normalizeBeatList(
    context.forbidden_beats_input ||
      context.inherited_forbidden_beats ||
      validation.forbidden_beats,
  )
  return {
    required: required.length,
    forbidden: forbidden.length,
    total: required.length + forbidden.length,
  }
}

function openRevisionModal(candidate: CandidateInfo) {
  if (candidate.status !== 'pending') {
    notification.warning('只有待处理候选稿可以按反馈再生成')
    return
  }
  revisionParent.value = candidate
  revisionFeedback.value = ''
  revisionQuickActions.value = []
  revisionScope.value = 'full_candidate'
  revisioning.value = true
}

function closeRevisionModal() {
  if (revisionSubmitting.value) return
  revisioning.value = false
  revisionParent.value = null
  revisionFeedback.value = ''
  revisionQuickActions.value = []
  revisionScope.value = 'full_candidate'
}

function toggleRevisionQuickAction(action: string) {
  if (revisionSubmitting.value) return
  if (revisionQuickActions.value.includes(action)) {
    revisionQuickActions.value = revisionQuickActions.value.filter((item) => item !== action)
  } else {
    revisionQuickActions.value = [...revisionQuickActions.value, action]
  }
}

async function submitRevision() {
  const parent = revisionParent.value
  const projectId = projectStore.currentProject?.id
  if (!parent || !projectId) return

  const feedbackText = revisionFeedback.value.trim()
  if (!feedbackText && revisionQuickActions.value.length === 0) {
    notification.warning('请填写反馈，或选择至少一个快捷反馈')
    return
  }
  if (revisionFeedbackLength.value > 1000) {
    notification.warning('反馈内容不能超过 1000 字')
    return
  }

  const payload: CandidateRevisionRequest = {
    feedback_text: feedbackText,
    quick_actions: revisionQuickActions.value,
    repair_scope: revisionScope.value,
    inherit_required_beats: true,
    inherit_forbidden_beats: true,
    run_beat_validation: true,
  }

  revisionSubmitting.value = true
  try {
    const child = await api.post<CandidateInfo>(
      API_ROUTES.candidateRevise(projectId, parent.id),
      payload,
    )
    notification.success('已生成新的反馈修订候选稿，采用后才会覆盖当前场景')
    revisioning.value = false
    revisionParent.value = null
    revisionFeedback.value = ''
    revisionQuickActions.value = []
    revisionScope.value = 'full_candidate'
    await fetchCandidates(true)
    selectedId.value = child.id
  } catch (error: unknown) {
    notification.error(toUserFacingMessage(error, '按反馈再生成候选稿失败'))
  } finally {
    revisionSubmitting.value = false
  }
}

async function adoptCandidate(candidate: CandidateInfo) {
  // 检查编辑器中是否有未保存的本地修改（仅存在于内存，后端 hash 冲突检测无法发现）
  const hasUnsavedEdits = fileStore.unsavedFiles.has(candidate.source_path)

  // 构建确认消息，优先展示连续性警告
  const warning = getPreviewWarning(candidate)
  let confirmMsg = `确认将该候选稿写入当前正文？\n此操作会替换 "${candidate.source_filename}" 的当前内容。\n\n采用前会检查正文是否被其他操作修改，避免误覆盖。`
  if (hasUnsavedEdits) {
    confirmMsg = `⚠ 该文件有未保存的修改，采用候选稿将覆盖这些修改且无法恢复。\n\n${confirmMsg}`
  }
  if (warning) {
    confirmMsg = `⚠ 该候选稿存在采用前警告：\n${warning}\n\n${confirmMsg}`
  }
  if (!confirm(confirmMsg)) {
    return
  }
  
  try {
    const result = await api.post<CandidateAdoptResult>(
      API_ROUTES.candidateAdopt(projectStore.currentProject?.id || '', candidate.id),
    )
    if (result?.conflict || result?.success === false) {
      notification.error(result?.message || '源文件已被其他操作修改，请重新生成候选稿后再采用。')
      await fetchCandidates()
      return
    }

    notification.success('候选稿已采用，正式正文已更新。')
    await fetchCandidates()
    await syncAdoptedSource(result?.file_path || candidate.source_path)
  } catch (error: unknown) {
    if ((error as { response?: { status?: number } }).response?.status === 409 || getApiErrorCode(error) === 'FILE_CONFLICT') {
      notification.error(toUserFacingMessage(error, '源文件已被其他操作修改，请重新生成候选稿后再采用。'))
      await fetchCandidates()
      return
    }
    notification.error(toUserFacingMessage(error, '采用候选稿失败'))
  }
}

async function adoptFromPreview() {
  if (!previewCandidateInfo.value) return
  await adoptCandidate(previewCandidateInfo.value)
  closePreview()
}

async function deleteCandidate(candidate: CandidateInfo) {
  if (!confirm(`确定要删除这个候选稿吗？`)) {
    return
  }
  
  try {
    await api.delete(API_ROUTES.candidateDetail(projectStore.currentProject?.id || '', candidate.id))
    notification.success('候选稿已成功删除')
    await fetchCandidates()
  } catch (error: unknown) {
    notification.error(toUserFacingMessage(error, '删除候选稿失败'))
  }
}

/** 检查候选稿是否有可修复的警告 */
function hasRepairableWarning(candidate: CandidateInfo): boolean {
  if (candidate.status !== 'pending') return false
  const q = candidate.quality
  if (!q) return false
  // 有任意质量警告则认为可修复
  return (
    q.instruction_following === 'warning' ||
    q.forbidden_check === 'warning' ||
    q.change_scope === 'large'
  )
}

/** 修复候选稿 */
async function repairCandidate(candidate: CandidateInfo) {
  if (!projectStore.currentProject?.id) return
  if (!confirm('修复会生成新的候选稿，不会自动修改正文。是否继续？')) {
    return
  }
  try {
    const { repairCandidate: repairApi } = await import('@/modules/candidate/api')
    const child = await repairApi(projectStore.currentProject.id, candidate.id)
    notification.success('已生成修复候选稿')
    await fetchCandidates()
    void child // child info available if needed
  } catch (error: unknown) {
    notification.error(toUserFacingMessage(error, '生成修复候选稿失败'))
  }
}

onMounted(() => {
  void fetchCandidates(true)
  disposeCandidateCreated = sse.on('candidate-created', () => {
    void fetchCandidates(true)
  })
  disposeCandidateAdopted = sse.on('candidate-adopted', () => {
    void fetchCandidates(true)
  })
})

onUnmounted(() => {
  disposeCandidateCreated?.()
  disposeCandidateAdopted?.()
})

watch(() => projectStore.currentProject?.id, () => {
  selectedId.value = null
  closePreview()
  void fetchCandidates(true)
})
</script>

<style scoped>
.candidate-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid var(--border-color);
}

.panel-title {
  font-weight: 600;
  color: var(--text-primary);
}

.candidate-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  margin: 0 8px 4px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--accent-primary);
  line-height: 1.4;
}

.candidate-notice i {
  flex-shrink: 0;
  font-size: 11px;
}

.btn-refresh {
  padding: 4px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
  &:hover:not(:disabled) {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-muted);
  i {
    font-size: 32px;
    margin-bottom: 8px;
    opacity: 0.5;
  }
}

.candidate-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.candidate-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  
  &:hover {
    border-color: var(--border-color);
  }
  
  &.active {
    border-color: var(--accent-primary);
    background: rgba(59, 130, 246, 0.05);
  }
}

.card-header {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.continuity-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;

  &.continuity-high {
    background: rgba(239, 68, 68, 0.18);
    color: var(--accent-danger);
  }
  &.continuity-medium {
    background: rgba(251, 146, 60, 0.18);
    color: #f97316;
  }
  &.continuity-low {
    background: rgba(234, 179, 8, 0.18);
    color: var(--accent-warning);
  }
}

.beat-validation-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;

  &.beat-pass {
    background: rgba(34, 197, 94, 0.16);
    color: var(--accent-success);
  }
  &.beat-warning {
    background: rgba(251, 146, 60, 0.18);
    color: #f97316;
  }
  &.beat-unknown {
    background: rgba(148, 163, 184, 0.2);
    color: var(--text-secondary);
  }
}

.source-type-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;

  &.source-llm {
    background: rgba(59, 130, 246, 0.12);
    color: var(--accent-primary);
  }
  &.source-dry-run {
    background: rgba(148, 163, 184, 0.2);
    color: var(--text-secondary);
  }
}

.candidate-warning-message {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  margin: 6px 0;
  background: rgba(251, 146, 60, 0.1);
  border-left: 2px solid #f97316;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;

  i {
    flex-shrink: 0;
    color: #f97316;
    margin-top: 2px;
  }
}

.beat-message-content {
  display: grid;
  gap: 4px;
}

.beat-detail-list {
  margin: 0;
  padding-left: 16px;
  color: var(--text-muted);
}

.beat-message-pass {
  background: rgba(34, 197, 94, 0.08);
  border-left-color: var(--accent-success);

  i {
    color: var(--accent-success);
  }
}

.beat-message-warning {
  background: rgba(251, 146, 60, 0.1);
  border-left-color: #f97316;
}

.beat-message-unknown {
  background: rgba(148, 163, 184, 0.12);
  border-left-color: var(--text-muted);

  i {
    color: var(--text-muted);
  }
}

.quality-summary {
  display: flex;
  gap: 6px;
  margin: 6px 0;
  flex-wrap: wrap;
}

.quality-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;

  i { font-size: 9px; }

  &.badge-pass {
    background: rgba(34, 197, 94, 0.15);
    color: var(--accent-success);
  }
  &.badge-warning {
    background: rgba(251, 146, 60, 0.18);
    color: #f97316;
  }
  &.badge-danger {
    background: rgba(239, 68, 68, 0.18);
    color: var(--accent-danger);
  }
  &.badge-unknown {
    background: rgba(148, 163, 184, 0.15);
    color: var(--text-muted);
  }
}

.quality-badge-scope {
  font-family: monospace;
  font-size: 9px;
}

/* T10.1 Quality Explanation collapsible area */
.quality-explanation {
  margin: 6px 0;
  border-radius: var(--radius-sm);
  background: rgba(148, 163, 184, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.quality-explanation-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 7px 8px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  text-align: left;
  border-radius: var(--radius-sm);
  transition: background 0.15s;

  &:hover {
    background: rgba(148, 163, 184, 0.08);
  }

  i {
    font-size: 9px;
    flex-shrink: 0;
    color: var(--text-muted);
  }
}

.quality-explanation-body {
  padding: 4px 8px 8px;
  display: grid;
  gap: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.quality-explanation-empty {
  font-size: 11px;
  color: var(--text-muted);
  padding: 4px 0;
}

.quality-dimension {
  padding: 4px 0;
}

.quality-dimension-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.quality-dimension-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}

.quality-dimension-status {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 5px;
  border-radius: 3px;

  &.expl-pass {
    background: rgba(34, 197, 94, 0.12);
    color: var(--accent-success);
  }
  &.expl-warning {
    background: rgba(251, 146, 60, 0.14);
    color: #f97316;
  }
  &.expl-danger {
    background: rgba(239, 68, 68, 0.14);
    color: var(--accent-danger);
  }
  &.expl-unknown {
    background: rgba(148, 163, 184, 0.12);
    color: var(--text-muted);
  }
}

.quality-dimension-description {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.45;
}

.quality-repair-explanation {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 7px 8px;
  background: rgba(251, 146, 60, 0.07);
  border-left: 2px solid #f97316;
  border-radius: 4px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-secondary);

  i {
    flex-shrink: 0;
    color: #f97316;
    margin-top: 2px;
  }

  div {
    display: grid;
    gap: 2px;
  }

  strong {
    color: var(--text-primary);
    font-weight: 600;
  }
}

.quality-repair-note {
  color: var(--text-muted);
  font-size: 10px;
}

.quality-safety-text {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  background: rgba(59, 130, 246, 0.06);
  border-radius: 4px;
  font-size: 10px;
  color: var(--accent-primary);
  line-height: 1.45;

  i {
    flex-shrink: 0;
    font-size: 10px;
    margin-top: 1px;
  }
}

.candidate-action {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  
  &.action-rewrite { background: rgba(239, 68, 68, 0.2); color: var(--accent-danger); }
  &.action-continue { background: rgba(34, 197, 94, 0.2); color: var(--accent-success); }
  &.action-modify { background: rgba(59, 130, 246, 0.2); color: var(--accent-primary); }
  &.action-chat { background: rgba(139, 92, 246, 0.2); color: #8b5cf6; }
  &.action-expand { background: rgba(234, 179, 8, 0.2); color: var(--accent-warning); }
  &.action-shrink { background: rgba(148, 163, 184, 0.2); color: var(--text-secondary); }
  &.action-polish { background: rgba(6, 182, 212, 0.2); color: #06b6d4; }
  &.action-fallback_draft { background: rgba(148, 163, 184, 0.2); color: var(--text-secondary); }
  &.action-repair { background: rgba(251, 146, 60, 0.2); color: #f97316; }
}

.candidate-status {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  
  &.status-pending { background: rgba(234, 179, 8, 0.2); color: var(--accent-warning); }
  &.status-adopted { background: rgba(34, 197, 94, 0.2); color: var(--accent-success); }
  &.status-discarded { background: rgba(148, 163, 184, 0.2); color: var(--text-muted); }
}

.card-body {
  margin-bottom: 8px;
}

.candidate-filename {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.candidate-revision-summary {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin: 7px 0;
  padding: 7px 8px;
  border-radius: var(--radius-sm);
  background: rgba(139, 92, 246, 0.1);
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.45;

  i {
    color: #8b5cf6;
    margin-top: 2px;
  }

  div {
    display: grid;
    gap: 2px;
  }

  strong {
    color: var(--text-primary);
    font-weight: 600;
  }
}

.candidate-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

.card-quality {
  margin: 6px 0;
  padding: 6px 8px;
  background: rgba(148, 163, 184, 0.06);
  border-radius: var(--radius-sm);
  display: grid;
  gap: 4px;
}

.quality-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  line-height: 1.4;

  i { flex-shrink: 0; font-size: 11px; }

  &.quality-pass {
    color: var(--accent-success);
    i { color: var(--accent-success); }
  }
  &.quality-warning {
    color: #f97316;
    i { color: #f97316; }
  }
  &.quality-unknown {
    color: var(--text-muted);
    i { color: var(--text-muted); }
  }
  &.quality-continuity {
    &.continuity-high { color: var(--accent-danger); i { color: var(--accent-danger); } }
    &.continuity-medium { color: #f97316; i { color: #f97316; } }
    &.continuity-low { color: var(--accent-warning); i { color: var(--accent-warning); } }
  }
}

.quality-detail {
  font-size: 11px;
  margin-top: 2px;
}

.quality-warning-detail {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px 6px;
  background: rgba(251, 146, 60, 0.1);
  border-left: 2px solid #f97316;
  border-radius: 4px;
  color: var(--text-secondary);
  line-height: 1.5;

  i { flex-shrink: 0; color: #f97316; margin-top: 2px; }
}

.quality-continuity-detail {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px 6px;
  background: rgba(251, 146, 60, 0.1);
  border-left: 2px solid #f97316;
  border-radius: 4px;
  color: var(--text-secondary);
  line-height: 1.5;

  i { flex-shrink: 0; color: #f97316; margin-top: 2px; }
}

.card-revision {
  margin: 6px 0;
}

.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.card-actions-primary {
  display: flex;
  gap: 4px;
}

.action-btn {
  padding: 4px 6px;
  border: none;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--border-color);
    color: var(--text-primary);
  }

  &.action-adopt {
    background: rgba(34, 197, 94, 0.1);
    color: var(--accent-success);
    &:hover {
      background: var(--accent-success);
      color: white;
    }
  }

  &.action-delete {
    &:hover {
      background: var(--accent-danger);
      color: white;
    }
  }

  &.action-revise {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(139, 92, 246, 0.12);
    color: #8b5cf6;
    font-size: 11px;
    &:hover {
      background: #8b5cf6;
      color: white;
    }
  }
}

.action-revise-label {
  font-size: 11px;
  white-space: nowrap;
}

.action-repair {
  color: var(--accent-warning, #f97316);
  border-color: var(--accent-warning, #f97316);
}

.action-repair-label {
  font-size: 11px;
  white-space: nowrap;
}

/* 预览弹窗 */
.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.preview-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.preview-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(59, 130, 246, 0.06);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  font-size: 11px;
  color: var(--accent-primary);
  line-height: 1.4;
}

.preview-notice i {
  flex-shrink: 0;
}

.preview-title {
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
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.preview-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-card);
  flex-wrap: wrap;
}

.preview-warning {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(251, 146, 60, 0.1);
  border-bottom: 1px solid rgba(251, 146, 60, 0.2);
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;

  i {
    flex-shrink: 0;
    color: #f97316;
    margin-top: 3px;
  }
}

.meta-label {
  font-size: 11px;
  color: var(--text-muted);
}

.meta-value {
  font-size: 12px;
  color: var(--text-secondary);
  
  &.action-badge {
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 500;
  }
}

.preview-body {
  flex: 1;
  padding: 16px;
  overflow: hidden;
}

.preview-textarea {
  width: 100%;
  height: 100%;
  min-height: 300px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  font-family: monospace;
  font-size: 13px;
  resize: none;
  outline: none;
  
  &:focus {
    border-color: var(--accent-primary);
  }
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.btn-adopt {
  padding: 8px 16px;
  background: var(--accent-success);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  
  &:hover {
    opacity: 0.9;
  }
}

.btn-cancel {
  padding: 8px 16px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  
  &:hover {
    background: var(--border-color);
    color: var(--text-primary);
  }
}

.revision-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.revision-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  width: 92%;
  max-width: 560px;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.revision-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.revision-title {
  font-weight: 600;
  color: var(--text-primary);
}

.revision-notice,
.revision-parent-warning {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 16px;
  font-size: 12px;
  line-height: 1.6;
}

.revision-notice {
  background: rgba(59, 130, 246, 0.06);
  color: var(--accent-primary);
}

.revision-parent-warning {
  background: rgba(251, 146, 60, 0.1);
  color: var(--text-secondary);
}

.revision-parent-beats {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 9px 16px;
  background: rgba(139, 92, 246, 0.08);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;

  i {
    color: #8b5cf6;
    margin-top: 2px;
  }
}

.revision-parent {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-card);
  font-size: 12px;
  color: var(--text-secondary);
}

.revision-parent strong {
  color: var(--text-primary);
  font-family: monospace;
}

.revision-parent em {
  color: var(--text-muted);
  font-style: normal;
}

.revision-quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px 4px;
}

.revision-quick-actions span {
  flex-basis: 100%;
  font-size: 12px;
  color: var(--text-muted);
}

.revision-quick-actions button {
  border: 1px solid var(--border-color);
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  padding: 5px 8px;
  font-size: 12px;
  cursor: pointer;

  &.active {
    border-color: #8b5cf6;
    background: rgba(139, 92, 246, 0.16);
    color: #8b5cf6;
  }
}

.revision-field {
  display: grid;
  gap: 6px;
  padding: 10px 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

.revision-field textarea,
.revision-field select {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 8px 10px;
  font-size: 13px;
  outline: none;

  &:focus {
    border-color: var(--accent-primary);
  }
}

.revision-field textarea {
  min-height: 110px;
  resize: vertical;
}

.revision-length-hint {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;

  &.warning {
    color: var(--accent-warning);
  }
}

.revision-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.btn-revision-submit {
  padding: 8px 16px;
  background: #8b5cf6;
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}
</style>
