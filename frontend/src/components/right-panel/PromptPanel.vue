<template>
  <div class="prompt-panel">
    <!-- Prompt 历史 -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">Prompt 历史</span>
        <button class="btn-icon" @click="clearHistory" title="清空">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>

      <div v-if="promptHistory.length === 0" class="section-empty">
        <i class="fa-solid fa-clock-rotate-left"></i>
        <span>暂无历史</span>
      </div>

      <div v-else class="prompt-list">
        <div
          v-for="(item, index) in promptHistory"
          :key="index"
          class="prompt-item"
          @click="copyPrompt(item)"
        >
          <div class="prompt-preview">{{ truncate(item, 100) }}</div>
          <button class="btn-copy" title="复制">
            <i class="fa-solid fa-copy"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- 当前 Prompt -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">当前 Prompt</span>
        <div class="header-actions">
          <button class="btn-icon" @click="sendToAI" title="发送到 AI" :disabled="!currentPrompt">
            <i class="fa-solid fa-paper-plane"></i>
          </button>
          <button class="btn-icon" @click="copyCurrentPrompt" title="复制">
            <i class="fa-solid fa-copy"></i>
          </button>
        </div>
      </div>
      <div class="prompt-current">
        <pre v-if="currentPrompt">{{ currentPrompt }}</pre>
        <span v-else class="empty-text">暂无内容</span>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">快捷操作</span>
      </div>
      <div class="quick-actions">
        <button class="quick-btn" @click="insertChapterTemplate">
          <i class="fa-solid fa-file-lines"></i>
          <span>章节模板</span>
        </button>
        <button class="quick-btn" @click="insertCharacterTemplate">
          <i class="fa-solid fa-user"></i>
          <span>角色模板</span>
        </button>
        <button class="quick-btn" @click="insertWorldTemplate">
          <i class="fa-solid fa-globe"></i>
          <span>世界观</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'
import { useEditorStore } from '@/stores/editor'

const rightPanelStore = useRightPanelStore()
const notification = useNotificationStore()
const chatStore = useChatStore()
const editorStore = useEditorStore()

const promptHistory = computed(() => rightPanelStore.promptHistory)
const currentPrompt = computed(() => rightPanelStore.currentPrompt)

async function sendToAI() {
  if (!currentPrompt.value) {
    notification.warning('暂无 Prompt 内容')
    return
  }
  try {
    await chatStore.sendMessage(currentPrompt.value)
  } catch (e) {
    notification.error('发送失败')
  }
}

function truncate(text: string, length: number): string {
  return text.length > length ? text.substring(0, length) + '...' : text
}

function copyPrompt(text: string) {
  navigator.clipboard.writeText(text)
  notification.success('已复制到剪贴板')
}

function copyCurrentPrompt() {
  if (currentPrompt.value) {
    copyPrompt(currentPrompt.value)
  }
}

function clearHistory() {
  rightPanelStore.clearHistory()
  notification.success('历史已清空')
}

function insertChapterTemplate() {
  const template = `## 第X章 标题

### 章节概述
本章主要讲述...

### 目标字数
约 3000 字

### 情节点
- [ ] 情节点1
- [ ] 情节点2

### 角色出场
- 角色A
- 角色B

### 章节内容
`
  rightPanelStore.loadPromptTemplate(template)
  editorStore.insertContent(template)
  notification.success('章节模板已插入')
}

function insertCharacterTemplate() {
  const template = `## 角色名称

### 基本信息
- 年龄：
- 性别：
- 外貌：
- 性格：

### 背景故事


### 人物关系


### 角色弧线


### 经典台词

`
  rightPanelStore.loadPromptTemplate(template)
  editorStore.insertContent(template)
  notification.success('角色模板已插入')
}

function insertWorldTemplate() {
  const template = `## 世界观设定

### 时代背景


### 地理环境


### 社会结构


### 规则设定
- 规则1
- 规则2

### 特殊设定

`
  rightPanelStore.loadPromptTemplate(template)
  editorStore.insertContent(template)
  notification.success('世界观模板已插入')
}
</script>

<style scoped lang="scss">
.prompt-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-section {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);

  &:last-child {
    border-bottom: none;
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 12px;

  &:hover {
    background: var(--bg-card);
    color: var(--text-primary);
  }
}

.section-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;

  i {
    font-size: 24px;
    opacity: 0.5;
  }
}

.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.prompt-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--bg-primary);

    .btn-copy {
      opacity: 1;
    }
  }
}

.prompt-preview {
  flex: 1;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.btn-copy {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  opacity: 0;
  transition: all 0.2s;

  &:hover {
    color: var(--accent-primary);
  }
}

.prompt-current {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 12px;
  max-height: 150px;
  overflow-y: auto;

  pre {
    font-size: 12px;
    line-height: 1.6;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
    font-family: inherit;
    margin: 0;
  }

  .empty-text {
    font-size: 13px;
    color: var(--text-muted);
  }
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.quick-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: var(--bg-card);
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;

  i {
    font-size: 16px;
    color: var(--accent-primary);
  }

  &:hover {
    background: var(--accent-primary);
    color: white;

    i {
      color: white;
    }
  }
}
</style>
