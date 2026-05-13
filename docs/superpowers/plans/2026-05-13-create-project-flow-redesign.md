# 新建项目流程改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将新建项目的多步骤弹窗改为「弹窗选参数 → 直接创建项目 + 跳转编辑器 + 流式写入文件」的单步流程

**Architecture:**
- CreateProjectModal 从5步向导精简为单页参数表单
- 点击「生成并打开」后创建 project → 关闭弹窗 → router.push 到编辑器
- 新建 `useFileGeneration` composable 处理编辑器内的流式生成，每个 delta 写入 `editorStore.appendContent`
- 右侧面板通过 `useSSE` 订阅 `generation` 事件，显示当前 prompt 和进度

**Tech Stack:** Vue 3, Pinia, Ant Design Vue, SSE, fetch streaming

---

### Task 1: 精简 useProjectWizard.ts

**Files:**
- Modify: `frontend/src/composables/useProjectWizard.ts`

去掉多步骤管理状态（currentStep, bookIdea, outline, editedOutline）和对应方法，只保留 params 表单状态。

- [ ] **Step 1: 重写 useProjectWizard**

```typescript
import { ref } from 'vue'
import { useProjectStore } from '@/stores/project'

export const useProjectWizard = () => {
  const projectStore = useProjectStore()

  // 创作参数（保留现有所有字段）
  const params = ref({
    genre: '',
    tone: '',
    background: '',
    theme: '',
    writing_style: '',
    author: '',
    target_word_count: 50000,
  })

  const isGenerating = ref(false)

  async function createProject(params: typeof params.value) {
    if (!params.genre) {
      throw new Error('请选择题材')
    }
    isGenerating.value = true
    try {
      const project = await projectStore.createProject({
        name: '新项目', // 后端生成书名后会更新
        genre: params.genre,
        tone: params.tone,
        background: params.background,
        theme: params.theme,
        writing_style: params.writing_style,
        author: params.author,
        target_word_count: params.target_word_count,
      })
      return project
    } finally {
      isGenerating.value = false
    }
  }

  function reset() {
    params.value = {
      genre: '',
      tone: '',
      background: '',
      theme: '',
      writing_style: '',
      author: '',
      target_word_count: 50000,
    }
    isGenerating.value = false
  }

  return {
    params,
    isGenerating,
    createProject,
    reset,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useProjectWizard.ts
git commit -m "refactor: 精简 useProjectWizard，移除多步骤管理"
```

---

### Task 2: 重写 CreateProjectModal.vue

**Files:**
- Modify: `frontend/src/components/modals/CreateProjectModal.vue`

去掉多步骤模板和逻辑，改为单页参数表单 + 「生成并打开」按钮。

- [ ] **Step 1: 重写 template**

去掉 `v-if="wizard.currentStep.value <= 1"` / `step 1.5` / `step 2` / `step 2.5` / `step 3` 所有多步骤区块。

保留 `<a-form>` 中的参数表单（genre, tone, writing_style, background, theme, target_word_count, author）。

footer 改为一个按钮：

```html
<template #footer>
  <div style="display: flex; justify-content: flex-end; gap: 12px;">
    <a-button
      type="primary"
      :disabled="!wizard.params.value.genre || wizard.isGenerating.value"
      :loading="wizard.isGenerating.value"
      @click="handleCreate"
    >
      <template #icon>
        <i class="fa-solid fa-magic"></i>
      </template>
      {{ wizard.isGenerating.value ? '创建中...' : '生成并打开' }}
    </a-button>
  </div>
</template>
```

- [ ] **Step 2: 重写 script**

```typescript
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectWizard } from '@/composables/useProjectWizard'
import { useUIStore } from '@/stores/ui'
import { useFileStore } from '@/stores/file'
import { useCustomParamsStore } from '@/stores/customParams'
import { useNotificationStore } from '@/stores/notification'
import { useProjectStore } from '@/stores/project'

const wizard = useProjectWizard()
const uiStore = useUIStore()
const fileStore = useFileStore()
const customParamsStore = useCustomParamsStore()
const notification = useNotificationStore()
const projectStore = useProjectStore()
const router = useRouter()

const visible = computed(() => uiStore.modals.createProject)

// 所有 options 保留
const genreOptions = computed(() => customParamsStore.getOptions('genre'))
const toneOptions = computed(() => customParamsStore.getOptions('tone'))
const styleOptions = computed(() => customParamsStore.getOptions('writing_style'))
const bgOptions = computed(() => customParamsStore.getOptions('background'))
const themeOptions = computed(() => customParamsStore.getOptions('theme'))
const scaleOptions = [
  { label: '5万字', value: 50000, hint: '≈ 28章' },
  { label: '10万字', value: 100000, hint: '≈ 56章' },
  { label: '15万字', value: 150000, hint: '≈ 84章' },
  { label: '20万字', value: 200000, hint: '≈ 112章' },
]

// 删除 stepTitle, stepIcon, createdProjectName, startGenerate, proceedToOutline, startCreateProject 等

async function handleCreate() {
  try {
    const project = await wizard.createProject(wizard.params.value)
    if (!project) return

    // 创建书名与创意文件
    await fileStore.createFile(project.id, '书名与创意.md', '')

    // 记录需要在项目打开后自动生成
    projectStore.setPendingGeneration({
      filePath: '书名与创意.md',
      prompt: `你是一位专业的小说创作助手。用户选择了「${wizard.params.value.genre}」题材，请生成一个吸引人的书名和创意描述。`,
    })

    // 关闭弹窗
    close()

    // 跳转到编辑器
    router.push(`/project/${project.id}`)
  } catch (e: any) {
    notification.error(e.message || '创建项目失败')
  }
}

function close() {
  wizard.reset()
  uiStore.closeCreateProject()
}

// editingCategory, newOptionInput, toggleEditCategory, addCustomOption, removeCustomOption 保留
```

- [ ] **Step 3: 清理 template step 标题**

```html
<template #title>
  <span style="display: flex; align-items: center; gap: 10px;">
    <i class="fa-solid fa-feather-pointed" style="color: var(--accent-primary);"></i>
    新建项目 - 创作参数
  </span>
</template>
```

- [ ] **Step 4: 清理不再使用的 import 和 watch**

移除：watch 监听 step 变化、`createdProjectName`、`stepTitle`、`stepIcon` 等。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/modals/CreateProjectModal.vue
git commit -m "feat: CreateProjectModal 改为单页，点击生成直接创建项目并跳转编辑器"
```

---

### Task 3: 添加 pendingGeneration 状态到 projectStore

**Files:**
- Modify: `frontend/src/stores/project.ts`

- [ ] **Step 1: 添加 pendingGeneration 状态**

```typescript
// 在 useProjectStore 的 ref 区域添加
const pendingGeneration = ref<{ filePath: string; prompt: string } | null>(null)

function setPendingGeneration(val: { filePath: string; prompt: string } | null) {
  pendingGeneration.value = val
}

// 在 return 中添加
return {
  // ... 现有所有 return ...
  pendingGeneration,
  setPendingGeneration,
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/project.ts
git commit -m "feat: 添加 pendingGeneration 状态，用于项目创建后自动触发流式生成"
```

---

### Task 4: 创建 useFileGeneration composable

**Files:**
- Create: `frontend/src/composables/useFileGeneration.ts`

处理编辑器内的流式生成：调用 `/api/generate`，每个 delta 写入 `editorStore.appendContent`。

- [ ] **Step 1: 创建 useFileGeneration.ts**

```typescript
import { ref } from 'vue'
import { useEditorStore } from '@/stores/editor'

/**
 * 文件生成 composable
 * 与 chatStore.continueWriting 类似，但将内容流式写入编辑器文件而非聊天面板
 */
export function useFileGeneration() {
  const editorStore = useEditorStore()
  const isGenerating = ref(false)
  const currentPrompt = ref('')
  const progress = ref({ current: 0, total: 0 })
  let abortController: AbortController | null = null

  /**
   * 对指定文件进行流式生成
   */
  async function generateToFile(
    projectId: string,
    filePath: string,
    prompt?: string,
  ) {
    if (isGenerating.value) return

    isGenerating.value = true
    currentPrompt.value = prompt || ''
    abortController = new AbortController()

    try {
      // 确保编辑器已打开该文件
      editorStore.setCurrentFile(filePath)

      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          file_path: filePath,
          prompt_type: 'generate/chapter',
          extra_vars: prompt ? { user_prompt: prompt } : {},
          mode: 'append',
          stream: true,
        }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      await parseSSEStream(reader, (delta) => {
        editorStore.appendContent(delta)
      })

      isGenerating.value = false
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // 用户取消，不报错
      } else {
        throw e
      }
    } finally {
      isGenerating.value = false
      abortController = null
    }
  }

  function cancelGeneration() {
    abortController?.abort()
    isGenerating.value = false
  }

  /**
   * 解析 SSE 流，提取 delta 内容
   */
  async function parseSSEStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onDelta: (delta: string) => void,
  ): Promise<void> {
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6))
            if (parsed.delta) {
              onDelta(parsed.delta)
            } else if (parsed.content) {
              onDelta(parsed.content)
            }
          } catch {
            // 跳过非 JSON 行
          }
        }
      }
    }
  }

  return {
    isGenerating,
    currentPrompt,
    progress,
    generateToFile,
    cancelGeneration,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useFileGeneration.ts
git commit -m "feat: 创建 useFileGeneration composable，支持流式写入编辑器文件"
```

---

### Task 5: 在 App.vue 中监听 pendingGeneration 自动触发生成

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 检查现有 App.vue 内容**

```bash
cat frontend/src/App.vue
```

- [ ] **Step 2: 添加 pendingGeneration 监听**

在 App.vue 的 script setup 中：

```typescript
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useFileGeneration } from '@/composables/useFileGeneration'

const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const fileGen = useFileGeneration()
const router = useRouter()

// 监听 pendingGeneration：项目创建后自动触发流式生成
watch(
  () => projectStore.pendingGeneration,
  async (pending) => {
    if (!pending || !projectStore.currentProject) return

    const projectId = projectStore.currentProject.id
    const { filePath, prompt } = pending

    // 等待路由导航完成 + 文件树加载
    await new Promise(resolve => setTimeout(resolve, 500))

    // 打开文件
    const node = { name: filePath.split('/').pop() || '', path: filePath, type: 'file' as const }
    fileStore.openFile(node)
    editorStore.setCurrentFile(filePath)

    try {
      // 读取文件（刚创建的空文件）
      await fileStore.readFile(projectId, filePath)
    } catch {
      // 文件可能尚未在后端就绪，忽略
    }

    // 触发流式生成
    try {
      await fileGen.generateToFile(projectId, filePath, prompt)
    } catch (e: any) {
      console.error('自动生成失败:', e)
    }

    // 清除 pending 标记
    projectStore.setPendingGeneration(null)
  },
)
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: 监听 pendingGeneration，项目创建后自动流式生成书名与创意"
```

---

### Task 6: 右侧面板显示生成状态和 Prompt

**Files:**
- Modify: `frontend/src/components/right-panel/RightPanel.vue`

- [ ] **Step 1: 读取 RightPanel.vue 当前内容**

```bash
cat frontend/src/components/right-panel/RightPanel.vue
```

- [ ] **Step 2: 在右侧面板添加「生成信息」区域**

在现有面板内容的基础上（保持布局不变），新增一个区块展示生成状态：

```html
<!-- 生成信息区块（生成中显示） -->
<div v-if="fileGen.isGenerating.value" class="panel-section">
  <div class="panel-section-header">
    <i class="fa-solid fa-wand-magic-sparkles"></i>
    <span>生成中</span>
  </div>
  <div class="panel-section-body">
    <div class="prompt-display">
      <div class="prompt-label">Prompt</div>
      <div class="prompt-text">{{ fileGen.currentPrompt.value }}</div>
    </div>
    <div class="generation-progress">
      <a-spin size="small" />
      <span>正在生成...</span>
    </div>
  </div>
</div>
```

```typescript
// script setup 中引入
import { useFileGeneration } from '@/composables/useFileGeneration'
const fileGen = useFileGeneration()
```

- [ ] **Step 3: 添加 scoped 样式**

```scss
.prompt-display {
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  padding: 10px;
  margin-bottom: 8px;
}

.prompt-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.prompt-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.generation-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--accent-primary);
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/right-panel/RightPanel.vue
git commit -m "feat: 右侧面板显示生成状态和当前 prompt"
```

---

### Self-Review

**1. Spec coverage:**
- 弹窗改为单页 ✅ (Task 1, 2)
- 点击生成后创建项目 ✅ (Task 2)
- 跳转编辑器 ✅ (Task 2: router.push)
- 自动流式写入 ✅ (Task 4, 5)
- 右侧面板显示 prompt ✅ (Task 6)
- 用户可通过聊天调整（已有功能，无需改动）

**2. Placeholder scan:** No TBD, TODO, or vague sections found.

**3. Type consistency:**
- `projectStore.pendingGeneration`: `{ filePath: string; prompt: string } | null` — consistently used across Task 2 (set), Task 3 (state), Task 5 (read)
- `useFileGeneration` composable returns reactive refs, used in Task 5 and Task 6
- `router.push` string path matches route definition in router/index.ts (`/project/:projectId`)
