<template>
  <div class="recent-context-panel">
    <div class="panel-header">
      <h3>近期上下文</h3>
      <button
        class="btn-action"
        @click="handleAppend"
      >
        <i class="fa-solid fa-plus" /> 追加记录
      </button>
    </div>

    <div class="panel-content">
      <div
        v-if="isLoading"
        class="panel-loading"
      >
        <i class="fa-solid fa-spinner fa-spin" /> 加载中...
      </div>
      <div
        v-else-if="entries.length === 0"
        class="panel-empty"
      >
        <i class="fa-solid fa-clock-rotate-left" />
        <p>暂无上下文记录</p>
      </div>
      <div
        v-else
        class="entries-list"
      >
        <div
          v-for="(entry, i) in entries"
          :key="entry.time"
          class="context-entry"
        >
          <div class="entry-header">
            <span class="entry-time">{{ entry.time }}</span>
            <button
              class="entry-delete"
              title="删除"
              @click="deleteEntry(i)"
            >
              <i class="fa-solid fa-trash" />
            </button>
          </div>
          <div class="entry-content">
            {{ entry.text }}
          </div>
        </div>
      </div>
    </div>

    <!-- 追加对话框 -->
    <div
      v-if="showAppendDialog"
      class="append-dialog"
    >
      <textarea
        v-model="appendText"
        placeholder="输入新的上下文记录..."
        rows="4"
      />
      <div class="dialog-actions">
        <button
          class="btn-cancel"
          @click="showAppendDialog = false"
        >
          取消
        </button>
        <button
          class="btn-confirm"
          @click="confirmAppend"
        >
          追加
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRecentContextStore } from '@/stores/recentContext'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'

interface ContextEntry {
  time: string
  text: string
}

const recentContextStore = useRecentContextStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()

const isLoading = ref(false)
const showAppendDialog = ref(false)
const appendText = ref('')

const entries = computed<ContextEntry[]>(() => {
  // 解析：按 ## 标题分隔（与 store appendChapter 格式一致）
  const raw = recentContextStore.content
  if (!raw) return []
  return raw.split(/\n(?=## )/).map((block) => {
    const lines = block.trim().split('\n')
    const time = (lines[0] || '').replace(/^##\s*/, '')
    const text = lines.slice(1).join('\n').trim()
    return { time, text }
  }).filter(e => e.time || e.text)
})

async function loadContext() {
  if (!projectStore.currentProject) return
  isLoading.value = true
  try {
    await recentContextStore.load(projectStore.currentProject.id)
  } finally {
    isLoading.value = false
  }
}

function handleAppend() {
  showAppendDialog.value = true
  appendText.value = ''
}

async function confirmAppend() {
  if (!appendText.value.trim() || !projectStore.currentProject) return
  const timestamp = new Date().toLocaleString('zh-CN')
  const entry = `\n## ${timestamp}\n${appendText.value.trim()}\n`
  const newContent = recentContextStore.content
    ? recentContextStore.content + '\n' + entry
    : entry

  recentContextStore.content = newContent
  try {
    await recentContextStore.save(projectStore.currentProject.id)
    showAppendDialog.value = false
    notification.success('已追加上下文记录')
  } catch {
    notification.error('追加失败')
  }
}

async function deleteEntry(index: number) {
  if (!projectStore.currentProject) return
  const raw = recentContextStore.content
  if (!raw) return

  // 过滤空块，与 entries computed 保持一致
  const blocks = raw.split(/\n(?=## )/).filter(Boolean)
  if (index < 0 || index >= blocks.length) return

  blocks.splice(index, 1)
  const newContent = blocks.join('')

  recentContextStore.content = newContent
  try {
    await recentContextStore.save(projectStore.currentProject.id)
    notification.success('已删除上下文记录')
  } catch {
    notification.error('删除失败')
    recentContextStore.content = raw
  }
}

defineExpose({ loadContext })
</script>

<style scoped>
.recent-context-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.panel-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--accent-primary);
  color: white;
  font-size: 12px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
}

.panel-loading,
.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  color: var(--text-muted);
  opacity: 0.5;
}

.panel-empty i { font-size: 28px; }

.entries-list {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.context-entry {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.entry-time {
  font-size: 11px;
  color: var(--text-muted);
}

.entry-delete {
  background: none;
  color: var(--text-muted);
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 3px;
  transition: color 0.2s;
}

.entry-delete:hover { color: var(--accent-danger); }

.entry-content {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
  white-space: pre-wrap;
}

.append-dialog {
  padding: 12px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.append-dialog textarea {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px;
  color: var(--text-primary);
  font-size: 13px;
  resize: none;
  outline: none;
  font-family: inherit;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.btn-cancel,
.btn-confirm {
  padding: 4px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  transition: opacity 0.2s;
}

.btn-cancel {
  background: var(--bg-card);
  color: var(--text-secondary);
}

.btn-confirm {
  background: var(--accent-primary);
  color: white;
}

.btn-confirm:hover { opacity: 0.85; }
</style>
