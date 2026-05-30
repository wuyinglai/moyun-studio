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
          <span class="candidate-status" :class="`status-${candidate.status}`">
            {{ statusLabel(candidate.status) }}
          </span>
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
          <button
            class="action-btn"
            title="预览"
            @click.stop="previewCandidate(candidate)"
          >
            <i class="fa-solid fa-eye" />
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
        <div class="preview-meta">
          <span class="meta-label">源文件:</span>
          <span class="meta-value">{{ previewCandidateInfo?.source_filename }}</span>
          <span class="meta-label">动作:</span>
          <span class="meta-value action-badge" :class="`action-${previewCandidateInfo?.action}`">
            {{ actionLabel(previewCandidateInfo?.action || '') }}
          </span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import { useFileStore, type FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useSSE } from '@/composables/useSSE'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { CandidateAdoptResult, CandidateInfo } from '@/shared/api/types'

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
let disposeCandidateCreated: (() => void) | null = null
let disposeCandidateAdopted: (() => void) | null = null

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    rewrite: '重写',
    continue: '续写',
    modify: '修改',
    chat: '聊天改稿',
    expand: '扩写',
    shrink: '缩写',
    polish: '润色',
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
  } catch {
    if (!silent) {
      notification.error('获取候选稿列表失败')
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
  } catch {
    notification.error('获取候选稿内容失败')
    closePreview()
  }
}

function closePreview() {
  previewing.value = false
  previewCandidateInfo.value = null
  previewContent.value = ''
}

function getApiErrorCode(error: unknown): string | undefined {
  const response = (error as { response?: { data?: { error?: { code?: string } } } }).response
  return response?.data?.error?.code
}

function getApiErrorMessage(error: unknown): string {
  const response = (error as {
    response?: {
      data?: {
        error?: { message?: string }
        message?: string
        detail?: string | { message?: string }
      }
    }
    message?: string
  }).response
  const detail = response?.data?.detail
  if (typeof detail === 'string') return detail
  return response?.data?.error?.message
    || response?.data?.message
    || detail?.message
    || (error as { message?: string }).message
    || ''
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

async function adoptCandidate(candidate: CandidateInfo) {
  if (!confirm(`确定要采用这个候选稿吗？这将覆盖原文件 "${candidate.source_filename}"。`)) {
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
      notification.error(getApiErrorMessage(error) || '源文件已被其他操作修改，请重新生成候选稿后再采用。')
      await fetchCandidates()
      return
    }
    notification.error(getApiErrorMessage(error) || '采用候选稿失败')
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
  } catch {
    notification.error('删除候选稿失败')
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

.candidate-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

.card-actions {
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
</style>
