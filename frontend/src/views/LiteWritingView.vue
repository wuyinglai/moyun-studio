<template>
  <div class="lite-page" data-testid="lite-entry-root">
    <section
      v-if="!projectStore.currentProject"
      class="idea-screen"
    >
      <div class="idea-head">
        <div>
          <p class="eyebrow">
            爽文模式
          </p>
          <h1>今天想写哪一种爽文？</h1>
          <p class="sub">
            选一张开局卡，系统会创建作品并进入无大纲创作。
          </p>
        </div>
        <button
          class="ghost-btn"
          :class="{ loading: loadingIdeas }"
          :disabled="loadingIdeas"
          @click="loadIdeas(true)"
        >
          <span v-if="loadingIdeas" class="loading-spinner"></span>
          {{ loadingIdeas ? 'AI正在生成...' : '换一批' }}
        </button>
      </div>

      <div class="idea-grid">
        <button
          v-for="card in ideaCards"
          :key="card.id"
          class="idea-card"
          :disabled="creating"
          @click="startProject(card)"
        >
          <span class="genre-pill">{{ card.genre }}</span>
          <strong>{{ card.title }}</strong>
          <span>{{ card.one_liner }}</span>
          <small>主角：{{ card.protagonist_hook }}</small>
          <small>爽点：{{ card.selling_point }}</small>
        </button>
      </div>
    </section>

    <section
      v-else
      class="writing-shell"
    >
      <aside class="lite-sidebar">
        <div class="side-head">
          <p class="eyebrow">
            作品
          </p>
          <h2>{{ projectStore.currentProject.name }}</h2>
          <p
            v-if="currentChapterProgress"
            class="chapter-progress-text"
          >
            {{ currentChapterProgress }}
          </p>
        </div>
        <button
          class="primary-btn full"
          @click="() => refreshOptions()"
        >
          换个方向
        </button>
        <div class="chapter-list">
          <button
            v-for="node in chapterFiles"
            :key="node.path"
            class="chapter-item"
            :class="{ active: node.path === currentFilePath, streaming: node.path === streamingFilePath }"
            @click="openChapter(node.path)"
          >
            <span>{{ formatChapterLabel(node.path) }}</span>
            <small
              v-if="chapterBadge(node.path)"
              :class="`badge-${chapterBadgeKind(node.path)}`"
            >
              {{ chapterBadge(node.path) }}
            </small>
          </button>
        </div>
      </aside>

      <main class="lite-editor">
        <ErrorBoundary
          title="编辑器出错"
          description="写作区域发生了意外错误，你可以重试或刷新页面。"
        >
        <div class="editor-top">
          <div>
            <p class="eyebrow">
              当前场景
            </p>
            <h1>{{ currentFilePath ? formatChapterLabel(currentFilePath) : '尚未打开场景' }}</h1>
            <p
              v-if="completionSummary"
              class="completion-summary"
            >
              {{ completionSummary }}
            </p>
            <p
              v-if="fallbackUsed"
              class="fallback-warning"
              data-testid="lite-fallback-warning"
            >
              ⚠️ 本场为应急草稿，建议重写或扩写。
            </p>
            <p
              v-if="currentFilePath"
              class="path-hint"
            >
              {{ currentFilePath }}
            </p>
          </div>
        </div>
        <textarea
          ref="textareaRef"
          v-model="content"
          class="chapter-textarea"
          data-testid="lite-editor-content"
          placeholder="选择右侧爽点卡开始生成，或在这里直接修改正文..."
          @input="dirty = true"
          @scroll="handleTextareaScroll"
        />
        <div
          v-if="isViewingCandidate && candidateDraft"
          class="candidate-bar"
        >
          <div>
            <strong>候选稿：{{ candidateActionText(candidateDraft.action) }}</strong>
            <span>原文不会被覆盖，满意后再采用。</span>
          </div>
          <button
            class="primary-btn compact"
            data-testid="lite-accept-button"
            :disabled="saving || generating"
            @click="acceptCandidate"
          >
            采用候选稿
          </button>
          <button
            class="ghost-btn"
            :disabled="saving || generating"
            @click="discardCandidate"
          >
            放弃
          </button>
        </div>
        <div class="editor-actions">
          <button
            class="ghost-btn"
            :disabled="!dirty || saving || isViewingCandidate"
            @click="saveCurrent"
          >
            保存
          </button>
          <button
            v-if="generating"
            class="ghost-btn danger-btn"
            @click="stopGeneration"
          >
            停止生成
          </button>
          <button
            v-else-if="canContinueDraft"
            class="ghost-btn continue-btn"
            @click="continueDraft"
          >
            继续生成
          </button>
          <button
            class="ghost-btn"
            :disabled="!currentFilePath || generating || !nextCards.length"
            @click="rewriteCurrent"
          >
            重写当前场景
          </button>
          <button
            class="ghost-btn"
            :disabled="!currentFilePath || generating || !nextCards.length"
            @click="improveCurrent('more_exciting')"
          >
            让当前场景更爽
          </button>
          <button
            class="ghost-btn"
            :disabled="!currentFilePath || generating || !nextCards.length"
            @click="improveCurrent('more_reasonable')"
          >
            让当前场景更合理
          </button>
        </div>
        <div
          v-if="qualitySummary"
          class="quality-line-wrap"
        >
          <span class="quality-line">{{ qualitySummary }}</span>
        </div>
        <div
          v-if="activeWorkStatus"
          class="work-status"
        >
          <div class="work-status-head">
            <span class="loading-spinner"></span>
            <strong>{{ activeWorkStatus.title }}</strong>
          </div>
          <p>{{ activeWorkStatus.detail }}</p>
        </div>
        <div
          v-if="generating"
          class="generating-mask"
          data-testid="lite-generating-status"
        >
          {{ activeWorkStatus?.detail || `正在写${pendingTargetLabel}，正文会实时出现在编辑器里...` }}
        </div>
        </ErrorBoundary>
      </main>

      <aside class="lite-assistant" data-testid="lite-next-options-panel">
        <section class="panel">
          <div
            v-if="chapterMilestone"
            class="chapter-milestone"
          >
            <span>本章完成</span>
            <strong>{{ chapterMilestone.summary }}</strong>
            <p>{{ chapterMilestone.nextGoal }}</p>
          </div>
          <div class="panel-title">
            <span>下一场景爽点卡</span>
            <button
              class="link-btn"
              :disabled="loadingOptions"
              @click="() => refreshOptions()"
            >
              刷新
            </button>
          </div>
          <p
            v-if="nextTargetHint"
            class="next-target-hint"
          >
            {{ nextTargetHint }}
          </p>
          <p
            v-if="generating"
            class="option-loading"
          >
            正在自动写{{ pendingTargetLabel }}，完成后会刷新下一场景爽点卡。
          </p>
          <p
            v-else-if="loadingOptions"
            class="option-loading"
          >
            正在根据前文生成爽点卡...
          </p>
          <p
            v-else-if="optionError"
            class="option-loading"
          >
            {{ optionError }}
          </p>
          <p
            v-else-if="!nextCards.length"
            class="option-loading"
          >
            打开一个场景后生成下一场景方向。
          </p>
          <button
            v-if="!nextCards.length && !loadingOptions && !generating"
            class="primary-btn full"
            data-testid="lite-generate-next-options"
            @click="refreshOptions"
          >
            生成下一场景爽点卡
          </button>
          <template v-if="!generating">
          <button
          v-for="(card, idx) in nextCards"
          :key="card.id"
          class="option-card"
          :data-testid="`lite-option-card-${idx}`"
          :disabled="generating"
          @click="generateWithCard(card)"
        >
            <strong>{{ card.title }}</strong>
            <div class="option-beats">
              <p v-if="card.protagonist_desire">
                <b>主角想要</b>
                <span>{{ card.protagonist_desire }}</span>
              </p>
              <p v-if="card.obstacle">
                <b>阻力</b>
                <span>{{ card.obstacle }}</span>
              </p>
              <p>
                <b>冲突升级</b>
                <span>{{ card.scene }}</span>
              </p>
              <p>
                <b>爽点兑现</b>
                <span>{{ card.payoff || card.beat }}</span>
              </p>
              <p v-if="card.advancement">
                <b>故事推进</b>
                <span>{{ card.advancement }}</span>
              </p>
              <p>
                <b>结尾钩子</b>
                <span>{{ card.hook }}</span>
              </p>
            </div>
            <em>{{ optionActionLabel }}</em>
          </button>
          </template>
        </section>

        <section class="panel">
          <div class="panel-title">
            <span>灵感改稿</span>
          </div>
          <div class="lite-chat-box">
            <p
              v-if="chatRevisionNote"
              class="chat-revision-note"
            >
              {{ chatRevisionNote }}
            </p>
            <textarea
              v-model="chatRevisionInput"
              rows="4"
              data-testid="lite-prompt-input"
              placeholder="比如：主角不够狠，改得更强势；结尾钩子再刺激一点。"
              @keydown.ctrl.enter.prevent="runChatRevision"
              @keydown.meta.enter.prevent="runChatRevision"
            />
            <button
              class="primary-btn full"
              data-testid="lite-generate-button"
              :disabled="!canRunChatRevision"
              @click="runChatRevision"
            >
              生成候选稿
            </button>
          </div>
        </section>

        <section class="panel">
          <div class="panel-title">
            <span>关键参数</span>
          </div>
          <label>文风<select v-model="prefs.style"><option
            v-for="v in styles"
            :key="v"
          >{{ v }}</option></select></label>
          <label>爽点强度<select v-model="prefs.intensity"><option
            v-for="v in intensities"
            :key="v"
          >{{ v }}</option></select></label>
          <label>节奏<select v-model="prefs.pace"><option
            v-for="v in paces"
            :key="v"
          >{{ v }}</option></select></label>
          <label>主角性格<select v-model="prefs.protagonist"><option
            v-for="v in protagonists"
            :key="v"
          >{{ v }}</option></select></label>
          <label>喜欢的元素<textarea
            v-model="prefs.likes"
            rows="2"
          /></label>
          <label>不要写的内容<textarea
            v-model="prefs.dislikes"
            rows="2"
          /></label>
        </section>

        <section class="panel">
          <div class="panel-title">
            <span>故事状态</span>
          </div>
          <dl class="engine-summary">
            <dt>主角目标</dt><dd>{{ engineSummary.protagonist_goal || '待更新' }}</dd>
            <dt>当前冲突</dt><dd>{{ engineSummary.current_conflict || '待更新' }}</dd>
            <dt>未回收伏笔</dt><dd>{{ engineSummary.foreshadowing || '待更新' }}</dd>
            <dt>下一阶段</dt><dd>{{ engineSummary.stage_goal || '待更新' }}</dd>
          </dl>
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import { useProjectStore } from '@/stores/project'
import { useFileStore, type FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import { defaultLitePrefs, type LiteIdeaCard, type LiteNextOptionCard } from '@/services/liteService'
import { useLiteGeneration } from '@/composables/useLiteGeneration'
import { useFlowRun } from '@/composables/useFlowRun'
import { useLiteCandidateActions } from '@/composables/useLiteCandidateActions'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()

// Component-level state (not managed by composables)
const content = ref('')
const currentFilePath = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const saving = ref(false)
const dirty = ref(false)
const prefs = reactive(defaultLitePrefs())
const chapterStatus = ref<Record<string, 'done' | 'blank' | 'draft'>>({})

const styles = ['轻松', '热血', '细腻', '幽默', '电影感']
const intensities = ['克制', '标准', '拉满']
const paces = ['慢热', '均衡', '快节奏']
const protagonists = ['冷静', '张扬', '腹黑', '善良', '疯批边缘']

// Computed: chapter file list
const chapterFiles = computed(() => {
  const seen = new Set<string>()
  const files: FileNode[] = []
  const walk = (nodes: FileNode[]) => {
    for (const node of nodes) {
      if (node.type === 'file' && /chapters\/.*sec-\d+\.md$/.test(node.path) && !seen.has(node.path)) {
        seen.add(node.path)
        files.push(node)
      }
      if (node.children) walk(node.children)
    }
  }
  walk(fileStore.tree)
  return files.sort((a, b) => a.path.localeCompare(b.path))
})

// UI helpers
function chapterBadge(path: string) {
  if (path === gen.streamingFilePath.value) return '生成中'
  if (chapterStatus.value[path] === 'done') return '已写'
  if (chapterStatus.value[path] === 'draft') return '草稿'
  if (chapterStatus.value[path] === 'blank') return '待写'
  return ''
}

function chapterBadgeKind(path: string) {
  if (path === gen.streamingFilePath.value) return 'streaming'
  return chapterStatus.value[path] || 'unknown'
}

function chapterProgressText(path: string) {
  const { vol, ch } = gen.parseSectionPath(path)
  if (!vol || !ch) return ''
  const sameChapter = chapterFiles.value.filter((node) => {
    const meta = gen.parseSectionPath(node.path)
    return meta.vol === vol && meta.ch === ch
  })
  const total = Math.max(sameChapter.length, 4)
  const done = sameChapter.filter((node) => chapterStatus.value[node.path] === 'done').length
  return `第${ch}章 ${Math.min(done, total)}/${total} 场景`
}

// Scroll helpers
function isTextareaNearBottom() {
  const el = textareaRef.value
  if (!el) return true
  return el.scrollTop + el.clientHeight >= el.scrollHeight - 32
}

function handleTextareaScroll() {
  if (!gen.generating.value) return
  gen.autoScrollDuringGeneration.value = isTextareaNearBottom()
}

async function scrollTextareaToBottom() {
  if (!gen.autoScrollDuringGeneration.value || currentFilePath.value !== gen.streamingFilePath.value) return
  await nextTick()
  const el = textareaRef.value
  if (el) el.scrollTop = el.scrollHeight
}

// Chapter operations (UI-level)
async function confirmDirty() {
  if (!dirty.value) return true
  return await new Promise<boolean>((resolve) => {
    Modal.confirm({
      title: '有未保存内容',
      content: '当前场景还没有保存，确定继续切换吗？',
      okText: '继续',
      cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
}

async function openChapter(path: string, options: { skipOptions?: boolean } = {}) {
  if (!gen.generating.value && !(await confirmDirty())) return
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const buffered = gen.streamingBuffers.value[path]
  const data = buffered === undefined ? await fileStore.readFile(projectId, path) : { content: buffered }
  currentFilePath.value = path
  content.value = gen.normalizeChapterHeading(path, data.content || '')
  chapterStatus.value[path] = gen.isBlankChapter(content.value) ? 'blank' : 'done'
  fileStore.openFile({ name: path.split('/').pop() || '', path, type: 'file' })
  editorStore.loadContent(path, content.value)
  editorStore.setCurrentFile(path)
  dirty.value = false
  if (!gen.generating.value && !options.skipOptions) {
    await gen.refreshOptions(path)
  }
}

async function saveCurrent() {
  const projectId = projectStore.currentProject?.id
  if (!projectId || !currentFilePath.value) return
  saving.value = true
  try {
    await fileStore.saveFile(projectId, currentFilePath.value, content.value)
    chapterStatus.value[currentFilePath.value] = gen.isBlankChapter(content.value) ? 'blank' : 'done'
    dirty.value = false
    notification.success('已保存')
  } finally {
    saving.value = false
  }
}

// ─── Composables ──────────────────────────────────────────

const flow = useFlowRun()

const gen = useLiteGeneration({
  content,
  currentFilePath,
  chapterStatus,
  textareaRef,
  scrollTextareaToBottom,
  dirty,
  prefs,
  chapterFiles,
  openChapter,
  flow,
})

const cand = useLiteCandidateActions({
  content,
  currentFilePath,
  chapterStatus,
  streamingBuffers: gen.streamingBuffers,
  generating: gen.generating,
  saving,
  dirty,
  prefs,
  formatChapterLabel: gen.formatChapterLabel,
  isBlankChapter: gen.isBlankChapter,
  normalizeChapterHeading: gen.normalizeChapterHeading,
  refreshOptions: gen.refreshOptions,
  setWorkStatus: gen.setWorkStatus,
  clearWorkStatus: gen.clearWorkStatus,
  runGeneration: gen.runGeneration,
  openChapter,
  loadingOptions: gen.loadingOptions,
})

// ─── UI Computed ──────────────────────────────────────────

const optionActionLabel = computed(() => {
  if (gen.nextTargetFile.value) {
    const verb = gen.isChapterStart(gen.nextTargetFile.value) && gen.chapterMilestone.value ? '开启' : '自动写'
    return `选这个，${verb}${gen.formatChapterLabel(gen.nextTargetFile.value)}`
  }
  return '选这个，自动写下一场景'
})

const currentChapterProgress = computed(() => {
  const basePath = gen.streamingFilePath.value || currentFilePath.value || gen.nextTargetFile.value
  if (basePath && gen.chapterMilestone.value) {
    const meta = gen.parseSectionPath(basePath)
    if (meta.vol === gen.chapterMilestone.value.vol && meta.ch === gen.chapterMilestone.value.ch) {
      return `第${meta.ch}章完成 · 下一章已准备`
    }
  }
  return basePath ? chapterProgressText(basePath) : ''
})

const completionSummary = computed(() => {
  if (cand.candidateDraft.value && currentFilePath.value === cand.candidateDraft.value.path) {
    return `候选稿：${gen.candidateActionText(cand.candidateDraft.value.action)}，满意后再采用替换原文`
  }
  if (gen.generating.value && gen.pendingTargetLabel.value) {
    return `正在写${gen.pendingTargetLabel.value} · ${currentChapterProgress.value || '本章进度更新中'}`
  }
  if (!currentFilePath.value || chapterStatus.value[currentFilePath.value] !== 'done') {
    return currentChapterProgress.value
  }
  return `${gen.formatChapterLabel(currentFilePath.value)}已完成 · ${currentChapterProgress.value}`
})

const nextTargetHint = computed(() => {
  if (gen.loadingOptions.value) return ''
  if (!gen.nextTargetFile.value) return ''
  const verb = gen.isChapterStart(gen.nextTargetFile.value) && gen.chapterMilestone.value ? '开启' : '自动写'
  return `选择一张卡，${verb}${gen.formatChapterLabel(gen.nextTargetFile.value)}`
})

const canContinueDraft = computed(() => {
  return Boolean(
    currentFilePath.value
    && chapterStatus.value[currentFilePath.value] === 'draft'
    && content.value.trim()
    && gen.lastGenerationCard.value,
  )
})

const isViewingCandidate = computed(() => {
  return Boolean(cand.candidateDraft.value && currentFilePath.value === cand.candidateDraft.value.path)
})

const fallbackUsed = computed(() => gen.fallbackUsed.value)

const canRunChatRevision = computed(() => {
  return Boolean(
    cand.chatRevisionInput.value.trim()
    && currentFilePath.value
    && !gen.generating.value
    && !saving.value,
  )
})

const activeWorkStatus = computed(() => {
  if (gen.workPhase.value) {
    return {
      title: gen.workPhase.value,
      detail: gen.workDetail.value,
    }
  }
  if (gen.loadingOptions.value) {
    return {
      title: '正在生成爽点卡',
      detail: '正在读取前文、故事引擎和近期上下文，给下一场景准备 3 个方向。',
    }
  }
  if (gen.creating.value) {
    return {
      title: '正在创建作品',
      detail: '正在建立章节目录、故事引擎和初始写作参数。',
    }
  }
  return null
})

// ─── Event Handlers ───────────────────────────────────────

async function handleStartProject(card: LiteIdeaCard) {
  await gen.startProject(card, router, cand.candidateDraft)
}

async function handleGenerateWithCard(card: LiteNextOptionCard) {
  await gen.generateWithCard(card, cand.candidateDraft)
}

async function handleRewriteCurrent() {
  await cand.rewriteCurrent(gen.nextCards.value, currentFilePath.value)
}

async function handleImproveCurrent(action: 'more_exciting' | 'more_reasonable') {
  await cand.improveCurrent(action, gen.nextCards.value, currentFilePath.value)
}

async function handleContinueDraft() {
  await gen.continueDraft(cand.candidateDraft)
}

async function handleRunChatRevision() {
  await cand.runChatRevision(currentFilePath.value)
}

// ─── Lifecycle ────────────────────────────────────────────

onMounted(async () => {
  if (route.params.projectId) {
    await gen.openProject(route.params.projectId as string, cand.candidateDraft)
  } else {
    projectStore.closeProject()
    await gen.loadIdeas(false)
  }
})

watch(() => route.params.projectId, async (id) => {
  if (id) {
    if (gen.creating.value) return
    await gen.openProject(id as string, cand.candidateDraft)
  } else {
    projectStore.closeProject()
    await gen.loadIdeas(false)
  }
})

// ─── Template aliases (avoid changing template) ───────────
const ideaCards = gen.ideaCards
const nextCards = gen.nextCards
const pendingTargetLabel = gen.pendingTargetLabel
const streamingFilePath = gen.streamingFilePath
const generating = gen.generating
const loadingIdeas = gen.loadingIdeas
const loadingOptions = gen.loadingOptions
const optionError = gen.optionError
const creating = gen.creating
const qualitySummary = gen.qualitySummary
const engineSummary = gen.engineSummary
const chapterMilestone = gen.chapterMilestone
const candidateDraft = cand.candidateDraft
const chatRevisionInput = cand.chatRevisionInput
const chatRevisionNote = cand.chatRevisionNote
const formatChapterLabel = gen.formatChapterLabel
const candidateActionText = gen.candidateActionText
function loadIdeas(force: boolean) { gen.loadIdeas(force) }
function startProject(card: LiteIdeaCard) { handleStartProject(card) }
function generateWithCard(card: LiteNextOptionCard) { handleGenerateWithCard(card) }
function rewriteCurrent() { handleRewriteCurrent() }
function improveCurrent(action: 'more_exciting' | 'more_reasonable') { handleImproveCurrent(action) }
function continueDraft() { handleContinueDraft() }
function runChatRevision() { handleRunChatRevision() }
function stopGeneration() { gen.stopGeneration() }
function acceptCandidate() { cand.acceptCandidate() }
function discardCandidate() { cand.discardCandidate() }
function refreshOptions() { gen.refreshOptions() }
</script>

<style scoped lang="scss">
.lite-page {
  height: 100%;
  min-height: 0;
  background: #151824;
  color: var(--text-primary);
}

.idea-screen,
.writing-shell {
  height: 100%;
}

.idea-screen {
  padding: 40px;
  overflow: auto;
}

.idea-head,
.editor-top,
.panel-title,
.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.idea-head h1,
.editor-top h1,
.side-head h2 {
  margin: 4px 0;
}

.editor-top h1 {
  font-size: 22px;
  line-height: 1.25;
  font-weight: 700;
}

.path-hint {
  margin: 4px 0 0;
  color: var(--text-faint);
  font-size: 12px;
  line-height: 1.4;
  word-break: break-all;
}

.completion-summary,
.chapter-progress-text,
.next-target-hint {
  margin: 6px 0 0;
  color: var(--gold-primary);
  font-size: 13px;
  line-height: 1.5;
}

.chapter-progress-text {
  color: var(--text-muted-ink);
}

.fallback-warning {
  margin: 0;
  padding: 8px 12px;
  background: rgba(220, 84, 64, 0.12);
  border: 1px solid rgba(220, 84, 64, 0.3);
  border-radius: 6px;
  color: #ffb6a9;
  font-size: 13px;
}

.next-target-hint {
  padding: 8px 10px;
  border: 1px solid rgba(201, 169, 110, .18);
  border-radius: 6px;
  background: rgba(201, 169, 110, .07);
}

.candidate-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(201, 169, 110, .28);
  border-radius: 7px;
  background: rgba(201, 169, 110, .08);
}

.candidate-bar div {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 3px;
}

.candidate-bar strong {
  color: var(--gold-primary);
  font-size: 13px;
}

.candidate-bar span {
  color: var(--text-muted-ink);
  font-size: 12px;
}

.work-status {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid rgba(45, 138, 110, .24);
  border-radius: 7px;
  background: rgba(45, 138, 110, .08);
}

.work-status-head {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.work-status strong {
  color: var(--jade-light);
  font-size: 13px;
}

.work-status p {
  margin: 0;
  color: var(--text-muted-ink);
  font-size: 12px;
  line-height: 1.5;
}

.sub,
.eyebrow,
.option-card small,
.idea-card small {
  color: var(--text-muted-ink);
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0;
}

.idea-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
  margin-top: 28px;
}

.idea-card,
.option-card,
.panel,
.lite-sidebar,
.lite-editor,
.lite-assistant {
  border: 1px solid var(--border-ink);
  background: #1d2230;
}

.idea-card,
.option-card {
  text-align: left;
  color: inherit;
  cursor: pointer;
  transition: border-color .18s ease, transform .18s ease;
}

.idea-card {
  min-height: 230px;
  padding: 18px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.idea-card:hover,
.option-card:hover {
  border-color: var(--gold-primary);
  transform: translateY(-1px);
}

.genre-pill {
  align-self: flex-start;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(201, 169, 110, .14);
  color: var(--gold-primary);
  font-size: 12px;
}

.writing-shell {
  display: grid;
  grid-template-columns: 220px minmax(360px, 1fr) 340px;
  gap: 1px;
  background: var(--border-ink);
  min-height: 0;
}

.lite-sidebar,
.lite-editor,
.lite-assistant {
  min-height: 0;
  overflow: auto;
}

.lite-sidebar,
.lite-assistant {
  padding: 16px;
}

.lite-editor {
  display: flex;
  flex-direction: column;
  padding: 18px;
  position: relative;
}

.chapter-textarea {
  flex: 1;
  min-height: 0;
  margin-top: 12px;
  resize: none;
  padding: 18px;
  border: 1px solid var(--border-ink);
  border-radius: 8px;
  background: #111520;
  color: var(--text-primary);
  line-height: 1.8;
  font-size: 15px;
  outline: none;
}

.chapter-textarea:focus {
  border-color: var(--gold-primary);
}

.chapter-list {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.chapter-item {
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted-ink);
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 38px;
}

.chapter-item span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-item small {
  flex: 0 0 auto;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 11px;
}

.chapter-item small.badge-done {
  background: rgba(45, 138, 110, .16);
  color: var(--jade-light);
}

.chapter-item small.badge-blank {
  background: rgba(255, 255, 255, .06);
  color: var(--text-faint);
}

.chapter-item small.badge-draft {
  background: rgba(201, 169, 110, .14);
  color: var(--gold-primary);
}

.chapter-item small.badge-streaming {
  background: rgba(45, 138, 110, .16);
  color: var(--jade-light);
}

.chapter-item.active,
.chapter-item:hover {
  color: var(--gold-primary);
  border-color: rgba(201, 169, 110, .35);
  background: rgba(201, 169, 110, .08);
}

.chapter-item.streaming {
  border-color: rgba(45, 138, 110, .38);
}

.panel {
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.chapter-milestone {
  display: grid;
  gap: 7px;
  padding: 10px 11px;
  margin-bottom: 12px;
  border: 1px solid rgba(45, 138, 110, .26);
  border-radius: 7px;
  background: rgba(45, 138, 110, .08);
}

.chapter-milestone span {
  color: var(--jade-light);
  font-size: 12px;
}

.chapter-milestone strong {
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.5;
}

.chapter-milestone p {
  margin: 0;
  color: var(--text-muted-ink);
  font-size: 13px;
  line-height: 1.55;
}

.option-card {
  width: 100%;
  padding: 12px;
  border-radius: 7px;
  margin-top: 10px;
  display: grid;
  gap: 9px;
}

.option-beats {
  display: grid;
  gap: 7px;
}

.option-beats p {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  margin: 0;
  line-height: 1.5;
}

.option-beats b {
  color: var(--gold-primary);
  font-size: 12px;
  font-weight: 600;
}

.option-beats span {
  min-width: 0;
  color: var(--text-muted-ink);
  font-size: 13px;
}

.option-card em {
  margin-top: 3px;
  padding-top: 8px;
  border-top: 1px solid rgba(201, 169, 110, .16);
  color: var(--gold-primary);
  font-style: normal;
  font-size: 12px;
}

.option-loading {
  margin: 12px 0 0;
  color: var(--text-muted-ink);
  font-size: 13px;
  line-height: 1.6;
}

.lite-chat-box {
  display: grid;
  gap: 10px;
}

.lite-chat-box textarea {
  width: 100%;
  resize: vertical;
  min-height: 92px;
  border: 1px solid var(--border-ink);
  border-radius: 6px;
  background: #111520;
  color: var(--text-primary);
  padding: 9px;
  outline: none;
  line-height: 1.6;
}

.chat-revision-note {
  margin: 0;
  color: var(--text-muted-ink);
  font-size: 13px;
  line-height: 1.55;
}

label {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  color: var(--text-muted-ink);
  font-size: 12px;
}

select,
label textarea {
  width: 100%;
  border: 1px solid var(--border-ink);
  border-radius: 6px;
  background: #111520;
  color: var(--text-primary);
  padding: 8px;
  outline: none;
}

.engine-summary {
  display: grid;
  gap: 8px;
  margin: 10px 0 0;
}

.engine-summary dt {
  color: var(--gold-primary);
  font-size: 12px;
}

.engine-summary dd {
  margin: 0;
  color: var(--text-muted-ink);
  font-size: 13px;
  line-height: 1.5;
}

.primary-btn,
.ghost-btn,
.link-btn {
  border-radius: 6px;
  cursor: pointer;
}

.primary-btn,
.ghost-btn {
  padding: 8px 12px;
  border: 1px solid var(--border-ink);
}

.primary-btn {
  background: var(--gold-primary);
  color: #171717;
  border-color: var(--gold-primary);
}

.primary-btn.compact {
  padding: 7px 10px;
  white-space: nowrap;
}

.ghost-btn {
  background: transparent;
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.ghost-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ghost-btn.loading {
  color: var(--gold-primary);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(201, 169, 110, 0.3);
  border-top-color: var(--gold-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.danger-btn {
  border-color: rgba(220, 88, 88, .45);
  color: #ff9a9a;
}

.continue-btn {
  border-color: rgba(45, 138, 110, .45);
  color: var(--jade-light);
}

.link-btn {
  background: transparent;
  border: none;
  color: var(--gold-primary);
}

.full {
  width: 100%;
}

.quality-line {
  color: var(--jade-light);
  font-size: 13px;
}

.generating-mask {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 70px;
  padding: 12px 14px;
  border: 1px solid rgba(201, 169, 110, .35);
  border-radius: 8px;
  background: rgba(17, 21, 32, .92);
  color: var(--gold-primary);
  font-size: 13px;
}
</style>
