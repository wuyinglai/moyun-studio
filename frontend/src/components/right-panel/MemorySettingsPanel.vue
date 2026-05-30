<template>
  <div class="memory-settings-panel">
    <section class="dashboard-section">
      <div class="section-head">
        <span>记忆概览</span>
        <button
          class="link-btn"
          :disabled="!projectId || isRefreshing"
          @click="refreshAll"
        >
          <i :class="isRefreshing ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-rotate'" />
          刷新
        </button>
      </div>

      <div class="status-cards">
        <div
          v-for="card in statusCards"
          :key="card.label"
          class="status-card"
        >
          <div
            class="card-indicator"
            :class="card.statusClass"
          />
          <div class="card-info">
            <span class="card-label">{{ card.label }}</span>
            <span class="card-detail">{{ card.detail }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="editor-section">
      <div class="section-head">
        <span>记忆文件编辑</span>
      </div>

      <a-collapse
        v-model:active-key="activePanels"
        :bordered="false"
        class="memory-collapse"
      >
        <a-collapse-panel
          key="story-state"
          header="故事状态 (story-state.md)"
        >
          <template #extra>
            <button
              class="btn-save-inline"
              :disabled="!projectId || savingState === 'story-state'"
              @click.stop="saveStoryState"
            >
              {{ savingState === 'story-state' ? '保存中...' : '保存' }}
            </button>
          </template>
          <textarea
            v-model="storyStateContent"
            class="memory-editor"
            placeholder="# 故事状态&#10;&#10;记录当前故事状态：主要人物位置、已发生的关键事件、下一步计划等..."
          />
        </a-collapse-panel>

        <a-collapse-panel
          key="recent-context"
          header="近期上下文 (recent-context.md)"
        >
          <template #extra>
            <div class="panel-extra">
              <span class="entry-count">{{ recentEntries.length }} 条</span>
              <button
                class="btn-save-inline"
                @click.stop="handleAppendContext"
              >
                追加
              </button>
            </div>
          </template>

          <div
            v-if="recentEntries.length === 0"
            class="panel-empty"
          >
            暂无上下文记录
          </div>
          <div
            v-else
            class="entries-list"
          >
            <div
              v-for="(entry, i) in recentEntries"
              :key="`${entry.time}-${i}`"
              class="context-entry"
            >
              <div class="entry-header">
                <span class="entry-time">{{ entry.time }}</span>
                <button
                  class="entry-delete"
                  title="删除"
                  @click="deleteContextEntry(i)"
                >
                  <i class="fa-solid fa-trash" />
                </button>
              </div>
              <div class="entry-content">{{ entry.text }}</div>
            </div>
          </div>

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
        </a-collapse-panel>

        <a-collapse-panel
          key="story-engine"
          header="故事引擎 (story-engine.md)"
        >
          <template #extra>
            <button
              class="btn-save-inline"
              :disabled="!projectId || savingState === 'story-engine'"
              @click.stop="saveStoryEngine"
            >
              {{ savingState === 'story-engine' ? '保存中...' : '保存' }}
            </button>
          </template>
          <textarea
            v-model="storyEngineContent"
            class="memory-editor"
            placeholder="# 故事引擎&#10;&#10;## 人物欲望&#10;- &#10;&#10;## 冲突推进&#10;- &#10;&#10;## 前文记忆&#10;- &#10;&#10;## 阶段性目标&#10;- "
          />
        </a-collapse-panel>

        <a-collapse-panel
          key="style-guide"
          header="文风指南 (style-guide.md)"
        >
          <template #extra>
            <button
              class="btn-save-inline"
              :disabled="!projectId || savingState === 'style-guide'"
              @click.stop="saveStyleGuide"
            >
              {{ savingState === 'style-guide' ? '保存中...' : '保存' }}
            </button>
          </template>
          <textarea
            v-model="styleGuideContent"
            class="memory-editor"
            placeholder="# 文风指南&#10;&#10;定义写作风格、遣词造句偏好、修辞手法等..."
          />
        </a-collapse-panel>
      </a-collapse>
    </section>

    <section class="config-section">
      <div class="section-head">
        <span>记忆配置</span>
      </div>
      <div class="config-item">
        <label class="config-label">上下文保留条数</label>
        <a-slider
          :value="recentContextSceneLimit"
          :min="5"
          :max="30"
          :step="1"
          disabled
          class="config-slider"
        />
        <span class="config-value">{{ recentContextSceneLimit }} 条</span>
      </div>
      <p class="config-hint">
        当前为只读显示，修改需要在 .env 中设置 RECENT_CONTEXT_SCENE_LIMIT
      </p>
    </section>

    <section class="operations-section">
      <div class="section-head">
        <span>手动操作</span>
      </div>
      <div class="operation-buttons">
        <button
          class="btn-operation"
          :disabled="!projectId || isOperating"
          @click="handleManualUpdate"
        >
          <i :class="isOperating ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-rotate'" />
          手动更新记忆
        </button>
        <button
          class="btn-operation secondary"
          :disabled="!projectId || isOperating"
          @click="handleRefreshStatus"
        >
          <i class="fa-solid fa-arrows-rotate" />
          刷新状态
        </button>
      </div>
      <p
        v-if="operationStatus"
        class="operation-status"
      >
        {{ operationStatus }}
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useStoryStateStore } from '@/stores/storyState'
import { useRecentContextStore } from '@/stores/recentContext'
import { useStyleGuideStore } from '@/stores/styleGuide'
import { useNotificationStore } from '@/stores/notification'
import { useWorkflow } from '@/composables/useWorkflow'

interface ContextEntry {
  time: string
  text: string
}

interface MemoryStatusData {
  project_id: string
  story_state_exists: boolean
  recent_context_exists: boolean
  recent_entries_count: number
  story_state_length: number
  recent_context_length: number
  last_updated: number | null
  story_engine_exists: boolean
  story_engine_length: number
  story_engine_mtime: number | null
  style_guide_exists: boolean
  style_guide_length: number
  style_guide_mtime: number | null
  recent_context_scene_limit: number
}

const projectStore = useProjectStore()
const fileStore = useFileStore()
const storyStateStore = useStoryStateStore()
const recentContextStore = useRecentContextStore()
const styleGuideStore = useStyleGuideStore()
const notification = useNotificationStore()
const { getMemoryStatus, updateMemory } = useWorkflow()

const projectId = computed(() => projectStore.currentProject?.id || '')
const isRefreshing = ref(false)
const isOperating = ref(false)
const operationStatus = ref('')

const activePanels = ref<string[]>(['story-state', 'recent-context'])

const storyStateContent = ref('')
const storyEngineContent = ref('')
const styleGuideContent = ref('')
const savingState = ref<string | null>(null)

const showAppendDialog = ref(false)
const appendText = ref('')

const memoryStatus = ref<MemoryStatusData>({
  project_id: '',
  story_state_exists: false,
  recent_context_exists: false,
  recent_entries_count: 0,
  story_state_length: 0,
  recent_context_length: 0,
  last_updated: null,
  story_engine_exists: false,
  story_engine_length: 0,
  story_engine_mtime: null,
  style_guide_exists: false,
  style_guide_length: 0,
  style_guide_mtime: null,
  recent_context_scene_limit: 15,
})

const recentContextSceneLimit = computed(() => memoryStatus.value.recent_context_scene_limit)

const recentEntries = computed<ContextEntry[]>(() => {
  const raw = recentContextStore.content
  if (!raw) return []
  return raw.split(/\n(?=## )/).map((block) => {
    const lines = block.trim().split('\n')
    const time = (lines[0] || '').replace(/^##\s*/, '')
    const text = lines.slice(1).join('\n').trim()
    return { time, text }
  }).filter(e => e.time || e.text)
})

const statusCards = computed(() => {
  const ms = memoryStatus.value
  const cardData = (exists: boolean, label: string, detail: string) => ({
    label,
    detail,
    statusClass: exists ? 'status-green' : 'status-gray',
  })

  return [
    cardData(ms.story_state_exists, '故事状态', ms.story_state_exists
      ? `${formatSize(ms.story_state_length)} · ${formatTime(ms.last_updated)}`
      : '未创建'),
    cardData(ms.recent_context_exists, '近期上下文', ms.recent_context_exists
      ? `${ms.recent_entries_count} 条记录 · ${formatSize(ms.recent_context_length)}`
      : '未创建'),
    cardData(ms.story_engine_exists, '故事引擎', ms.story_engine_exists
      ? `${formatSize(ms.story_engine_length)} · ${formatTime(ms.story_engine_mtime)}`
      : '未创建'),
    cardData(ms.style_guide_exists, '文风指南', ms.style_guide_exists
      ? `${formatSize(ms.style_guide_length)} · ${formatTime(ms.style_guide_mtime)}`
      : '未创建'),
  ]
})

const unsubStoryState = storyStateStore.$subscribe(() => {
  storyStateContent.value = storyStateStore.content
})
const unsubRecentContext = recentContextStore.$subscribe(() => {})
const unsubStyleGuide = styleGuideStore.$subscribe(() => {
  styleGuideContent.value = styleGuideStore.content
})

watch(projectId, (id) => {
  if (id) loadAll()
}, { immediate: true })

onUnmounted(() => {
  unsubStoryState()
  unsubRecentContext()
  unsubStyleGuide()
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  return `${(bytes / 1024).toFixed(1)}KB`
}

function formatTime(mtime: number | null): string {
  if (!mtime) return '-'
  const timestamp = mtime > 10_000_000_000 ? mtime : mtime * 1000
  const diff = Date.now() - timestamp
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  return `${days} 天前`
}

async function loadAll() {
  const id = projectId.value
  if (!id) return

  const status = await getMemoryStatus(id)
  if (status) {
    memoryStatus.value = status as MemoryStatusData
  }

  await Promise.allSettled([
    storyStateStore.load(id).then(() => { storyStateContent.value = storyStateStore.content }),
    recentContextStore.load(id),
    styleGuideStore.load(id).then(() => { styleGuideContent.value = styleGuideStore.content }),
  ])

  try {
    const data = await fileStore.readFile(id, 'story-engine.md')
    storyEngineContent.value = data.content || ''
  } catch {
    storyEngineContent.value = ''
  }
}

async function refreshAll() {
  isRefreshing.value = true
  try {
    await loadAll()
  } finally {
    isRefreshing.value = false
  }
}

async function saveStoryState() {
  const id = projectId.value
  if (!id) return
  savingState.value = 'story-state'
  try {
    storyStateStore.content = storyStateContent.value
    await storyStateStore.save(id)
    notification.success('故事状态已保存')
  } catch {
    notification.error('保存故事状态失败')
  } finally {
    savingState.value = null
  }
}

async function saveStoryEngine() {
  const id = projectId.value
  if (!id) return
  savingState.value = 'story-engine'
  try {
    await fileStore.saveFile(id, 'story-engine.md', storyEngineContent.value)
    notification.success('故事引擎已保存')
  } catch {
    notification.error('保存故事引擎失败')
  } finally {
    savingState.value = null
  }
}

async function saveStyleGuide() {
  const id = projectId.value
  if (!id) return
  savingState.value = 'style-guide'
  try {
    styleGuideStore.content = styleGuideContent.value
    await styleGuideStore.save(id)
    notification.success('文风指南已保存')
  } catch {
    notification.error('保存文风指南失败')
  } finally {
    savingState.value = null
  }
}

function handleAppendContext() {
  showAppendDialog.value = true
  appendText.value = ''
}

async function confirmAppend() {
  const id = projectId.value
  if (!appendText.value.trim() || !id) return
  const timestamp = new Date().toLocaleString('zh-CN')
  const entry = `\n## ${timestamp}\n${appendText.value.trim()}\n`
  recentContextStore.content = recentContextStore.content
    ? `${recentContextStore.content}\n${entry}`
    : entry

  try {
    await recentContextStore.save(id)
    showAppendDialog.value = false
    notification.success('已追加上下文记录')
  } catch {
    notification.error('追加失败')
  }
}

async function deleteContextEntry(index: number) {
  const id = projectId.value
  const raw = recentContextStore.content
  if (!raw || !id) return

  const blocks = raw.split(/\n(?=## )/).filter(Boolean)
  if (index < 0 || index >= blocks.length) return

  blocks.splice(index, 1)
  recentContextStore.content = blocks.join('')

  try {
    await recentContextStore.save(id)
    notification.success('已删除上下文记录')
  } catch {
    notification.error('删除失败')
    recentContextStore.content = raw
  }
}

async function handleManualUpdate() {
  const id = projectId.value
  if (!id) return
  isOperating.value = true
  operationStatus.value = '正在更新记忆...'
  try {
    const result = await updateMemory(id, '', undefined, undefined, false)
    if (result) {
      operationStatus.value = '记忆更新完成'
      await loadAll()
    } else {
      operationStatus.value = '记忆更新失败'
    }
  } catch {
    operationStatus.value = '记忆更新出错'
  } finally {
    isOperating.value = false
  }
}

async function handleRefreshStatus() {
  isOperating.value = true
  operationStatus.value = '正在刷新状态...'
  try {
    await loadAll()
    operationStatus.value = '状态已刷新'
  } finally {
    isOperating.value = false
  }
}
</script>

<style scoped lang="scss">
.memory-settings-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px 8px;
  color: var(--gold-primary, #c9a96e);
  font-size: 13px;
  font-weight: 600;
}

.link-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: transparent;
  color: var(--gold-primary, #c9a96e);
  font-size: 12px;
  border: 1px solid rgba(201, 169, 110, 0.2);
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  transition: opacity 0.2s;
}

.link-btn:hover:not(:disabled) { opacity: 0.75; }
.link-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.dashboard-section,
.editor-section,
.config-section {
  border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.06));
}

.status-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 0 12px 12px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 11px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--border-color, rgba(255,255,255,0.06));
  border-radius: var(--radius-md, 6px);
}

.card-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.card-indicator.status-green { background: #52c41a; box-shadow: 0 0 4px rgba(82, 196, 26, 0.4); }
.card-indicator.status-gray { background: #666; }

.card-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.card-label {
  font-size: 11px;
  color: var(--text-muted-ink, #888);
  line-height: 1.3;
}

.card-detail {
  font-size: 10px;
  color: var(--text-faint, #666);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-section {
  flex: 1;
  overflow-y: auto;
}

.memory-collapse {
  background: transparent !important;

  :deep(.ant-collapse-item) {
    border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.06));
  }

  :deep(.ant-collapse-header) {
    padding: 10px 12px !important;
    color: var(--text-primary, #e0e0e0) !important;
    font-size: 13px;
    font-weight: 500;
    background: rgba(255, 255, 255, 0.015);
  }

  :deep(.ant-collapse-content) {
    background: transparent;
    border-top: 1px solid var(--border-color, rgba(255,255,255,0.04));
  }

  :deep(.ant-collapse-content-box) {
    padding: 8px 10px !important;
  }
}

.panel-extra {
  display: flex;
  align-items: center;
  gap: 8px;
}

.entry-count {
  font-size: 11px;
  color: var(--text-muted-ink, #888);
}

.btn-save-inline {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 3px 10px;
  background: var(--accent-primary, #1677ff);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm, 4px);
  font-size: 11px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-save-inline:hover:not(:disabled) { opacity: 0.85; }
.btn-save-inline:disabled { opacity: 0.5; cursor: not-allowed; }

.memory-editor {
  width: 100%;
  min-height: 160px;
  max-height: 320px;
  background: rgba(0, 0, 0, 0.15);
  color: var(--text-primary, #e0e0e0);
  border: 1px solid var(--border-color, rgba(255,255,255,0.06));
  border-radius: var(--radius-sm, 4px);
  padding: 10px 12px;
  font-family: var(--font-family-ch, inherit);
  font-size: 13px;
  line-height: 1.7;
  resize: vertical;
  outline: none;
}

.memory-editor::placeholder {
  color: var(--text-muted-ink, #666);
}

.panel-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: var(--text-muted-ink, #888);
  font-size: 13px;
  opacity: 0.5;
}

.entries-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.context-entry {
  background: rgba(0, 0, 0, 0.12);
  border-radius: var(--radius-sm, 4px);
  padding: 8px 10px;
}

.entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.entry-time {
  font-size: 10px;
  color: var(--text-muted-ink, #888);
}

.entry-delete {
  background: none;
  color: var(--text-muted-ink, #888);
  font-size: 10px;
  padding: 2px 4px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: color 0.2s;
}

.entry-delete:hover { color: var(--accent-danger, #ff4d4f); }

.entry-content {
  font-size: 12px;
  color: var(--text-primary, #e0e0e0);
  line-height: 1.5;
  white-space: pre-wrap;
}

.append-dialog {
  margin-top: 8px;
  padding: 10px;
  border-top: 1px solid var(--border-color, rgba(255,255,255,0.06));
  background: rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-sm, 4px);
}

.append-dialog textarea {
  width: 100%;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid var(--border-color, rgba(255,255,255,0.06));
  border-radius: var(--radius-sm, 4px);
  padding: 8px;
  color: var(--text-primary, #e0e0e0);
  font-size: 12px;
  resize: vertical;
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
  padding: 4px 12px;
  border: none;
  border-radius: var(--radius-sm, 4px);
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary, #999);
}

.btn-confirm {
  background: var(--accent-primary, #1677ff);
  color: #fff;
}

.btn-confirm:hover { opacity: 0.85; }

.config-section {
  padding-bottom: 10px;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px;
}

.config-label {
  font-size: 12px;
  color: var(--text-muted-ink, #888);
  white-space: nowrap;
  min-width: 90px;
}

.config-slider {
  flex: 1;

  :deep(.ant-slider-disabled) {
    .ant-slider-track { background: var(--gold-primary, #c9a96e) !important; }
    .ant-slider-handle { border-color: var(--gold-primary, #c9a96e) !important; }
  }
}

.config-value {
  font-size: 12px;
  color: var(--text-primary, #e0e0e0);
  white-space: nowrap;
  min-width: 36px;
  text-align: right;
}

.config-hint {
  padding: 2px 14px 0;
  margin: 0;
  font-size: 10px;
  color: var(--text-faint, #555);
  line-height: 1.4;
}

.operations-section {
  padding-bottom: 14px;
}

.operation-buttons {
  display: flex;
  gap: 8px;
  padding: 0 12px 8px;
}

.btn-operation {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
  justify-content: center;
  padding: 8px 12px;
  background: var(--accent-primary, #1677ff);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm, 4px);
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-operation.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary, #999);
}

.btn-operation:hover:not(:disabled) { opacity: 0.85; }
.btn-operation:disabled { opacity: 0.4; cursor: not-allowed; }

.operation-status {
  padding: 0 14px;
  margin: 0;
  font-size: 11px;
  color: var(--text-muted-ink, #888);
  line-height: 1.4;
}
</style>
