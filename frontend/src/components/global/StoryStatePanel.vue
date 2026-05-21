<template>
  <div class="story-state-panel">
    <div class="panel-header">
      <h3>故事状态</h3>
      <div class="panel-actions">
        <button
          class="btn-action"
          :disabled="isSaving"
          @click="handleSave"
        >
          <i class="fa-solid fa-save" /> 保存
        </button>
        <button
          class="btn-action secondary"
          @click="autoGenerate"
        >
          <i class="fa-solid fa-wand-magic-sparkles" /> AI 更新
        </button>
      </div>
    </div>

    <div class="panel-content">
      <div
        v-if="isLoading"
        class="panel-loading"
      >
        <i class="fa-solid fa-spinner fa-spin" /> 加载中...
      </div>
      <textarea
        v-else
        v-model="content"
        class="state-editor"
        placeholder="记录当前故事状态：主要人物位置、已发生的关键事件、下一步计划等..."
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useStoryStateStore } from '@/stores/storyState'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import { useEditorStore } from '@/stores/editor'

const storyStateStore = useStoryStateStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()
const editorStore = useEditorStore()

const content = ref(storyStateStore.content)
const isLoading = ref(false)
const isSaving = ref(false)

const unsubscribe = storyStateStore.$subscribe(() => {
  content.value = storyStateStore.content
})

onUnmounted(() => {
  unsubscribe()
})

async function loadState() {
  if (!projectStore.currentProject) return
  isLoading.value = true
  try {
    await storyStateStore.load(projectStore.currentProject.id)
    content.value = storyStateStore.content
  } finally {
    isLoading.value = false
  }
}

async function handleSave() {
  if (!projectStore.currentProject) return
  isSaving.value = true
  try {
    storyStateStore.content = content.value
    await storyStateStore.save(projectStore.currentProject.id)
    notification.success('故事状态已保存')
  } catch {
    notification.error('保存失败')
  } finally {
    isSaving.value = false
  }
}

async function autoGenerate() {
  if (!projectStore.currentProject) return
  const filePath = editorStore.currentFilePath
  const chapterContent = filePath ? editorStore.getContent(filePath).trim() : ''
  if (!filePath || !chapterContent) {
    notification.warning('请先打开有正文的章节')
    return
  }

  isSaving.value = true
  try {
    await storyStateStore.updateAfterChapter(
      projectStore.currentProject.id,
      chapterContent,
      filePath,
    )
    content.value = storyStateStore.content
    notification.success('故事状态已根据当前场景更新')
  } catch {
    notification.error('故事状态更新失败')
  } finally {
    isSaving.value = false
  }
}

defineExpose({ loadState })
</script>

<style scoped>
.story-state-panel {
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
  gap: 8px;
  flex-wrap: wrap;
}

.panel-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.panel-actions {
  display: flex;
  gap: 6px;
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
  transition: background 0.2s;
}

.btn-action.secondary {
  background: var(--bg-card);
  color: var(--text-secondary);
}

.btn-action:hover:not(:disabled) { opacity: 0.85; }
.btn-action:disabled { opacity: 0.5; cursor: not-allowed; }

.panel-content {
  flex: 1;
  overflow: hidden;
}

.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  color: var(--text-muted);
}

.state-editor {
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
  color: var(--text-primary);
  border: none;
  padding: 16px;
  font-family: var(--font-family-ch);
  font-size: 14px;
  line-height: 1.7;
  resize: none;
  outline: none;
}

.state-editor::placeholder {
  color: var(--text-muted);
}
</style>
