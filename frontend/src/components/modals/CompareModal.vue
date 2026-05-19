<template>
  <a-modal
    :open="visible"
    title="版本对比"
    :width="860"
    :footer="null"
    @cancel="close"
  >
    <div class="compare-modal">
      <a-alert
        v-if="currentPath"
        type="info"
        show-icon
        class="current-file-alert"
      >
        <template #message>
          当前文件：{{ currentPath }}
        </template>
      </a-alert>

      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="旧版本">
              <a-select
                v-model:value="oldSnapshotId"
                allow-clear
                placeholder="选择历史快照，或手动输入下方文本"
                style="width: 100%; margin-bottom: 8px;"
              >
                <a-select-option
                  v-for="s in snapshots"
                  :key="s.snapshot_id"
                  :value="s.snapshot_id"
                >
                  {{ snapshotLabel(s) }}
                </a-select-option>
              </a-select>
              <a-textarea
                v-model:value="oldText"
                :rows="8"
                placeholder="输入旧版本内容"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="新版本">
              <a-select
                v-model:value="newSnapshotId"
                allow-clear
                placeholder="选择历史快照，或使用当前编辑器内容"
                style="width: 100%; margin-bottom: 8px;"
              >
                <a-select-option
                  v-for="s in snapshots"
                  :key="s.snapshot_id"
                  :value="s.snapshot_id"
                >
                  {{ snapshotLabel(s) }}
                </a-select-option>
              </a-select>
              <a-textarea
                v-model:value="newText"
                :rows="8"
                placeholder="输入新版本内容"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <div class="compare-actions">
          <a-button
            :disabled="!currentPath"
            :loading="isLoadingSnapshots"
            @click="loadSnapshots"
          >
            加载历史版本
          </a-button>
          <a-button @click="loadCurrentVersion">
            使用当前内容
          </a-button>
          <a-button
            danger
            :disabled="!oldSnapshotId && !newSnapshotId"
            @click="restoreSelectedSnapshot"
          >
            恢复所选版本
          </a-button>
          <a-button
            type="primary"
            :loading="isComparing"
            @click="compare"
          >
            <template #icon>
              <i class="fa-solid fa-code-compare" />
            </template>
            对比
          </a-button>
        </div>
      </a-form>

      <div
        v-if="snapshots.length > 0"
        class="snapshot-list"
      >
        <span
          v-for="s in snapshots.slice(0, 6)"
          :key="s.snapshot_id"
          class="snapshot-chip"
        >
          {{ snapshotLabel(s) }}
        </span>
      </div>

      <div
        v-if="diffResult"
        class="diff-result"
      >
        <a-divider>差异结果</a-divider>
        <div class="diff-stats">
          <span class="stat-added">+{{ diffResult.added_lines }} 行</span>
          <span class="stat-removed">-{{ diffResult.removed_lines }} 行</span>
        </div>
        <pre
          class="diff-content"
          v-text="diffResult.diff || '两个版本没有差异'"
        />
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

interface CompareResult {
  diff: string
  has_diff: boolean
  added_lines: number
  removed_lines: number
}

interface SnapshotItem {
  snapshot_id: string
  file_path: string
  label?: string | null
  created_at: string
  word_count?: number
}

const uiStore = useUIStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.compare)
const currentPath = computed(() => editorStore.currentFilePath || '')
const oldText = ref('')
const newText = ref('')
const oldSnapshotId = ref<string | undefined>(undefined)
const newSnapshotId = ref<string | undefined>(undefined)
const snapshots = ref<SnapshotItem[]>([])
const isComparing = ref(false)
const isLoadingSnapshots = ref(false)
const diffResult = ref<CompareResult | null>(null)

watch(visible, async (val) => {
  if (val) {
    loadCurrentVersion()
    await loadSnapshots()
  }
})

function snapshotLabel(item: SnapshotItem) {
  const time = item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : item.snapshot_id
  return `${item.label || '快照'} · ${time}`
}

async function loadSnapshots() {
  const projectId = projectStore.currentProject?.id
  if (!projectId || !currentPath.value) return
  isLoadingSnapshots.value = true
  try {
    snapshots.value = await fileStore.loadSnapshots(projectId, currentPath.value) as SnapshotItem[]
    if (snapshots.value.length > 0 && !oldSnapshotId.value) oldSnapshotId.value = snapshots.value[0].snapshot_id
  } catch (e: any) {
    snapshots.value = []
    notification.error(e?.message || '加载历史版本失败')
  } finally {
    isLoadingSnapshots.value = false
  }
}

function loadCurrentVersion() {
  const path = currentPath.value
  if (!path) {
    notification.warning('没有打开的文件')
    return
  }
  newText.value = editorStore.getContent(path)
}

async function compare() {
  const projectId = projectStore.currentProject?.id
  if (projectId && oldSnapshotId.value && newSnapshotId.value) {
    await compareSnapshots(projectId)
    return
  }
  if (!oldText.value && !newText.value) {
    notification.warning('请填写至少一个版本的内容')
    return
  }
  isComparing.value = true
  diffResult.value = null
  try {
    diffResult.value = await api.post<CompareResult>('/compare', {
      old_text: oldText.value,
      new_text: newText.value,
    })
  } catch (e: any) {
    notification.error(e?.message || '对比失败')
  } finally {
    isComparing.value = false
  }
}

async function compareSnapshots(projectId: string) {
  isComparing.value = true
  diffResult.value = null
  try {
    diffResult.value = await api.post<CompareResult>(`/snapshots/${projectId}/compare`, {
      snapshot_id1: oldSnapshotId.value,
      snapshot_id2: newSnapshotId.value,
    })
  } catch (e: any) {
    notification.error(e?.message || '快照对比失败')
  } finally {
    isComparing.value = false
  }
}

async function restoreSelectedSnapshot() {
  const projectId = projectStore.currentProject?.id
  const snapshotId = newSnapshotId.value || oldSnapshotId.value
  if (!projectId || !currentPath.value || !snapshotId) return
  const ok = window.confirm('确定恢复所选快照吗？当前文件内容会被覆盖。')
  if (!ok) return
  try {
    await fileStore.restoreSnapshot(projectId, currentPath.value, snapshotId)
    const fileData = await fileStore.readFile(projectId, currentPath.value)
    editorStore.loadContent(currentPath.value, fileData.content || '', fileData.frontmatter)
    notification.success('已恢复快照')
  } catch (e: any) {
    notification.error(e?.message || '恢复失败')
  }
}

function close() {
  uiStore.closeCompare()
  oldText.value = ''
  newText.value = ''
  oldSnapshotId.value = undefined
  newSnapshotId.value = undefined
  snapshots.value = []
  diffResult.value = null
}
</script>

<style scoped lang="scss">
.current-file-alert {
  margin-bottom: 12px;
}

.compare-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.snapshot-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.snapshot-chip {
  padding: 4px 8px;
  border: 1px solid var(--border-ink);
  border-radius: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.diff-result {
  margin-top: 16px;
}

.diff-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-added {
  color: var(--accent-success);
  font-weight: 600;
  font-size: 14px;
}

.stat-removed {
  color: var(--accent-danger);
  font-weight: 600;
  font-size: 14px;
}

.diff-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  max-height: 400px;
  overflow: auto;
  white-space: pre;
  color: var(--text-primary);
}
</style>
