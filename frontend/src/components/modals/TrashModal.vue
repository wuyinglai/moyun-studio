<template>
  <a-modal
    :open="visible"
    title="回收站"
    :width="760"
    :footer="null"
    @cancel="close"
  >
    <div class="trash-modal">
      <div class="trash-actions">
        <a-button
          :loading="loading"
          @click="loadTrash"
        >
          刷新
        </a-button>
        <a-popconfirm
          title="确定清空回收站吗？"
          ok-text="清空"
          cancel-text="取消"
          @confirm="emptyTrash"
        >
          <a-button
            danger
            :disabled="items.length === 0"
          >
            清空回收站
          </a-button>
        </a-popconfirm>
      </div>

      <a-spin :spinning="loading">
        <a-empty
          v-if="items.length === 0"
          description="回收站为空"
        />
        <a-list
          v-else
          :data-source="items"
          item-layout="horizontal"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <span class="trash-name">{{ item.original_path || item.trash_name }}</span>
                </template>
                <template #description>
                  <span class="trash-meta">{{ item.timestamp }}</span>
                </template>
              </a-list-item-meta>
              <template #actions>
                <a-button
                  size="small"
                  type="primary"
                  ghost
                  @click="restore(item.trash_name)"
                >
                  恢复
                </a-button>
              </template>
            </a-list-item>
          </template>
        </a-list>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useFileStore } from '@/stores/file'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

interface TrashItem {
  trash_name: string
  original_path: string
  timestamp: string
}

const uiStore = useUIStore()
const fileStore = useFileStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.trash)
const loading = ref(false)
const items = ref<TrashItem[]>([])

watch(visible, (val) => {
  if (val) void loadTrash()
})

async function loadTrash() {
  loading.value = true
  try {
    const res = await api.get<{ items: TrashItem[] }>('/trash/list')
    items.value = res.items || []
  } catch (e: any) {
    items.value = []
    notification.error(e?.message || '加载回收站失败')
  } finally {
    loading.value = false
  }
}

async function restore(trashName: string) {
  try {
    await api.post('/trash/restore', { trash_name: trashName })
    notification.success('已恢复')
    if (projectStore.currentProject) await fileStore.loadTree(projectStore.currentProject.id)
    await loadTrash()
  } catch (e: any) {
    notification.error(e?.message || '恢复失败')
  }
}

async function emptyTrash() {
  try {
    const res = await api.post<{ count: number }>('/trash/empty', {})
    notification.success(`已清空 ${res.count || 0} 项`)
    await loadTrash()
  } catch (e: any) {
    notification.error(e?.message || '清空失败')
  }
}

function close() {
  uiStore.closeTrash()
}
</script>

<style scoped lang="scss">
.trash-modal {
  min-height: 240px;
}

.trash-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 12px;
}

.trash-name {
  color: var(--text-primary);
  word-break: break-all;
}

.trash-meta {
  color: var(--text-muted);
  font-size: 12px;
}
</style>
