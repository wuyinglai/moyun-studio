<template>
  <div class="style-guide-panel">
    <div class="panel-header">
      <h3>文风指南</h3>
      <div class="panel-actions">
        <button
          class="btn-action"
          :disabled="isSaving"
          @click="handleSave"
        >
          <i class="fa-solid fa-save" /> 保存
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

      <div
        v-else
        class="editor-wrapper"
      >
        <textarea
          v-model="content"
          class="guide-editor"
          placeholder="在此编写文风指南...

示例：
## 语言风格
- 使用简洁有力的短句
- 避免过度华丽的修辞
- 对话自然流畅，符合人物性格

## 叙事视角
- 采用第三人称有限视角
- 心理描写适度，点到即止

## 用词规范
- 避免网络流行语
- 人名、地名等专有名词统一"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useStyleGuideStore } from '@/stores/styleGuide'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'

const styleGuideStore = useStyleGuideStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()

const content = ref(styleGuideStore.content)
const isLoading = ref(false)
const isSaving = ref(false)

// 同步 store 变化
const unsubscribe = styleGuideStore.$subscribe(() => {
  content.value = styleGuideStore.content
})

onUnmounted(() => {
  unsubscribe()
})

async function loadGuide() {
  if (!projectStore.currentProject) return
  isLoading.value = true
  try {
    await styleGuideStore.load(projectStore.currentProject.id)
    content.value = styleGuideStore.content
  } finally {
    isLoading.value = false
  }
}

async function handleSave() {
  if (!projectStore.currentProject) return
  isSaving.value = true
  try {
    styleGuideStore.content = content.value
    await styleGuideStore.save(projectStore.currentProject.id)
    notification.success('文风指南已保存')
  } catch {
    notification.error('保存失败')
  } finally {
    isSaving.value = false
  }
}

defineExpose({ loadGuide })
</script>

<style scoped>
.style-guide-panel {
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

.panel-actions {
  display: flex;
  gap: 8px;
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

.btn-action:hover:not(:disabled) { filter: brightness(1.15); }
.btn-action:disabled { opacity: 0.5; cursor: not-allowed; }

.panel-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  color: var(--text-muted);
}

.editor-wrapper {
  flex: 1;
  overflow: hidden;
}

.guide-editor {
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

.guide-editor::placeholder {
  color: var(--text-muted);
}
</style>
