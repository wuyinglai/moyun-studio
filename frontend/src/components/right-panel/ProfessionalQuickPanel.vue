<template>
  <div class="professional-quick-panel">
    <section class="quick-section">
      <div class="section-head">
        <span>当前写作</span>
        <button
          class="link-btn"
          :disabled="!projectId"
          @click="refreshEngine"
        >
          刷新
        </button>
      </div>
      <div class="current-file">
        <strong>{{ currentFileLabel }}</strong>
        <p>{{ currentFileHint }}</p>
      </div>
      <div class="action-grid">
        <button
          class="quick-action primary"
          :disabled="!canGenerate || running"
          @click="handleContinue"
        >
          <i class="fa-solid fa-pen-nib" />
          <span>{{ continueLabel }}</span>
        </button>
        <button
          class="quick-action"
          :disabled="!canGenerate || running"
          @click="handleRewrite"
        >
          <i class="fa-solid fa-rotate" />
          <span>{{ rewriteLabel }}</span>
        </button>
        <button
          class="quick-action"
          :disabled="!canGenerate || running"
          @click="handleBoost"
        >
          <i class="fa-solid fa-bolt" />
          <span>补强爽点</span>
        </button>
        <button
          class="quick-action"
          :disabled="!projectId"
          @click="openStoryEngine"
        >
          <i class="fa-solid fa-compass" />
          <span>故事引擎</span>
        </button>
        <button
          class="quick-action"
          :disabled="!projectId"
          @click="openStoryState"
        >
          <i class="fa-solid fa-book-open" />
          <span>故事状态</span>
        </button>
        <button
          class="quick-action"
          :disabled="!projectId"
          @click="openCurrentPlan"
        >
          <i class="fa-solid fa-route" />
          <span>章规划</span>
        </button>
      </div>
      <p
        v-if="statusText"
        class="status-line"
      >
        {{ statusText }}
      </p>
    </section>

    <section class="quick-section">
      <div class="section-head">
        <span>故事引擎摘要</span>
        <button
          class="link-btn"
          :disabled="!projectId"
          @click="openStoryEngine"
        >
          编辑
        </button>
      </div>
      <dl class="engine-summary">
        <dt>人物欲望</dt>
        <dd>{{ engineSummary.desire }}</dd>
        <dt>冲突推进</dt>
        <dd>{{ engineSummary.conflict }}</dd>
        <dt>前文记忆</dt>
        <dd>{{ engineSummary.memory }}</dd>
        <dt>阶段目标</dt>
        <dd>{{ engineSummary.goal }}</dd>
      </dl>
    </section>

    <section class="quick-section compact">
      <div class="section-head">
        <span>专业能力</span>
      </div>
      <div class="nav-actions">
        <button @click="rightPanelStore.setActiveTab('workflow')">
          工作流编排
        </button>
        <button @click="rightPanelStore.setActiveTab('pipeline')">
          管线编辑
        </button>
        <button @click="rightPanelStore.setActiveTab('prompt')">
          Prompt 调整
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore, type FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useGenerationStore } from '@/stores/generation'
import { useNotificationStore } from '@/stores/notification'
import { useRightPanelStore } from '@/stores/rightPanel'
import { parseScenePath, buildChapterPlanPath } from '@/modules/scene/scenePath'
import { useFileGeneration } from '@/composables/useFileGeneration'

const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const generationStore = useGenerationStore()
const notification = useNotificationStore()
const rightPanelStore = useRightPanelStore()
const fileGen = useFileGeneration()

const running = ref(false)
const statusText = ref('')
const engineSummary = reactive({
  desire: '待补充',
  conflict: '待补充',
  memory: '待补充',
  goal: '待补充',
})

const projectId = computed(() => projectStore.currentProject?.id || '')
const currentFilePath = computed(() => fileStore.currentFile?.path || editorStore.currentFilePath || '')
const currentFileLabel = computed(() => currentFilePath.value || '尚未打开文件')
const canGenerate = computed(() => Boolean(projectId.value && currentFilePath.value))
const isChapterFile = computed(() => /chapters\/.*\/sec-\d+\.md$/.test(currentFilePath.value))
const continueLabel = computed(() => isChapterFile.value ? '续写当前场景' : '续写当前文件')
const rewriteLabel = computed(() => isChapterFile.value ? '重写当前场景' : '重写当前文件')
const currentFileHint = computed(() => {
  if (!projectId.value) return '打开项目后可使用专业快捷操作。'
  if (!currentFilePath.value) return '从文件树打开一个场景或素材文件。'
  return '专业版不要求先写大纲，可以围绕当前文件直接生成、重写和补强。'
})

watch(projectId, () => {
  void refreshEngine()
}, { immediate: true })

onMounted(() => {
  void refreshEngine()
})

function firstLineOfSection(text: string, name: string) {
  const pattern = new RegExp(`## ${name}\\n(?<body>[\\s\\S]*?)(?=\\n## |$)`)
  const match = text.match(pattern)
  const body = match?.groups?.body || ''
  const line = body
    .split(/\r?\n/)
    .map(item => item.replace(/^[-*]\s*/, '').trim())
    .find(Boolean)
  return line || '待补充'
}

async function refreshEngine() {
  if (!projectId.value) return
  try {
    const data = await fileStore.readFile(projectId.value, 'story-engine.md')
    const text = data.content || ''
    engineSummary.desire = firstLineOfSection(text, '人物欲望')
    engineSummary.conflict = firstLineOfSection(text, '冲突推进')
    engineSummary.memory = firstLineOfSection(text, '前文记忆')
    engineSummary.goal = firstLineOfSection(text, '阶段性目标')
  } catch {
    engineSummary.desire = '尚未创建 story-engine.md'
    engineSummary.conflict = '可从爽文模式生成，也可在专业版手动维护。'
    engineSummary.memory = '待补充'
    engineSummary.goal = '待补充'
  }
}

function currentChapterPlanPath() {
  const file = currentFilePath.value
  const info = parseScenePath(file)
  if (info) return buildChapterPlanPath(info.volume, info.chapter)
  // fallback: 从路径中提取 vol/ch
  const vol = file.match(/vol-(\d+)/)?.[1] || '01'
  const ch = file.match(/ch-(\d+)/)?.[1] || '001'
  return `chapters/vol-${vol}/ch-${ch}/ch-plan.md`
}

async function openFile(path: string, fallbackContent = '') {
  if (!projectId.value) return
  let content = fallbackContent
  try {
    const data = await fileStore.readFile(projectId.value, path)
    content = data.content || fallbackContent
  } catch {
    if (fallbackContent) {
      await fileStore.createFile(projectId.value, path, fallbackContent)
      await fileStore.loadTree(projectId.value)
    }
  }
  const node: FileNode = { name: path.split('/').pop() || path, path, type: 'file' }
  fileStore.openFile(node)
  editorStore.setCurrentFile(path)
  editorStore.loadContent(path, content)
}

async function openStoryEngine() {
  await openFile('story-engine.md', [
    '# 故事引擎',
    '',
    '## 人物欲望',
    '- ',
    '',
    '## 冲突推进',
    '- ',
    '',
    '## 场景直觉',
    '- ',
    '',
    '## 前文记忆',
    '- ',
    '',
    '## 读者期待',
    '- ',
    '',
    '## 阶段性目标',
    '- ',
  ].join('\n'))
}

async function openStoryState() {
  await openFile('story-state.md', '# 故事状态\n\n')
  rightPanelStore.setActiveTab('story')
}

async function openCurrentPlan() {
  await openFile(currentChapterPlanPath(), '# 章规划\n\n')
}

async function runAction(label: string, runner: () => Promise<void>) {
  if (!canGenerate.value || running.value) return
  running.value = true
  statusText.value = `${label}已发送，重写类结果会先进入候选稿。`
  try {
    await runner()
    notification.success(statusText.value)
  } catch (e: unknown) {
    statusText.value = (e instanceof Error ? e.message : '') || `${label}失败`
    notification.error(statusText.value)
  } finally {
    running.value = false
  }
}

async function handleContinue() {
  await runAction('续写当前场景', () => generationStore.continueWriting(
    projectId.value,
    currentFilePath.value,
    '请基于故事引擎和前文记忆，继续写当前场景；优先推进人物欲望、冲突和读者期待，不需要依赖大纲。',
  ))
}

async function handleRewrite() {
  await runAction('重写当前场景', async () => {
    rightPanelStore.setActiveTab('candidate')
    await fileGen.runPipeline(
      projectId.value,
      currentFilePath.value,
      'rewrite',
      { user_prompt: '请在保留核心事件的基础上重写当前文件，增强人物动机、场景行动和场景钩子。' },
      'candidate',
    )
  })
}

async function handleBoost() {
  await runAction('补强爽点', async () => {
    rightPanelStore.setActiveTab('candidate')
    await fileGen.runPipeline(
      projectId.value,
      currentFilePath.value,
      'rewrite',
      { user_prompt: '请生成一版候选稿：保留当前场景核心事件，加强冲突压力、主角反击的爽点兑现，以及下一场景钩子。不要直接覆盖原文。' },
      'candidate',
    )
  })
}
</script>

<style scoped lang="scss">
.professional-quick-panel {
  height: 100%;
  overflow: auto;
  padding: 12px;
  color: var(--text-primary);
}

.quick-section {
  padding: 13px;
  margin-bottom: 12px;
  border: 1px solid var(--border-ink);
  border-radius: 8px;
  background: rgba(255, 255, 255, .025);
}

.quick-section.compact {
  padding-bottom: 10px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  color: var(--gold-primary);
  font-size: 13px;
  font-weight: 600;
}

.current-file {
  padding: 10px;
  border-radius: 7px;
  background: rgba(0, 0, 0, .16);
}

.current-file strong {
  display: block;
  font-size: 14px;
  line-height: 1.45;
  word-break: break-all;
}

.current-file p,
.status-line {
  margin: 6px 0 0;
  color: var(--text-muted-ink);
  font-size: 12px;
  line-height: 1.55;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.quick-action,
.nav-actions button,
.link-btn {
  border: 1px solid var(--border-ink);
  border-radius: 6px;
  cursor: pointer;
}

.quick-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 38px;
  padding: 8px;
  background: rgba(255, 255, 255, .025);
  color: var(--text-primary);
  font-size: 13px;
}

.quick-action.primary {
  border-color: rgba(201, 169, 110, .45);
  color: var(--gold-primary);
}

.quick-action:disabled {
  cursor: not-allowed;
  opacity: .45;
}

.engine-summary {
  display: grid;
  gap: 7px;
  margin: 0;
}

.engine-summary dt {
  color: var(--gold-primary);
  font-size: 12px;
}

.engine-summary dd {
  margin: 0 0 4px;
  color: var(--text-muted-ink);
  font-size: 13px;
  line-height: 1.5;
}

.nav-actions {
  display: grid;
  gap: 8px;
}

.nav-actions button {
  padding: 8px 10px;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
}

.link-btn {
  padding: 4px 7px;
  background: transparent;
  color: var(--gold-primary);
  font-size: 12px;
}

.link-btn:disabled {
  cursor: not-allowed;
  opacity: .45;
}
</style>
