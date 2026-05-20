<template>
  <div class="lite-page">
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
        <div class="editor-top">
          <div>
            <p class="eyebrow">
              当前章节
            </p>
            <h1>{{ currentFilePath ? formatChapterLabel(currentFilePath) : '尚未打开章节' }}</h1>
            <p
              v-if="completionSummary"
              class="completion-summary"
            >
              {{ completionSummary }}
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
            重写这一章
          </button>
          <button
            class="ghost-btn"
            :disabled="!currentFilePath || generating || !nextCards.length"
            @click="improveCurrent('more_exciting')"
          >
            更爽一点
          </button>
          <button
            class="ghost-btn"
            :disabled="!currentFilePath || generating || !nextCards.length"
            @click="improveCurrent('more_reasonable')"
          >
            更合理一点
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
        >
          {{ activeWorkStatus?.detail || `正在写${pendingTargetLabel}，正文会实时出现在编辑器里...` }}
        </div>
      </main>

      <aside class="lite-assistant">
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
            <span>下一节爽点卡</span>
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
            正在自动写{{ pendingTargetLabel }}，完成后会刷新下一节爽点卡。
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
            打开一个章节后生成下一节方向。
          </p>
          <button
            v-for="card in nextCards"
            v-if="!generating"
            :key="card.id"
            class="option-card"
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
              placeholder="比如：主角不够狠，改得更强势；结尾钩子再刺激一点。"
              @keydown.ctrl.enter.prevent="runChatRevision"
              @keydown.meta.enter.prevent="runChatRevision"
            />
            <button
              class="primary-btn full"
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
import { useProjectStore } from '@/stores/project'
import { useFileStore, type FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import {
  createLiteProject,
  defaultLitePrefs,
  fetchLiteIdeas,
  fetchLiteNextOptions,
  streamLiteNext,
  type LiteIdeaCard,
  type LiteWriteAction,
  type LiteNextOptionCard,
} from '@/services/liteService'
import { consumeOrFetch } from '@/composables/useLitePrefetch'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()

const ideaCards = ref<LiteIdeaCard[]>([])
const nextCards = ref<LiteNextOptionCard[]>([])
const nextTargetFile = ref('')
const pendingTargetLabel = ref('')
const content = ref('')
const currentFilePath = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const streamingFilePath = ref('')
const streamingBuffers = ref<Record<string, string>>({})
const candidateDraft = ref<{
  sourcePath: string
  path: string
  action: LiteWriteAction
  title: string
  content: string
} | null>(null)
const chapterStatus = ref<Record<string, 'done' | 'blank' | 'draft'>>({})
const chapterMilestone = ref<{ vol: number; ch: number; summary: string; nextGoal: string } | null>(null)
const qualitySummary = ref('')
const engineSummary = ref<Record<string, string>>({})
const loadingIdeas = ref(false)
const loadingOptions = ref(false)
const optionError = ref('')
const optionRequestId = ref(0)
const workPhase = ref('')
const workDetail = ref('')
const creating = ref(false)
const generating = ref(false)
const generationAbortController = ref<AbortController | null>(null)
const lastGenerationCard = ref<LiteNextOptionCard | null>(null)
const autoScrollDuringGeneration = ref(true)
const saving = ref(false)
const dirty = ref(false)
const chatRevisionInput = ref('')
const chatRevisionNote = ref('')
const prefs = reactive(defaultLitePrefs())

const styles = ['轻松', '热血', '细腻', '幽默', '电影感']
const intensities = ['克制', '标准', '拉满']
const paces = ['慢热', '均衡', '快节奏']
const protagonists = ['冷静', '张扬', '腹黑', '善良', '疯批边缘']

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

const optionActionLabel = computed(() => {
  if (nextTargetFile.value) {
    const verb = isChapterStart(nextTargetFile.value) && chapterMilestone.value ? '开启' : '自动写'
    return `选这个，${verb}${formatChapterLabel(nextTargetFile.value)}`
  }
  return '选这个，自动写下一节'
})

const currentChapterProgress = computed(() => {
  const basePath = streamingFilePath.value || currentFilePath.value || nextTargetFile.value
  if (basePath && chapterMilestone.value) {
    const meta = parseSectionPath(basePath)
    if (meta.vol === chapterMilestone.value.vol && meta.ch === chapterMilestone.value.ch) {
      return `第${meta.ch}章完成 · 下一章已准备`
    }
  }
  return basePath ? chapterProgressText(basePath) : ''
})

const completionSummary = computed(() => {
  if (candidateDraft.value && currentFilePath.value === candidateDraft.value.path) {
    return `候选稿：${candidateActionText(candidateDraft.value.action)}，满意后再采用替换原文`
  }
  if (generating.value && pendingTargetLabel.value) {
    return `正在写${pendingTargetLabel.value} · ${currentChapterProgress.value || '本章进度更新中'}`
  }
  if (!currentFilePath.value || chapterStatus.value[currentFilePath.value] !== 'done') {
    return currentChapterProgress.value
  }
  return `${formatChapterLabel(currentFilePath.value)}已完成 · ${currentChapterProgress.value}`
})

const nextTargetHint = computed(() => {
  if (loadingOptions.value) return ''
  if (!nextTargetFile.value) return ''
  const verb = isChapterStart(nextTargetFile.value) && chapterMilestone.value ? '开启' : '自动写'
  return `选择一张卡，${verb}${formatChapterLabel(nextTargetFile.value)}`
})

const canContinueDraft = computed(() => {
  return Boolean(
    currentFilePath.value
    && chapterStatus.value[currentFilePath.value] === 'draft'
    && content.value.trim()
    && lastGenerationCard.value,
  )
})

const isViewingCandidate = computed(() => {
  return Boolean(candidateDraft.value && currentFilePath.value === candidateDraft.value.path)
})

const canRunChatRevision = computed(() => {
  return Boolean(
    chatRevisionInput.value.trim()
    && currentFilePath.value
    && !generating.value
    && !saving.value,
  )
})

const activeWorkStatus = computed(() => {
  if (workPhase.value) {
    return {
      title: workPhase.value,
      detail: workDetail.value,
    }
  }
  if (loadingOptions.value) {
    return {
      title: '正在生成爽点卡',
      detail: '正在读取前文、故事引擎和近期上下文，给下一节准备 3 个方向。',
    }
  }
  if (creating.value) {
    return {
      title: '正在创建作品',
      detail: '正在建立章节目录、故事引擎和初始写作参数。',
    }
  }
  return null
})

onMounted(async () => {
  if (route.params.projectId) {
    await openProject(route.params.projectId as string)
  } else {
    projectStore.closeProject()
    await loadIdeas(false)
  }
})

watch(() => route.params.projectId, async (id) => {
  if (id) {
    // 如果正在创建项目中，跳过 watch 处理，由 startProject 处理完整流程
    if (creating.value) {
      return
    }
    await openProject(id as string)
  } else {
    projectStore.closeProject()
    await loadIdeas(false)
  }
})

async function loadIdeas(force: boolean) {
  loadingIdeas.value = true
  try {
    if (force) {
      // 换一批：优先消费预取好的下一批
      try {
        ideaCards.value = await consumeOrFetch()
      } catch {
        // 预取失败，兜底请求
        ideaCards.value = await fetchLiteIdeas(String(Date.now()))
      }
    } else {
      // 首次进入：优先消费预取缓存
      ideaCards.value = await consumeOrFetch()
    }
  } finally {
    loadingIdeas.value = false
  }
}

async function startProject(card: LiteIdeaCard) {
  creating.value = true
  try {
    const created = await createLiteProject(card, prefs)

    await projectStore.openProject(created.project_id)

    await fileStore.loadTree(created.project_id)

    await router.push(`/project/${created.project_id}/lite`)

    await openChapter(created.first_file, { skipOptions: true })
    engineSummary.value = {
      protagonist_goal: '主角：证明自己，摆脱羞辱，获得真正能改变命运的力量。',
      current_conflict: card.core_conflict,
      foreshadowing: card.one_liner,
      stage_goal: '当前 5 章目标：完成开局压迫到第一次漂亮反击。',
    }
    const openingCard: LiteNextOptionCard = {
      id: `opening-${card.id}`,
      title: card.title,
      beat: `第一章围绕“${card.one_liner}”展开，写出压迫、反击前奏和主角钩子。`,
      scene: '开局冲突现场',
      protagonist_desire: card.protagonist_hook,
      obstacle: card.core_conflict,
      payoff: card.selling_point,
      hook: '让更大的冲突在结尾露出苗头',
      advancement: '完成开局压迫和第一次行动选择，为下一节留出明确冲突。',
    }
    nextTargetFile.value = created.first_file
    nextCards.value = []
    await runGeneration(openingCard, 'write', created.first_file)
  } catch (e: any) {
    notification.error(e.message || '创建爽文项目失败')
  } finally {
    creating.value = false
  }
}

function formatChapterLabel(path: string) {
  const vol = path.match(/vol-(\d+)/)?.[1]
  const ch = path.match(/ch-(\d+)/)?.[1]
  const sec = path.match(/sec-(\d+)/)?.[1]
  if (!vol && !ch && !sec) return path.split('/').pop()?.replace('.md', '') || path
  const parts = []
  if (vol) parts.push(`第${Number(vol)}卷`)
  if (ch) parts.push(`第${Number(ch)}章`)
  if (sec) parts.push(`第${Number(sec)}节`)
  return parts.join(' ')
}

function candidateActionText(action: LiteWriteAction) {
  if (candidateDraft.value?.path.endsWith('.chat.md')) return '聊天改稿'
  if (action === 'rewrite') return '重写这一章'
  if (action === 'more_exciting') return '更爽一点'
  if (action === 'more_reasonable') return '更合理一点'
  return '候选稿'
}

function buildCandidatePath(sourcePath: string, action: LiteWriteAction) {
  const safeSource = sourcePath.replace(/\.md$/, '').replace(/[\\/]/g, '__')
  return `.lite-candidates/${safeSource}.${action}.md`
}

function buildChatRevisionPath(sourcePath: string) {
  const safeSource = sourcePath.replace(/\.md$/, '').replace(/[\\/]/g, '__')
  return `.lite-candidates/${safeSource}.chat.md`
}

function setWorkStatus(title: string, detail: string) {
  workPhase.value = title
  workDetail.value = detail
}

function clearWorkStatus() {
  workPhase.value = ''
  workDetail.value = ''
}

function parseSectionPath(path: string) {
  const vol = Number(path.match(/vol-(\d+)/)?.[1] || 0)
  const ch = Number(path.match(/ch-(\d+)/)?.[1] || 0)
  const sec = Number(path.match(/sec-(\d+)/)?.[1] || 0)
  return { vol, ch, sec }
}

function isChapterStart(path: string) {
  return parseSectionPath(path).sec === 1
}

function chapterProgressText(path: string) {
  const { vol, ch } = parseSectionPath(path)
  if (!vol || !ch) return ''
  const sameChapter = chapterFiles.value.filter((node) => {
    const meta = parseSectionPath(node.path)
    return meta.vol === vol && meta.ch === ch
  })
  const total = Math.max(sameChapter.length, 4)
  const done = sameChapter.filter((node) => chapterStatus.value[node.path] === 'done').length
  return `第${ch}章 ${Math.min(done, total)}/${total} 节`
}

function isAbortError(e: unknown) {
  return e instanceof DOMException && e.name === 'AbortError'
}

function isTextareaNearBottom() {
  const el = textareaRef.value
  if (!el) return true
  return el.scrollTop + el.clientHeight >= el.scrollHeight - 32
}

function handleTextareaScroll() {
  if (!generating.value) return
  autoScrollDuringGeneration.value = isTextareaNearBottom()
}

async function scrollTextareaToBottom() {
  if (!autoScrollDuringGeneration.value || currentFilePath.value !== streamingFilePath.value) return
  await nextTick()
  const el = textareaRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function appendDraftContent(base: string, addition: string) {
  if (!base.trim()) return addition
  if (!addition.trim()) return base
  return `${base.replace(/\s+$/, '')}\n\n${addition.replace(/^\s+/, '')}`
}

function stripLeadingMarkdownHeading(text: string) {
  return text.replace(/^\s*#{1,6}\s+[^\n\r]*(\r?\n)+/, '')
}

function extractNextChapterGoal(plan: string | null | undefined) {
  const fallback = '下一章会把本章留下的压力继续推高。'
  if (!plan) return fallback
  const line = plan
    .split(/\r?\n/)
    .map(item => item.replace(/^#+\s*/, '').replace(/^[-*]\s*/, '').trim())
    .find(item => item && !item.includes('章规划格式'))
  return line ? line.slice(0, 80) : fallback
}

function buildChapterMilestone(result: { file_path: string; chapter_plan?: string | null }, card: LiteNextOptionCard) {
  const { vol, ch } = parseSectionPath(result.file_path)
  if (!vol || !ch) return null
  return {
    vol,
    ch,
    summary: `第${ch}章完成：${card.title}，${card.payoff}`,
    nextGoal: `下一章目标：${extractNextChapterGoal(result.chapter_plan)}`,
  }
}

function isBlankChapter(text: string) {
  const body = text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
    .join('')
  return body.length < 20
}

function chapterBadge(path: string) {
  if (path === streamingFilePath.value) return '生成中'
  if (chapterStatus.value[path] === 'done') return '已写'
  if (chapterStatus.value[path] === 'draft') return '草稿'
  if (chapterStatus.value[path] === 'blank') return '待写'
  return ''
}

function chapterBadgeKind(path: string) {
  if (path === streamingFilePath.value) return 'streaming'
  return chapterStatus.value[path] || 'unknown'
}

function normalizeChapterHeading(path: string, text: string) {
  const lines = text.split(/\r?\n/)
  const first = lines[0] || ''
  if (!first.trim().startsWith('#')) return text
  const expectedPrefix = `# ${formatChapterLabel(path)}`
  if (first.startsWith(expectedPrefix)) return text
  const title = first
    .replace(/^#+\s*/, '')
    .replace(/第\d+卷/g, '')
    .replace(/第\d+章/g, '')
    .replace(/第\d+节/g, '')
    .replace(/\s*-\s*/g, ' ')
    .trim() || projectStore.currentProject?.name || ''
  lines[0] = title ? `${expectedPrefix} ${title}` : expectedPrefix
  return lines.join('\n')
}

function buildOpeningCardFromProject(): LiteNextOptionCard {
  const project = projectStore.currentProject
  return {
    id: 'opening-current-project',
    title: project?.name || '开局第一章',
    beat: `第一章围绕“${project?.name || '开局冲突'}”展开，写出人物欲望、压迫感和第一个钩子。`,
    scene: project?.background || '开局冲突现场',
    protagonist_desire: '主角要摆脱被动处境，拿到第一份可见收益。',
    obstacle: project?.background || '旧秩序和当面施压的人挡在前面。',
    payoff: project?.theme || '完成开局爽点兑现',
    hook: '让更大的冲突在结尾露出苗头',
    advancement: '把主角目标、压迫来源和下一节冲突接力点建立起来。',
  }
}

async function openProject(projectId: string) {
  await projectStore.openProject(projectId)
  await fileStore.loadTree(projectId)
  const { node: resume, hasWritten } = await findResumeChapter(projectId)
  if (resume) await openChapter(resume.path, { skipOptions: !hasWritten })
  if (resume && !hasWritten && !creating.value && isBlankChapter(content.value)) {
    const openingCard = buildOpeningCardFromProject()
    nextTargetFile.value = resume.path
    nextCards.value = []
    await runGeneration(openingCard, 'write', resume.path)
  } else if (!resume) {
    await refreshOptions()
  }
}

async function findResumeChapter(projectId: string) {
  let lastWritten = chapterFiles.value[0] || null
  let hasWritten = false
  let firstBlank: FileNode | null = null
  for (const node of chapterFiles.value) {
    const data = await fileStore.readFile(projectId, node.path)
    const blank = isBlankChapter(data.content || '')
    chapterStatus.value[node.path] = blank ? 'blank' : 'done'
    if (blank && !firstBlank) {
      firstBlank = node
    }
    if (blank) continue
    hasWritten = true
    lastWritten = node
  }
  if (firstBlank) return { node: firstBlank, hasWritten }
  return { node: lastWritten, hasWritten }
}

async function openChapter(path: string, options: { skipOptions?: boolean } = {}) {
  if (!generating.value && !(await confirmDirty())) return
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const buffered = streamingBuffers.value[path]
  const data = buffered === undefined ? await fileStore.readFile(projectId, path) : { content: buffered }
  currentFilePath.value = path
  content.value = normalizeChapterHeading(path, data.content || '')
  chapterStatus.value[path] = isBlankChapter(content.value) ? 'blank' : 'done'
  fileStore.openFile({ name: path.split('/').pop() || '', path, type: 'file' })
  editorStore.loadContent(path, content.value)
  editorStore.setCurrentFile(path)
  dirty.value = false
  if (!generating.value && !options.skipOptions) {
    await refreshOptions(path)
  }
}

async function confirmDirty() {
  if (!dirty.value) return true
  return await new Promise<boolean>((resolve) => {
    Modal.confirm({
      title: '有未保存内容',
      content: '当前章节还没有保存，确定继续切换吗？',
      okText: '继续',
      cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
}

async function saveCurrent() {
  const projectId = projectStore.currentProject?.id
  if (!projectId || !currentFilePath.value) return
  saving.value = true
  try {
    await fileStore.saveFile(projectId, currentFilePath.value, content.value)
    chapterStatus.value[currentFilePath.value] = isBlankChapter(content.value) ? 'blank' : 'done'
    dirty.value = false
    notification.success('已保存')
  } finally {
    saving.value = false
  }
}

async function acceptCandidate() {
  const draft = candidateDraft.value
  const projectId = projectStore.currentProject?.id
  if (!draft || !projectId) return
  saving.value = true
  setWorkStatus('正在采用候选稿', '正在覆盖原章节、清理候选文件，并刷新下一节方向。')
  try {
    await fileStore.saveFile(projectId, draft.sourcePath, content.value)
    setWorkStatus('正在清理候选稿', '候选稿已经写入原章节，正在删除临时文件。')
    await fileStore.deleteFile(projectId, draft.path)
    candidateDraft.value = null
    delete streamingBuffers.value[draft.path]
    currentFilePath.value = draft.sourcePath
    content.value = normalizeChapterHeading(draft.sourcePath, content.value)
    chapterStatus.value[draft.sourcePath] = isBlankChapter(content.value) ? 'blank' : 'done'
    dirty.value = false
    fileStore.openFile({ name: draft.sourcePath.split('/').pop() || '', path: draft.sourcePath, type: 'file' })
    editorStore.setCurrentFile(draft.sourcePath)
    editorStore.loadContent(draft.sourcePath, content.value)
    await fileStore.loadTree(projectId)
    setWorkStatus('正在刷新下一节方向', '正在根据采用后的正文重新生成下一节爽点卡。')
    await refreshOptions(draft.sourcePath)
    notification.success('已采用候选稿并替换原文')
  } finally {
    saving.value = false
    if (!loadingOptions.value) clearWorkStatus()
  }
}

async function discardCandidate() {
  const draft = candidateDraft.value
  const projectId = projectStore.currentProject?.id
  if (!draft || !projectId) return
  try {
    await fileStore.deleteFile(projectId, draft.path)
  } catch {
    // 候选稿已经不存在时也允许回到原文。
  }
  candidateDraft.value = null
  delete streamingBuffers.value[draft.path]
  await openChapter(draft.sourcePath, { skipOptions: true })
  notification.success('已放弃候选稿')
}

async function refreshOptions(baseFile = currentFilePath.value || null) {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const requestId = ++optionRequestId.value
  loadingOptions.value = true
  optionError.value = ''
  nextCards.value = []
  setWorkStatus('正在生成爽点卡', '正在读取前文、故事引擎和近期上下文，给下一节准备 3 个方向。')
  try {
    const data = await fetchLiteNextOptions(projectId, baseFile, prefs)
    if (requestId !== optionRequestId.value) return
    setWorkStatus('爽点卡已生成', '下一节方向已经准备好，可以选择一张卡继续写。')
    nextCards.value = data.cards
    nextTargetFile.value = data.next_file
    if (!data.cards.length) {
      optionError.value = '这次没有生成出爽点卡，点“刷新”再试一次。'
      nextTargetFile.value = ''
    }
  } catch {
    if (requestId !== optionRequestId.value) return
    optionError.value = '爽点卡生成失败，点“刷新”重试。'
    nextTargetFile.value = ''
  } finally {
    if (requestId === optionRequestId.value) {
      loadingOptions.value = false
      clearWorkStatus()
    }
  }
}

async function generateWithCard(card: LiteNextOptionCard) {
  if (generating.value) return
  await runGeneration(card, 'write', nextTargetFile.value || null)
}

async function rewriteCurrent() {
  if (generating.value) return
  const card = nextCards.value[0]
  if (card && currentFilePath.value) {
    await runGeneration(card, 'rewrite', currentFilePath.value, buildCandidatePath(currentFilePath.value, 'rewrite'))
  }
}

async function improveCurrent(action: 'more_exciting' | 'more_reasonable') {
  if (generating.value) return
  const card = nextCards.value[0]
  if (card && currentFilePath.value) {
    await runGeneration(card, action, currentFilePath.value, buildCandidatePath(currentFilePath.value, action))
  }
}

async function runChatRevision() {
  const instruction = chatRevisionInput.value.trim()
  if (!instruction || generating.value) return
  const sourcePath = candidateDraft.value?.sourcePath || currentFilePath.value
  if (!sourcePath) return
  const label = formatChapterLabel(sourcePath)
  const card: LiteNextOptionCard = {
    id: `chat-revision-${Date.now()}`,
    title: '聊天改稿',
    beat: `根据用户聊天指令改写当前章节：${instruction}`,
    scene: `保留${label}的主要剧情，只调整用户指出的问题。`,
    protagonist_desire: '保持人物核心欲望不变，让行动更贴合用户修改方向。',
    obstacle: '不能破坏前文逻辑、人物动机、章节钩子和既有设定。',
    payoff: `完成用户要求：${instruction}`,
    hook: '保留或加强本节结尾钩子。',
    advancement: '生成一版可采用的候选稿，供用户确认后替换原文。',
  }
  chatRevisionNote.value = `正在根据“${instruction}”生成候选稿。`
  await runGeneration(card, 'rewrite', sourcePath, buildChatRevisionPath(sourcePath))
  chatRevisionNote.value = '候选稿已生成，可以在编辑器中查看并决定是否采用。'
}

function stopGeneration() {
  generationAbortController.value?.abort()
}

async function continueDraft() {
  if (generating.value || !currentFilePath.value || !lastGenerationCard.value) return
  streamingBuffers.value[currentFilePath.value] = content.value
  await runGeneration(lastGenerationCard.value, 'continue', currentFilePath.value)
}

async function runGeneration(card: LiteNextOptionCard, action: LiteWriteAction, targetFile: string | null, outputFile: string | null = null) {
  const projectId = projectStore.currentProject?.id
  if (!projectId || generating.value) return
  const isCandidate = Boolean(outputFile && outputFile !== targetFile)
  const candidateLabel = outputFile?.endsWith('.chat.md') ? '聊天改稿' : candidateActionText(action)
  const sourcePath = targetFile || nextTargetFile.value || currentFilePath.value || ''
  generating.value = true
  const abortController = new AbortController()
  generationAbortController.value = abortController
  lastGenerationCard.value = card
  autoScrollDuringGeneration.value = true
  let generatedFilePath = outputFile || sourcePath
  let streamHeadingPrefix = ''
  const continueBaseContent = action === 'continue' && generatedFilePath ? (streamingBuffers.value[generatedFilePath] || content.value) : ''
  pendingTargetLabel.value = formatChapterLabel(sourcePath)
  setWorkStatus(
    isCandidate ? `正在生成${candidateLabel}候选稿` : `正在写${pendingTargetLabel.value}`,
    isCandidate ? '正在准备当前章节、用户要求和故事状态，候选稿不会覆盖原文。' : '正在准备前文、故事引擎、近期上下文和本节爽点卡。',
  )
  qualitySummary.value = isCandidate
    ? `正在生成${candidateActionText(action)}候选稿，原文不会被覆盖。`
    : `正在写${pendingTargetLabel.value}，已生成的内容会自动保留。`
  try {
    await streamLiteNext(projectId, targetFile || nextTargetFile.value || currentFilePath.value || null, card, prefs, action, {
      onMeta: (meta) => {
        generatedFilePath = meta.file_path
        streamingFilePath.value = meta.file_path
        const displayPath = meta.source_file || meta.file_path
        setWorkStatus(
          meta.is_candidate ? `正在生成${candidateLabel}候选稿` : `正在写${formatChapterLabel(displayPath)}`,
          'AI 已开始响应，正文会流式出现在编辑器里。',
        )
        const headingPrefix = `# ${formatChapterLabel(displayPath)} ${card.title}\n\n`
        streamHeadingPrefix = headingPrefix
        const placeholder = action === 'continue'
          ? continueBaseContent
          : `${headingPrefix}AI 正在起笔，请稍等...`
        streamingBuffers.value[meta.file_path] = action === 'continue' ? continueBaseContent : headingPrefix
        chapterStatus.value[meta.file_path] = 'blank'
        currentFilePath.value = meta.file_path
        pendingTargetLabel.value = formatChapterLabel(displayPath)
        if (meta.is_candidate && meta.source_file) {
          candidateDraft.value = {
            sourcePath: meta.source_file,
            path: meta.file_path,
            action,
            title: card.title,
            content: placeholder,
          }
        }
        content.value = placeholder
        dirty.value = false
        fileStore.openFile({ name: meta.file_path.split('/').pop() || '', path: meta.file_path, type: 'file' })
        editorStore.setCurrentFile(meta.file_path)
        editorStore.loadContent(meta.file_path, placeholder)
        void scrollTextareaToBottom()
      },
      onStatus: (message) => {
        if (message.includes('更新故事状态')) {
          setWorkStatus('正在更新故事状态', '正在写入故事引擎、近期上下文和章节记忆，保证后续连续性。')
        } else if (message.includes('审稿')) {
          setWorkStatus('正在质量审稿', '正在检查逻辑、爽点兑现和连续性。')
        }
        qualitySummary.value = message === 'AI 正在写正文...'
          ? `正在写${pendingTargetLabel.value}，已生成的内容会自动保留。`
          : message
      },
      onDelta: (delta) => {
        if (!generatedFilePath) return
        setWorkStatus(
          isCandidate ? `正在生成${candidateLabel}候选稿` : `正在写${pendingTargetLabel.value}`,
          'AI 正在输出正文，已生成内容会自动保留。',
        )
        const currentBuffer = streamingBuffers.value[generatedFilePath] || ''
        const safeDelta = action !== 'continue' && currentBuffer === streamHeadingPrefix
          ? stripLeadingMarkdownHeading(delta)
          : delta
        const nextContent = action === 'continue' && currentBuffer === continueBaseContent
          ? appendDraftContent(currentBuffer, safeDelta)
          : currentBuffer + safeDelta
        streamingBuffers.value[generatedFilePath] = nextContent
        editorStore.loadContent(generatedFilePath, nextContent)
        if (currentFilePath.value === generatedFilePath) {
          content.value = nextContent
          void scrollTextareaToBottom()
        }
        if (!isBlankChapter(nextContent)) {
          chapterStatus.value[generatedFilePath] = 'done'
        }
      },
      onReplace: (nextContent) => {
        if (!generatedFilePath) return
        streamingBuffers.value[generatedFilePath] = nextContent
        if (candidateDraft.value?.path === generatedFilePath) {
          candidateDraft.value.content = nextContent
        }
        chapterStatus.value[generatedFilePath] = isBlankChapter(nextContent) ? 'blank' : 'done'
        editorStore.loadContent(generatedFilePath, nextContent)
        if (currentFilePath.value === generatedFilePath) {
          content.value = nextContent
          void scrollTextareaToBottom()
        }
      },
      onDone: (result) => {
        setWorkStatus(
          isCandidate ? '候选稿已生成' : '章节已写入',
          isCandidate ? '候选稿已保存，可以采用或放弃。' : '正文已经保存，正在准备后续爽点卡。',
        )
        generatedFilePath = result.file_path
        streamingBuffers.value[result.file_path] = result.content
        if (candidateDraft.value?.path === result.file_path) {
          candidateDraft.value.content = result.content
        }
        chapterStatus.value[result.file_path] = isBlankChapter(result.content) ? 'blank' : 'done'
        qualitySummary.value = result.quality_summary
        engineSummary.value = result.story_engine_summary
        if (result.chapter_plan) {
          chapterMilestone.value = buildChapterMilestone(result, card)
          notification.success(`第${parseSectionPath(result.file_path).ch}章完成，下一章已准备`)
        } else if (action !== 'continue') {
          chapterMilestone.value = null
        }
        dirty.value = false
        fileStore.openFile({ name: result.file_path.split('/').pop() || '', path: result.file_path, type: 'file' })
        editorStore.loadContent(result.file_path, result.content)
        if (currentFilePath.value === result.file_path) {
          content.value = result.content
          editorStore.setCurrentFile(result.file_path)
          void scrollTextareaToBottom()
        }
      },
    }, { signal: abortController.signal }, outputFile)
    generating.value = false
    generationAbortController.value = null
    streamingFilePath.value = ''
    pendingTargetLabel.value = ''
    await fileStore.loadTree(projectId)
    if (!isCandidate) {
      setWorkStatus('正在刷新下一节方向', '正在根据最新正文生成下一节爽点卡。')
      await refreshOptions(generatedFilePath || currentFilePath.value || null)
      notification.success('章节已生成')
    } else {
      notification.success('候选稿已生成')
    }
  } catch (e: any) {
    if (isAbortError(e)) {
      const draft = generatedFilePath ? (streamingBuffers.value[generatedFilePath] || '') : ''
      if (generatedFilePath) {
        chapterStatus.value[generatedFilePath] = draft.trim() ? 'draft' : 'blank'
      }
      dirty.value = Boolean(draft)
      qualitySummary.value = draft
        ? `已停止生成，${pendingTargetLabel.value}的草稿已保留，满意可以保存。`
        : `已停止生成${pendingTargetLabel.value}。`
      notification.success('已停止生成')
    } else {
      notification.error(e.message || '生成失败')
    }
  } finally {
    generating.value = false
    generationAbortController.value = null
    streamingFilePath.value = ''
    pendingTargetLabel.value = ''
    if (!loadingOptions.value) clearWorkStatus()
  }
}

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
