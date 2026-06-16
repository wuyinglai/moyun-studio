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
      <p class="safety-hint">
        <i class="fa-solid fa-shield-halved" />
        生成结果会先保存为候选稿，不会直接覆盖正文。
      </p>
      <details class="beat-input-box">
        <summary>
          <span>本场信息点</span>
          <em v-if="hasBeatInput">已启用检查</em>
        </summary>
        <p class="beat-input-hint">
          用于生成后检查候选稿是否漏掉关键信息。留空则不启用检查。
        </p>
        <p class="beat-input-summary">
          {{ beatInputSummary }}
        </p>
        <p
          v-if="hasLongBeatLine"
          class="beat-input-warning"
        >
          单条信息点过长，建议拆成多行，模型会更容易遵守。
        </p>
        <label class="beat-input-field">
          <span>本场必须出现</span>
          <textarea
            v-model="requiredBeatsText"
            data-testid="required-beats-input"
            rows="3"
            placeholder="每行一个必须出现的信息点，例如：第七层协议必须被提及"
          />
        </label>
        <label class="beat-input-field">
          <span>本场禁止出现 / 禁止揭晓</span>
          <textarea
            v-model="forbiddenBeatsText"
            data-testid="forbidden-beats-input"
            rows="3"
            placeholder="每行一个禁止项，例如：不能提前揭晓幕后人物身份"
          />
        </label>
      </details>
      <details
        class="anchor-input-box"
        data-testid="continuity-anchors-section"
      >
        <summary>
          <span>连续性锚点</span>
          <em>{{ continuityAnchorCountText }}</em>
        </summary>
        <p class="beat-input-hint">
          用于长期约束人物状态、线索、道具归属、关系和世界规则。生成时只注入 active 锚点。
        </p>
        <div class="anchor-form">
          <label class="beat-input-field">
            <span>标题</span>
            <input
              v-model="newAnchorTitle"
              data-testid="continuity-anchor-title"
              placeholder="例如：沈知夏左臂受伤"
            >
          </label>
          <label class="beat-input-field">
            <span>内容</span>
            <textarea
              v-model="newAnchorContent"
              data-testid="continuity-anchor-content"
              rows="3"
              placeholder="例如：沈知夏左臂仍有旧伤，不能做高强度攀爬或近身格斗。"
            />
          </label>
          <div class="anchor-controls">
            <label>
              <span>类型</span>
              <select
                v-model="newAnchorType"
                data-testid="continuity-anchor-type"
              >
                <option value="character_state">人物状态</option>
                <option value="plot_clue">线索伏笔</option>
                <option value="object_location">道具归属</option>
                <option value="relationship">人物关系</option>
                <option value="world_rule">世界规则</option>
              </select>
            </label>
            <label>
              <span>优先级</span>
              <select
                v-model="newAnchorPriority"
                data-testid="continuity-anchor-priority"
              >
                <option value="high">高</option>
                <option value="normal">普通</option>
                <option value="low">低</option>
              </select>
            </label>
            <button
              class="link-btn anchor-add-btn"
              data-testid="continuity-anchor-add"
              :disabled="!canAddContinuityAnchor"
              @click="addContinuityAnchor"
            >
              添加锚点
            </button>
          </div>
        </div>
        <div
          v-if="activeContinuityAnchors.length > 0"
          class="anchor-list"
        >
          <div
            v-for="anchor in activeContinuityAnchors"
            :key="anchor.id"
            class="anchor-item"
            data-testid="continuity-anchor-item"
          >
            <div>
              <strong>{{ anchor.title }}</strong>
              <small>{{ anchor.type }} / {{ anchor.priority }}</small>
              <p>{{ anchor.content }}</p>
            </div>
            <button
              class="link-btn"
              data-testid="continuity-anchor-archive"
              @click="archiveContinuityAnchor(anchor.id)"
            >
              归档
            </button>
          </div>
        </div>
        <p
          v-else
          class="beat-input-summary"
        >
          暂无 active 锚点。
        </p>
      </details>
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
import { useContinuityAnchors } from '@/composables/useContinuityAnchors'
import { useRequiredBeatsInput } from '@/composables/useRequiredBeatsInput'
import { useSceneGenerationActions } from '@/composables/useSceneGenerationActions'
import { getPipelineForFile } from '@/utils/promptTypes'
import type { ContinuityAnchorPriority, ContinuityAnchorType } from '@/shared/api/types'

const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const generationStore = useGenerationStore()
const notification = useNotificationStore()
const rightPanelStore = useRightPanelStore()
const fileGen = useFileGeneration()
const sceneActions = useSceneGenerationActions()
const continuityAnchors = useContinuityAnchors()
const {
  requiredBeatsText,
  forbiddenBeatsText,
  hasBeatInput,
  beatInputSummary,
  hasLongBeatLine,
  getBeatValidationExtraVars,
} = useRequiredBeatsInput()

const running = ref(false)
const statusText = ref('')
const newAnchorTitle = ref('')
const newAnchorContent = ref('')
const newAnchorType = ref<ContinuityAnchorType>('character_state')
const newAnchorPriority = ref<ContinuityAnchorPriority>('normal')
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
const continueLabel = computed(() => isChapterFile.value ? '生成当前场景' : '续写当前文件')
const rewriteLabel = computed(() => isChapterFile.value ? '重写当前场景' : '重写当前文件')
const activeContinuityAnchors = computed(() => continuityAnchors.activeAnchors.value)
const continuityAnchorCountText = computed(() => `${continuityAnchors.activeCount.value} 条 active`)
const canAddContinuityAnchor = computed(() => Boolean(
  projectId.value && newAnchorTitle.value.trim() && newAnchorContent.value.trim(),
))
const currentFileHint = computed(() => {
  if (!projectId.value) return '打开项目后可使用专业快捷操作。'
  if (!currentFilePath.value) return '从文件树打开一个场景或素材文件。'
  return '专业版不要求先写大纲，可以围绕当前文件直接生成、重写和补强。'
})

watch(projectId, () => {
  void refreshEngine()
  if (projectId.value) {
    void continuityAnchors.load(projectId.value)
  }
}, { immediate: true })

onMounted(() => {
  void refreshEngine()
})

async function addContinuityAnchor() {
  if (!projectId.value || !canAddContinuityAnchor.value) return
  const added = await continuityAnchors.addAnchor(projectId.value, {
    title: newAnchorTitle.value,
    content: newAnchorContent.value,
    type: newAnchorType.value,
    priority: newAnchorPriority.value,
  })
  if (added) {
    newAnchorTitle.value = ''
    newAnchorContent.value = ''
    notification.success('连续性锚点已添加。')
  }
}

async function archiveContinuityAnchor(anchorId: string) {
  if (!projectId.value || !anchorId) return
  await continuityAnchors.archiveAnchor(projectId.value, anchorId)
  notification.success('连续性锚点已归档。')
}

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
  const timers: number[] = []
  const clearTimers = () => {
    for (const timer of timers) window.clearTimeout(timer)
  }
  const isCandidateAction = /重写|润色|精修|补强|爽点/.test(label)
  const resultHint = isCandidateAction ? '结果将先进入候选稿。' : '正在准备写作结果。'
  statusText.value = `正在准备生成……${resultHint}`
  timers.push(window.setTimeout(() => {
    statusText.value = '正在调用模型……'
  }, 800))
  timers.push(window.setTimeout(() => {
    statusText.value = '模型响应较慢，仍在等待生成结果……'
  }, 15000))
  timers.push(window.setTimeout(() => {
    statusText.value = '真实 LLM 生成可能需要更久。你可以继续等待，或稍后重试。'
  }, 60000))
  try {
    await runner()
    clearTimers()
    statusText.value = isCandidateAction
      ? '已生成候选稿，采用后才会覆盖当前场景。'
      : `${label}完成。`
    notification.success(statusText.value)
  } catch (e: unknown) {
    clearTimers()
    const rawMessage = e instanceof Error ? e.message : String(e || '')
    const lower = rawMessage.toLowerCase()
    if (lower.includes('llm_error') || lower.includes('timeout') || rawMessage.includes('模型调用')) {
      statusText.value = '模型生成失败，可能是模型响应超时或服务暂时不可用。请稍后重试，或缩短上下文后再生成。'
    } else {
      statusText.value = rawMessage || `${label}失败`
    }
    notification.error(statusText.value)
  } finally {
    clearTimers()
    running.value = false
  }
}

async function handleContinue() {
  if (isChapterFile.value) {
    // 场景文件：使用统一的 writeCurrentScene 动作
    await runAction('生成当前场景', () => sceneActions.writeCurrentScene())
  } else {
    // 非场景文件：检查是否有专用管线（如 style-guide, blueprint 等）
    const pipelineName = getPipelineForFile(currentFilePath.value)
    if (pipelineName && pipelineName !== 'title') {
      // 有专用管线：通过 runPipeline 调用（走正确的管线，不生成正文）
      await runAction(`生成${currentFileLabel.value}`, () =>
        fileGen.runPipeline(
          projectId.value,
          currentFilePath.value,
          pipelineName,
          {},
          'write_scene',
        ),
      )
    } else {
      // 无专用管线的普通文件：使用原有的续写逻辑
      await runAction('续写当前文件', () => generationStore.continueWriting(
        projectId.value,
        currentFilePath.value,
        '请基于故事引擎和前文记忆，继续写当前文件；优先推进人物欲望、冲突和读者期待，不需要依赖大纲。',
      ))
    }
  }
}

async function handleRewrite() {
  if (isChapterFile.value) {
    // 场景文件：使用统一的 rewriteCurrentScene 动作
    await runAction('重写当前场景', () => sceneActions.rewriteCurrentScene())
  } else {
    // 非场景文件：使用原有的重写逻辑
    await runAction('重写当前文件', async () => {
      rightPanelStore.setActiveTab('candidate')
      await fileGen.runPipeline(
        projectId.value,
        currentFilePath.value,
        'rewrite',
        {
          user_prompt: '请在保留核心事件的基础上重写当前文件，增强人物动机、场景行动和场景钩子。',
          ...getBeatValidationExtraVars(),
        },
        'candidate',
      )
    })
  }
}

async function handleBoost() {
  await runAction('补强爽点', async () => {
    rightPanelStore.setActiveTab('candidate')
    await fileGen.runPipeline(
      projectId.value,
      currentFilePath.value,
      'rewrite',
      {
        user_prompt: '请生成一版候选稿：保留当前场景核心事件，加强冲突压力、主角反击的爽点兑现，以及下一场景钩子。不要直接覆盖原文。',
        ...getBeatValidationExtraVars(),
      },
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

.safety-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 8px 0 0;
  padding: 6px 10px;
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 5px;
  font-size: 11px;
  color: var(--accent-primary);
  line-height: 1.4;

  i {
    flex-shrink: 0;
    font-size: 10px;
  }
}

.beat-input-box {
  margin-top: 10px;
  padding: 9px 10px;
  border: 1px solid rgba(201, 169, 110, .18);
  border-radius: 6px;
  background: rgba(0, 0, 0, .12);
}

.anchor-input-box {
  @extend .beat-input-box;
}

.beat-input-box summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  color: var(--gold-primary);
  font-size: 12px;
  font-weight: 600;
}

.beat-input-box summary em {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(34, 197, 94, .14);
  color: var(--accent-success);
  font-size: 10px;
  font-style: normal;
  font-weight: 500;
}

.beat-input-hint {
  margin: 8px 0;
  color: var(--text-muted-ink);
  font-size: 11px;
  line-height: 1.5;
}

.beat-input-summary,
.beat-input-warning {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.45;
}

.beat-input-summary {
  color: var(--text-secondary);
}

.beat-input-warning {
  color: var(--accent-warning);
}

.beat-input-field {
  display: grid;
  gap: 5px;
  margin-top: 8px;
  color: var(--text-muted-ink);
  font-size: 12px;
}

.beat-input-field textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
  border: 1px solid var(--border-ink);
  border-radius: 6px;
  background: rgba(0, 0, 0, .18);
  color: var(--text-primary);
  font: inherit;
  line-height: 1.45;
  resize: vertical;
  outline: none;
}

.beat-input-field input,
.anchor-controls select {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
  border: 1px solid var(--border-ink);
  border-radius: 6px;
  background: rgba(0, 0, 0, .18);
  color: var(--text-primary);
  font: inherit;
  outline: none;
}

.beat-input-field textarea:focus,
.beat-input-field input:focus,
.anchor-controls select:focus {
  border-color: var(--gold-primary);
  box-shadow: 0 0 0 2px rgba(201, 169, 110, .12);
}

.anchor-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.anchor-controls label {
  display: grid;
  gap: 5px;
  color: var(--text-muted-ink);
  font-size: 12px;
}

.anchor-add-btn {
  grid-column: 1 / -1;
  min-height: 34px;
}

.anchor-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.anchor-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: start;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, .08);
  border-radius: 6px;
  background: rgba(255, 255, 255, .025);
}

.anchor-item strong,
.anchor-item small {
  display: block;
}

.anchor-item strong {
  color: var(--text-primary);
  font-size: 12px;
}

.anchor-item small {
  margin-top: 2px;
  color: var(--text-muted-ink);
  font-size: 10px;
}

.anchor-item p {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.45;
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
