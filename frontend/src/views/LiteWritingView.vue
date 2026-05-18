<template>
  <div class="lite-page">
    <section v-if="!projectStore.currentProject" class="idea-screen">
      <div class="idea-head">
        <div>
          <p class="eyebrow">爽文模式</p>
          <h1>今天想写哪一种爽文？</h1>
          <p class="sub">选一张开局卡，系统会创建作品并进入无大纲创作。</p>
        </div>
        <button class="ghost-btn" :disabled="loadingIdeas" @click="loadIdeas(true)">
          换一批
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

    <section v-else class="writing-shell">
      <aside class="lite-sidebar">
        <div class="side-head">
          <p class="eyebrow">作品</p>
          <h2>{{ projectStore.currentProject.name }}</h2>
        </div>
        <button class="primary-btn full" @click="refreshOptions">
          换个方向
        </button>
        <div class="chapter-list">
          <button
            v-for="node in chapterFiles"
            :key="node.path"
            class="chapter-item"
            :class="{ active: node.path === currentFilePath }"
            @click="openChapter(node.path)"
          >
            {{ formatChapterLabel(node.path) }}
          </button>
        </div>
      </aside>

      <main class="lite-editor">
        <div class="editor-top">
          <div>
            <p class="eyebrow">当前章节</p>
            <h1>{{ currentFilePath ? formatChapterLabel(currentFilePath) : '尚未打开章节' }}</h1>
            <p v-if="currentFilePath" class="path-hint">{{ currentFilePath }}</p>
          </div>
        </div>
        <textarea
          v-model="content"
          class="chapter-textarea"
          placeholder="选择右侧爽点卡开始生成，或在这里直接修改正文..."
          @input="dirty = true"
        />
        <div class="editor-actions">
          <button class="ghost-btn" :disabled="!dirty || saving" @click="saveCurrent">保存</button>
          <button class="ghost-btn" :disabled="!currentFilePath || generating" @click="rewriteCurrent">重写这一章</button>
          <button class="ghost-btn" :disabled="!currentFilePath || generating" @click="improveCurrent('more_exciting')">更爽一点</button>
          <button class="ghost-btn" :disabled="!currentFilePath || generating" @click="improveCurrent('more_reasonable')">更合理一点</button>
        </div>
        <div v-if="qualitySummary" class="quality-line-wrap">
          <span class="quality-line">{{ qualitySummary }}</span>
        </div>
        <div v-if="generating" class="generating-mask">
          正在写{{ pendingTargetLabel }}，正文会实时出现在编辑器里...
        </div>
      </main>

      <aside class="lite-assistant">
        <section class="panel">
          <div class="panel-title">
            <span>下一节爽点卡</span>
            <button class="link-btn" :disabled="loadingOptions" @click="refreshOptions">刷新</button>
          </div>
          <p v-if="loadingOptions" class="option-loading">正在根据前文生成爽点卡...</p>
          <p v-else-if="!nextCards.length" class="option-loading">打开一个章节后生成下一节方向。</p>
          <button
            v-for="card in nextCards"
            :key="card.id"
            class="option-card"
            :disabled="generating"
            @click="generateWithCard(card)"
          >
            <strong>{{ card.title }}</strong>
            <span>{{ card.payoff || card.beat }}</span>
            <small>{{ card.hook }}</small>
            <em>{{ optionActionLabel }}</em>
          </button>
        </section>

        <section class="panel">
          <div class="panel-title">
            <span>关键参数</span>
          </div>
          <label>文风<select v-model="prefs.style"><option v-for="v in styles" :key="v">{{ v }}</option></select></label>
          <label>爽点强度<select v-model="prefs.intensity"><option v-for="v in intensities" :key="v">{{ v }}</option></select></label>
          <label>节奏<select v-model="prefs.pace"><option v-for="v in paces" :key="v">{{ v }}</option></select></label>
          <label>主角性格<select v-model="prefs.protagonist"><option v-for="v in protagonists" :key="v">{{ v }}</option></select></label>
          <label>喜欢的元素<textarea v-model="prefs.likes" rows="2" /></label>
          <label>不要写的内容<textarea v-model="prefs.dislikes" rows="2" /></label>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
  type LiteNextOptionCard,
} from '@/services/liteService'
import { consumeOrFetch, clearCache } from '@/composables/useLitePrefetch'

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
const streamingFilePath = ref('')
const streamingBuffers = ref<Record<string, string>>({})
const qualitySummary = ref('')
const engineSummary = ref<Record<string, string>>({})
const loadingIdeas = ref(false)
const loadingOptions = ref(false)
const optionRequestId = ref(0)
const creating = ref(false)
const generating = ref(false)
const saving = ref(false)
const dirty = ref(false)
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
    return `选这个，自动生成${formatChapterLabel(nextTargetFile.value)}`
  }
  return '选这个，自动生成下一节'
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

    await openChapter(created.first_file)
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
      payoff: card.selling_point,
      hook: '让更大的冲突在结尾露出苗头',
    }
    nextTargetFile.value = created.first_file
    nextCards.value = [openingCard]
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

function isBlankChapter(text: string) {
  const body = text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
    .join('')
  return body.length < 20
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
    payoff: project?.theme || '完成开局爽点兑现',
    hook: '让更大的冲突在结尾露出苗头',
  }
}

async function openProject(projectId: string) {
  await projectStore.openProject(projectId)
  await fileStore.loadTree(projectId)
  const { node: resume, hasWritten } = await findResumeChapter(projectId)
  if (resume) await openChapter(resume.path)
  if (resume && !hasWritten && !creating.value && isBlankChapter(content.value)) {
    const openingCard = buildOpeningCardFromProject()
    nextTargetFile.value = resume.path
    nextCards.value = [openingCard]
    await runGeneration(openingCard, 'write', resume.path)
  } else if (!resume) {
    await refreshOptions()
  }
}

async function findResumeChapter(projectId: string) {
  let lastWritten = chapterFiles.value[0] || null
  let hasWritten = false
  for (const node of chapterFiles.value) {
    const data = await fileStore.readFile(projectId, node.path)
    if (isBlankChapter(data.content || '')) return { node, hasWritten }
    hasWritten = true
    lastWritten = node
  }
  return { node: lastWritten, hasWritten }
}

async function openChapter(path: string) {
  if (!generating.value && !(await confirmDirty())) return
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const buffered = streamingBuffers.value[path]
  const data = buffered === undefined ? await fileStore.readFile(projectId, path) : { content: buffered }
  currentFilePath.value = path
  content.value = normalizeChapterHeading(path, data.content || '')
  fileStore.openFile({ name: path.split('/').pop() || '', path, type: 'file' })
  editorStore.loadContent(path, content.value)
  editorStore.setCurrentFile(path)
  dirty.value = false
  if (!generating.value) {
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
    dirty.value = false
    notification.success('已保存')
  } finally {
    saving.value = false
  }
}

async function refreshOptions(baseFile = currentFilePath.value || null) {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const requestId = ++optionRequestId.value
  loadingOptions.value = true
  nextCards.value = []
  try {
    const data = await fetchLiteNextOptions(projectId, baseFile, prefs)
    if (requestId !== optionRequestId.value) return
    nextCards.value = data.cards
    nextTargetFile.value = data.next_file
  } finally {
    if (requestId === optionRequestId.value) {
      loadingOptions.value = false
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
  if (card) await runGeneration(card, 'rewrite', currentFilePath.value)
}

async function improveCurrent(action: 'more_exciting' | 'more_reasonable') {
  if (generating.value) return
  const card = nextCards.value[0]
  if (card) await runGeneration(card, action, currentFilePath.value)
}

async function runGeneration(card: LiteNextOptionCard, action: 'write' | 'rewrite' | 'more_exciting' | 'more_reasonable', targetFile: string | null) {
  const projectId = projectStore.currentProject?.id
  if (!projectId || generating.value) return
  generating.value = true
  let generatedFilePath = targetFile || nextTargetFile.value || currentFilePath.value || ''
  pendingTargetLabel.value = formatChapterLabel(targetFile || nextTargetFile.value || currentFilePath.value || '')
  qualitySummary.value = `正在生成${pendingTargetLabel.value}...`
  try {
    await streamLiteNext(projectId, targetFile || nextTargetFile.value || currentFilePath.value || null, card, prefs, action, {
      onMeta: (meta) => {
        generatedFilePath = meta.file_path
        streamingFilePath.value = meta.file_path
        streamingBuffers.value[meta.file_path] = ''
        currentFilePath.value = meta.file_path
        pendingTargetLabel.value = formatChapterLabel(meta.file_path)
        content.value = ''
        dirty.value = false
        fileStore.openFile({ name: meta.file_path.split('/').pop() || '', path: meta.file_path, type: 'file' })
        editorStore.setCurrentFile(meta.file_path)
        editorStore.loadContent(meta.file_path, '')
      },
      onStatus: (message) => {
        qualitySummary.value = message
      },
      onDelta: (delta) => {
        if (!generatedFilePath) return
        const nextContent = (streamingBuffers.value[generatedFilePath] || '') + delta
        streamingBuffers.value[generatedFilePath] = nextContent
        editorStore.loadContent(generatedFilePath, nextContent)
        if (currentFilePath.value === generatedFilePath) {
          content.value = nextContent
        }
      },
      onReplace: (nextContent) => {
        if (!generatedFilePath) return
        streamingBuffers.value[generatedFilePath] = nextContent
        editorStore.loadContent(generatedFilePath, nextContent)
        if (currentFilePath.value === generatedFilePath) {
          content.value = nextContent
        }
      },
      onDone: (result) => {
        generatedFilePath = result.file_path
        streamingBuffers.value[result.file_path] = result.content
        qualitySummary.value = result.quality_summary
        engineSummary.value = result.story_engine_summary
        if (result.chapter_plan) {
          notification.success(`第 ${result.file_path.match(/ch-(\d+)/)?.[1] || ''} 章完成，已生成下一章规划`)
        }
        dirty.value = false
        fileStore.openFile({ name: result.file_path.split('/').pop() || '', path: result.file_path, type: 'file' })
        editorStore.loadContent(result.file_path, result.content)
        if (currentFilePath.value === result.file_path) {
          content.value = result.content
          editorStore.setCurrentFile(result.file_path)
        }
      },
    })
    await fileStore.loadTree(projectId)
    await refreshOptions(generatedFilePath || currentFilePath.value || null)
    notification.success('章节已生成')
  } catch (e: any) {
    notification.error(e.message || '生成失败')
  } finally {
    generating.value = false
    streamingFilePath.value = ''
    pendingTargetLabel.value = ''
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
}

.chapter-item.active,
.chapter-item:hover {
  color: var(--gold-primary);
  border-color: rgba(201, 169, 110, .35);
  background: rgba(201, 169, 110, .08);
}

.panel {
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.option-card {
  width: 100%;
  padding: 12px;
  border-radius: 7px;
  margin-top: 10px;
  display: grid;
  gap: 7px;
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

.ghost-btn {
  background: transparent;
  color: var(--text-primary);
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
