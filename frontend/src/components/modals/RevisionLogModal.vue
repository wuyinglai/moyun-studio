<template>
  <a-modal
    :open="visible"
    title="修改日志管理"
    :width="800"
    :footer="null"
    @cancel="close"
  >
    <div class="revision-modal">
      <a-spin :spinning="isLoading">
        <a-empty
          v-if="logs.length === 0"
          description="暂无修改日志"
          style="margin-top: 24px;"
        />
        <a-list
          v-else
          :data-source="logs"
          item-layout="vertical"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <a-tag :color="typeColor(item.revision_type)">
                    {{ typeLabel(item.revision_type) }}
                  </a-tag>
                  {{ item.description }}
                </template>
                <template #description>
                  <div class="log-meta">
                    <span>字数: {{ item.word_count_before }} → {{ item.word_count_after }}</span>
                    <span>{{ formatTime(item.created_at) }}</span>
                    <span class="log-path">{{ item.chapter_path }}</span>
                  </div>
                </template>
              </a-list-item-meta>
              <template #extra>
                <a-button
                  size="small"
                  @click="showDiff(item)"
                >
                  <template #icon>
                    <i class="fa-solid fa-code-compare" />
                  </template>
                  查看差异
                </a-button>
              </template>
              <div
                v-if="selectedLog?.id === item.id && selectedLog?.diff"
                class="diff-block"
              >
                <a-divider>差异</a-divider>
                <pre
                  class="diff-content"
                  v-text="selectedLog.diff"
                />
              </div>
            </a-list-item>
          </template>
        </a-list>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import api from '@/services/api'

const uiStore = useUIStore()
const projectStore = useProjectStore()

const visible = computed(() => uiStore.modals.revisionLog)

interface RevisionLog {
  id: string
  chapter_path: string
  revision_type: string
  description: string
  word_count_before: number
  word_count_after: number
  diff?: string
  created_at: string
}

const logs = ref<RevisionLog[]>([])
const isLoading = ref(false)
const selectedLog = ref<RevisionLog | null>(null)

watch(visible, async (val) => {
  if (val) {
    await loadLogs()
    selectedLog.value = null
  }
})

async function loadLogs() {
  if (!projectStore.currentProject) return
  isLoading.value = true
  try {
    logs.value = await api.get<RevisionLog[]>(`/revision-log/${projectStore.currentProject.id}`)
  } catch {
    logs.value = []
  } finally {
    isLoading.value = false
  }
}

async function showDiff(log: RevisionLog) {
  if (selectedLog.value?.id === log.id) {
    selectedLog.value = null
    return
  }
  selectedLog.value = log
}

function typeColor(type: string): string {
  switch (type) {
    case 'ai_rewrite': return 'purple'
    case 'user_edit': return 'blue'
    case 'auto_save': return 'green'
    default: return 'default'
  }
}

function typeLabel(type: string): string {
  switch (type) {
    case 'ai_rewrite': return 'AI重写'
    case 'user_edit': return '用户编辑'
    case 'auto_save': return '自动保存'
    default: return type
  }
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function close() {
  uiStore.closeRevisionLog()
  selectedLog.value = null
}
</script>

<style scoped lang="scss">
.revision-modal {
  .log-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
    flex-wrap: wrap;
  }

  .log-path {
    font-family: monospace;
    font-size: 11px;
    opacity: 0.7;
  }

  .diff-block {
    margin-top: 8px;
  }

  .diff-content {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 11px;
    line-height: 1.5;
    max-height: 300px;
    overflow: auto;
    white-space: pre;
    color: var(--text-primary);
  }
}
</style>
