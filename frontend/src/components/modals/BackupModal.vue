<template>
  <a-modal
    :open="visible"
    title="项目备份"
    :width="720"
    :footer="null"
    :destroy-on-close="true"
    @cancel="close"
  >
    <div class="backup-modal">
      <div class="create-row">
        <a-input
          v-model:value="description"
          placeholder="备份说明，例如：第一卷完成前"
          @press-enter="createBackup"
        />
        <a-button
          type="primary"
          :loading="isCreating"
          :disabled="!projectId"
          @click="createBackup"
        >
          创建备份
        </a-button>
      </div>

      <div class="toolbar">
        <span>{{ backups.length }} 个备份</span>
        <a-button
          size="small"
          :loading="isLoading"
          @click="loadBackups"
        >
          刷新
        </a-button>
      </div>

      <a-empty
        v-if="!isLoading && backups.length === 0"
        description="暂无备份"
      />
      <div
        v-else
        class="backup-list"
      >
        <div
          v-for="backup in backups"
          :key="backup.backup_id"
          class="backup-item"
        >
          <div class="backup-main">
            <div class="backup-title">
              {{ backup.description || '未命名备份' }}
            </div>
            <div class="backup-meta">
              {{ formatTime(backup.created_at) }} · {{ backup.file_count }} 个文件 · {{ formatSize(backup.total_size) }}
            </div>
            <code>{{ backup.backup_id }}</code>
          </div>
          <div class="backup-actions">
            <a-button
              size="small"
              @click="restoreBackup(backup.backup_id)"
            >
              恢复
            </a-button>
            <a-button
              size="small"
              danger
              @click="deleteBackup(backup.backup_id)"
            >
              删除
            </a-button>
          </div>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Modal } from 'ant-design-vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'

interface BackupInfo {
  backup_id: string
  project_id: string
  description: string
  created_at: string
  file_count: number
  total_size: number
}

const uiStore = useUIStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.backup)
const projectId = computed(() => projectStore.currentProject?.id || '')

const backups = ref<BackupInfo[]>([])
const description = ref('')
const isLoading = ref(false)
const isCreating = ref(false)

watch(visible, (v) => {
  if (v) {
    description.value = ''
    loadBackups()
  }
})

async function loadBackups() {
  if (!projectId.value) return
  isLoading.value = true
  try {
    const data = await api.get<{ backups: BackupInfo[]; total: number }>('/backup', {
      params: { project_id: projectId.value },
    })
    backups.value = data.backups || []
  } catch {
    notification.error('备份列表加载失败')
  } finally {
    isLoading.value = false
  }
}

async function createBackup() {
  if (!projectId.value) return
  isCreating.value = true
  try {
    await api.post<BackupInfo>('/backup', {
      project_id: projectId.value,
      description: description.value.trim(),
    })
    description.value = ''
    notification.success('备份已创建')
    await loadBackups()
  } catch {
    notification.error('创建备份失败')
  } finally {
    isCreating.value = false
  }
}

function restoreBackup(backupId: string) {
  if (!projectId.value) return
  Modal.confirm({
    title: '恢复备份',
    content: '恢复会覆盖当前项目文件，备份目录会保留。确定继续吗？',
    okText: '恢复',
    cancelText: '取消',
    async onOk() {
      try {
        await api.post(API_ROUTES.backupDetail(backupId), { target_project_id: null }, {
          params: { project_id: projectId.value },
        })
        await fileStore.loadTree(projectId.value)
        editorStore.setCurrentFile(null)
        notification.success('备份已恢复')
        close()
      } catch {
        notification.error('恢复备份失败')
      }
    },
  })
}

function deleteBackup(backupId: string) {
  if (!projectId.value) return
  Modal.confirm({
    title: '删除备份',
    content: '删除后不能恢复，确定删除这个备份吗？',
    okText: '删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      try {
        await api.delete(API_ROUTES.backupDetail(backupId), {
          params: { project_id: projectId.value },
        })
        notification.success('备份已删除')
        await loadBackups()
      } catch {
        notification.error('删除备份失败')
      }
    },
  })
}

function formatTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatSize(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function close() {
  uiStore.closeBackup()
}
</script>

<style scoped lang="scss">
.backup-modal {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.create-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 13px;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow: auto;
}

.backup-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.backup-main {
  min-width: 0;
}

.backup-title {
  color: var(--text-primary);
  font-weight: 600;
  margin-bottom: 4px;
}

.backup-meta {
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 6px;
}

code {
  color: var(--text-secondary);
  font-size: 11px;
  word-break: break-all;
}

.backup-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-shrink: 0;
}
</style>
