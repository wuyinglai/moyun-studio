<template>
  <div class="workflow-panel">
    <!-- ─── 模式切换：列表 / 详情 / 编辑器 ─── -->
    <template v-if="mode === 'list'">
      <div class="panel-section-header">
        <span class="section-title">工作流</span>
        <div class="header-actions">
          <button
            class="btn-icon"
            :disabled="isRunning"
            title="刷新"
            @click="refresh"
          >
            <i class="fa-solid fa-rotate" />
          </button>
          <button
            class="btn-icon"
            title="新建"
            @click="startNew"
          >
            <i class="fa-solid fa-plus" />
          </button>
        </div>
      </div>

      <div
        v-if="workflows.length === 0"
        class="section-empty"
      >
        <i class="fa-solid fa-diagram-project" />
        <span>{{ isLoading ? '加载中...' : '暂无工作流' }}</span>
      </div>

      <div
        v-else
        class="workflow-list"
      >
        <div
          v-for="wf in workflows"
          :key="wf.name"
          class="workflow-card"
        >
          <div
            class="wf-card-body"
            @click="selectWorkflow(wf.name)"
          >
            <div class="wf-card-header">
              <span class="wf-name">{{ wf.label }}</span>
              <span class="wf-badge">{{ countSteps(wf.steps as WorkflowStep[]) }} 步</span>
            </div>
            <p class="wf-desc">
              {{ wf.description || '无描述' }}
            </p>
          </div>
          <div class="wf-card-actions">
            <button
              class="btn-action"
              title="编辑"
              @click="editWorkflow(wf.name)"
            >
              <i class="fa-solid fa-pen" />
            </button>
            <button
              class="btn-action btn-action--del"
              title="删除"
              @click="handleDelete(wf.name)"
            >
              <i class="fa-solid fa-trash-can" />
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- ─── 详情视图 ─── -->
    <template v-if="mode === 'detail'">
      <div class="detail-view">
        <div class="detail-header">
          <button
            class="btn-back"
            @click="mode = 'list'"
          >
            <i class="fa-solid fa-arrow-left" />
          </button>
          <div class="detail-title">
            <strong>{{ detail?.label || selectedName }}</strong>
            <span class="detail-desc">{{ detail?.description }}</span>
          </div>
        </div>

        <!-- ─── 节点状态面板 ─── -->
        <div
          v-if="hasRun"
          class="node-status-panel"
        >
          <div class="section-label">
            节点状态
          </div>
          <!-- 当前运行节点 -->
          <div
            v-if="currentNode"
            class="current-node"
            :class="{ 'waiting': currentNode.waiting_for_user }"
          >
            <div class="node-header">
              <span class="node-badge" :class="`executor-${currentNode.executor}`">
                {{ currentNode.executor_label }}
              </span>
              <span class="node-type">{{ currentNode.node_label }}</span>
            </div>
            <div class="node-name">
              {{ currentNode.label }}
            </div>
            <div
              v-if="currentNode.waiting_for_user"
              class="waiting-actions"
            >
              <span class="waiting-reason">{{ currentNode.waiting_reason }}</span>
              <div class="action-buttons">
                <button
                  v-for="action in currentNode.actions"
                  :key="action"
                  class="action-btn"
                  :class="`action-${action}`"
                  @click="handleNodeAction(action)"
                >
                  {{ actionLabel(action) }}
                </button>
              </div>
            </div>
            <div
              v-else
              class="node-progress"
            >
              <span class="progress-text">运行中...</span>
            </div>
          </div>
          <!-- 步骤树预览 -->
          <div class="step-tree">
            <div
              v-for="step in stepsPreview"
              :key="step.id"
              class="tree-step"
              :class="`status-${nodeStates[step.id] || 'pending'}`"
            >
              <span class="step-status-icon">{{ nodeStatusIcon(nodeStates[step.id]) }}</span>
              <span class="step-executor">{{ step.executor_label }}</span>
              <span class="step-label">{{ step.label }}</span>
              <span class="step-type-badge">{{ step.node_label }}</span>
            </div>
          </div>
        </div>

        <!-- ─── 变量池面板 ─── -->
        <div
          v-if="hasRun && variablePool.length > 0"
          class="variable-pool-panel"
        >
          <div class="section-label">
            变量池
          </div>
          <div class="var-pool-list">
            <div
              v-for="entry in variablePool"
              :key="entry.key"
              class="var-pool-entry"
              :class="`source-${entry.source}`"
            >
              <span class="var-key">{{ entry.key }}</span>
              <span class="var-value">{{ truncateValue(entry.value) }}</span>
              <span class="var-source">{{ entry.source }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="!hasRun"
          class="step-overview"
        >
          <div class="section-label">
            步骤预览
          </div>
          <div class="step-tree">
            <div
              v-for="step in detail?.steps || []"
              :key="step.id"
              class="tree-step"
            >
              <span class="step-icon">{{ stepIcon(step.type) }}</span>
              <span class="step-label">{{ step.label }}</span>
              <span class="step-badge">{{ step.type }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="!hasRun"
          class="var-config"
        >
          <div class="section-label">
            变量配置
          </div>
          <div
            v-for="(_val, key) in varOverrides"
            :key="key"
            class="var-field"
          >
            <label :for="'wf-var-' + key">{{ key }}</label>
            <input
              :id="'wf-var-' + key"
              v-model="varOverrides[key]"
              type="text"
            >
          </div>
          <div
            v-if="Object.keys(varOverrides).length === 0"
            class="no-vars"
          >
            无需配置变量
          </div>
        </div>

        <div
          v-if="runLogs.length > 0"
          class="run-logs"
        >
          <div class="section-label">
            执行日志
          </div>
          <div
            ref="logRef"
            class="log-container"
          >
            <div
              v-for="(log, i) in runLogs"
              :key="i"
              class="log-line"
              :class="logClass(log)"
            >
              {{ log }}
            </div>
          </div>
        </div>

        <div class="detail-actions">
          <button
            v-if="!isRunning && !hasRun"
            class="btn-run"
            @click="handleRun"
          >
            <i class="fa-solid fa-play" /> 运行
          </button>
          <button
            v-if="isRunning"
            class="btn-stop"
            @click="handleStop"
          >
            <i class="fa-solid fa-stop" /> 停止
          </button>
          <button
            v-if="hasRun && !isRunning"
            class="btn-run"
            @click="handleRunAgain"
          >
            <i class="fa-solid fa-rotate" /> 重新运行
          </button>
          <button
            class="btn-ghost"
            title="编辑"
            @click="editWorkflow(selectedName!)"
          >
            <i class="fa-solid fa-pen" /> 编辑
          </button>
        </div>
      </div>
    </template>

    <!-- ─── 编辑器 ─── -->
    <template v-if="mode === 'editor'">
      <div class="editor-view">
        <div class="detail-header">
          <button
            class="btn-back"
            @click="exitEditor"
          >
            <i class="fa-solid fa-arrow-left" />
          </button>
          <div class="detail-title">
            <strong>{{ editData.name ? '编辑: ' + editData.label : '新建工作流' }}</strong>
          </div>
          <button
            class="btn-save"
            :disabled="!editData.name || !editData.label"
            @click="handleSave"
          >
            <i class="fa-solid fa-floppy-disk" /> 保存
          </button>
        </div>

        <!-- 基本信息 -->
        <div class="editor-section">
          <div class="section-label">
            基本信息
          </div>
          <div class="form-field">
            <label>标识名</label>
            <input
              v-model="editData.name"
              placeholder="write-chapters"
              :disabled="isEditing"
            >
          </div>
          <div class="form-field">
            <label>名称</label>
            <input
              v-model="editData.label"
              placeholder="批量写章节"
            >
          </div>
          <div class="form-field">
            <label>描述</label>
            <input
              v-model="editData.description"
              placeholder="工作流描述"
            >
          </div>
        </div>

        <!-- 变量 -->
        <div class="editor-section">
          <div class="section-label-row">
            <span class="section-label">变量</span>
            <button
              class="btn-icon"
              @click="addVariable"
            >
              <i class="fa-solid fa-plus" />
            </button>
          </div>
          <div
            v-for="(_, idx) in editVarKeys"
            :key="'var-' + idx"
            class="var-row"
          >
            <input
              v-model="editVarKeys[idx]"
              class="var-key"
              placeholder="key"
            >
            <input
              v-model="editData.variables[editVarKeys[idx]]"
              class="var-val"
              placeholder="default"
            >
            <button
              class="btn-icon-sm"
              @click="removeVariable(idx)"
            >
              ✕
            </button>
          </div>
          <div
            v-if="editVarKeys.length === 0"
            class="no-vars"
          >
            无变量
          </div>
        </div>

        <!-- 步骤 -->
        <div class="editor-section steps-section">
          <div class="section-label-row">
            <span class="section-label">步骤</span>
            <button
              class="btn-icon"
              @click="addStep"
            >
              <i class="fa-solid fa-plus" />
            </button>
          </div>
          <div
            ref="stepEditorListRef"
            class="step-editor-list"
          >
            <StepEditor
              v-for="(step, idx) in editData.steps"
              :key="step.id"
              :step="step"
              :depth="0"
              :index="idx"
              :can-move-up="idx > 0"
              :can-move-down="idx < editData.steps.length - 1"
              @update="(s) => updateStep(idx, s)"
              @remove="removeStep(idx)"
              @move-up="moveStep(idx, -1)"
              @move-down="moveStep(idx, 1)"
            />
          </div>
          <div
            v-if="editData.steps.length === 0"
            class="no-vars"
          >
            暂无步骤，点击 + 添加
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<!-- ─── 子组件：步骤编辑器 ─── -->
<script setup lang="ts">
import { ref, reactive, watch, nextTick, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import { useWorkflow, type WorkflowStep, type Workflow } from '@/composables/useWorkflow'
import StepEditor from './StepEditor.vue'
import Sortable from 'sortablejs'

const projectStore = useProjectStore()
const notification = useNotificationStore()
const {
  workflows, isLoading, isRunning, currentRunId, runLogs,
  currentNode, nodeStates, stepsPreview, variablePool,
  fetchWorkflows, fetchWorkflowDetail, runWorkflow, stopWorkflow,
  saveWorkflow, deleteWorkflow,
} = useWorkflow()

const mode = ref<'list' | 'detail' | 'editor'>('list')
const selectedName = ref<string | null>(null)
const detail = ref<Workflow | null>(null)
const varOverrides = ref<Record<string, string>>({})
const hasRun = ref(false)
const logRef = ref<HTMLElement | null>(null)
const stepEditorListRef = ref<HTMLElement | null>(null)
let sortableInstance: any = null

// 编辑器数据
const editData = reactive<{ name: string; label: string; description: string; variables: Record<string, string>; steps: WorkflowStep[] }>({
  name: '', label: '', description: '', variables: {}, steps: [],
})
const editVarKeys = ref<string[]>([])
const isEditing = ref(false)  // true = editing existing, false = creating new

watch(runLogs, async () => {
  await nextTick()
  if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
}, { deep: true })

// ─── 节点状态辅助函数 ───

function nodeStatusIcon(status: string | undefined): string {
  switch (status) {
    case 'pending': return '○'
    case 'running': return '◐'
    case 'waiting_for_user': return '◔'
    case 'completed': return '●'
    case 'failed': return '✕'
    case 'skipped': return '⊘'
    default: return '○'
  }
}

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    approve: '通过',
    edit_and_approve: '编辑后通过',
    regenerate: '重新生成',
    stop: '停止',
  }
  return labels[action] || action
}

function truncateValue(value: string, maxLen = 50): string {
  if (value.length <= maxLen) return value
  return value.slice(0, maxLen) + '...'
}

function handleNodeAction(action: string) {
  // TODO: 实现 Human 节点动作处理
  notification.info(`执行动作: ${actionLabel(action)}`)
}

// ─── SortableJS 拖拽排序 ───

function initSortable() {
  destroySortable()
  if (!stepEditorListRef.value) return
  sortableInstance = Sortable.create(stepEditorListRef.value, {
    handle: '.step-drag-handle',
    animation: 150,
    easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    ghostClass: 'step-dragging',
    onEnd: (evt: any) => {
      const { oldIndex, newIndex } = evt
      if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) return
      const item = editData.steps.splice(oldIndex, 1)[0]
      editData.steps.splice(newIndex, 0, item)
    },
  })
}

function destroySortable() {
  if (sortableInstance) {
    sortableInstance.destroy()
    sortableInstance = null
  }
}

watch(mode, async (val) => {
  if (val === 'editor') {
    await nextTick()
    initSortable()
  } else {
    destroySortable()
  }
})

function countSteps(steps: WorkflowStep[]): number {
  let total = 0
  for (const s of steps) { total++; if (s.type === 'loop' && s.steps) total += countSteps(s.steps as WorkflowStep[]) }
  return total
}

function stepIcon(type: string): string {
  switch (type) {
    case 'pipeline': return '⚡'
    case 'loop': return '🔄'
    case 'file': return '📁'
    default: return '⬜'
  }
}

function logClass(log: string): string {
  if (log.includes('[错误]')) return 'log-error'
  if (log.includes('[停止]')) return 'log-warn'
  if (log.includes('[完成]') || log.includes('[步骤] 完成')) return 'log-success'
  return 'log-info'
}

// ─── 列表操作 ───

async function refresh() { await fetchWorkflows() }

async function selectWorkflow(name: string) {
  selectedName.value = name
  detail.value = await fetchWorkflowDetail(name)
  const vars: Record<string, string> = {}
  if (detail.value?.variables) for (const [k, v] of Object.entries(detail.value.variables)) vars[k] = String(v)
  varOverrides.value = vars
  hasRun.value = false
  mode.value = 'detail'
}

// ─── 编辑器操作 ───

function startNew() {
  isEditing.value = false
  editData.name = ''
  editData.label = ''
  editData.description = ''
  editData.variables = {}
  editData.steps = []
  editVarKeys.value = []
  mode.value = 'editor'
}

async function editWorkflow(name: string) {
  const wf = await fetchWorkflowDetail(name)
  if (!wf) { notification.error('加载工作流失败'); return }
  isEditing.value = true
  editData.name = wf.name
  editData.label = wf.label
  editData.description = wf.description || ''
  editData.variables = { ...(wf.variables || {}) }
  editData.steps = JSON.parse(JSON.stringify(wf.steps || []))
  editVarKeys.value = Object.keys(editData.variables)
  mode.value = 'editor'
}

function exitEditor() {
  mode.value = selectedName.value ? 'detail' : 'list'
}

async function handleSave() {
  if (!editData.name.trim()) { notification.warning('请填写标识名'); return }
  if (!editData.label.trim()) { notification.warning('请填写名称'); return }

  const vars: Record<string, string> = {}
  for (const k of editVarKeys.value) {
    if (k.trim()) vars[k.trim()] = editData.variables[k] || ''
  }

  const ok = await saveWorkflow({
    name: editData.name.trim(),
    label: editData.label.trim(),
    description: editData.description.trim(),
    variables: vars,
    steps: editData.steps,
  })
  if (ok) {
    notification.success('工作流已保存')
    selectedName.value = editData.name.trim()
    detail.value = await fetchWorkflowDetail(selectedName.value!)
    mode.value = 'detail'
  } else {
    notification.error('保存失败')
  }
}

async function handleDelete(name: string) {
  if (!confirm(`确定删除工作流「${name}」？`)) return
  const ok = await deleteWorkflow(name)
  if (ok) notification.success('已删除')
}

// ─── 变量操作 ───

function addVariable() {
  const key = `var_${editVarKeys.value.length + 1}`
  editVarKeys.value.push(key)
  editData.variables[key] = ''
}

function removeVariable(idx: number) {
  const key = editVarKeys.value[idx]
  delete editData.variables[key]
  editVarKeys.value.splice(idx, 1)
}

// ─── 步骤操作 ───

function generateId(): string {
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}

function addStep() {
  editData.steps.push({
    id: generateId(),
    label: '新步骤',
    type: 'pipeline',
    pipeline: '',
    output: '',
    output_mode: 'overwrite',
  })
}

function updateStep(idx: number, updated: WorkflowStep) {
  editData.steps[idx] = updated
}

function removeStep(idx: number) {
  editData.steps.splice(idx, 1)
}

function moveStep(idx: number, dir: -1 | 1) {
  const target = idx + dir
  if (target < 0 || target >= editData.steps.length) return
  const tmp = editData.steps[target]
  editData.steps[target] = editData.steps[idx]
  editData.steps[idx] = tmp
}

// ─── 运行操作 ───

async function handleRun() {
  const projectId = projectStore.currentProject?.project_id
  if (!projectId) { notification.warning('请先打开一个项目'); return }
  if (!selectedName.value) return
  hasRun.value = true
  const variables: Record<string, string> = {}
  if (detail.value?.variables) for (const [k, v] of Object.entries(detail.value.variables)) variables[k] = varOverrides.value[k] || String(v)
  const ok = await runWorkflow(selectedName.value, projectId, variables)
  if (ok) {
    notification.success('工作流执行完成')
  } else {
    notification.error('工作流执行失败')
  }
}

async function handleStop() {
  if (currentRunId.value) await stopWorkflow(currentRunId.value)
  notification.warning('已发送停止信号')
}

async function handleRunAgain() {
  hasRun.value = false
  await handleRun()
}

onMounted(() => { fetchWorkflows() })
</script>

<style scoped lang="scss">
.workflow-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 12px;
  gap: 10px;
}

// ─── Common ───

.panel-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.section-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none;
  color: var(--text-muted); cursor: pointer; border-radius: var(--radius-sm);
  font-size: 12px;
  &:hover { background: var(--bg-card); color: var(--text-primary); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.btn-icon-sm {
  width: 20px; height: 20px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: none;
  color: var(--text-muted); cursor: pointer; border-radius: 4px;
  font-size: 11px;
  &:hover { background: var(--bg-hover); color: var(--text-primary); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
  &.btn-remove:hover { color: var(--accent-danger); }
}

.section-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 24px; color: var(--text-muted); font-size: 13px;
  i { font-size: 28px; opacity: 0.4; }
}

.no-vars {
  font-size: 11px; color: var(--text-muted); text-align: center; padding: 8px;
}

// ─── List ───

.workflow-list {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;
}

.workflow-card {
  background: var(--bg-card); border-radius: var(--radius-md); overflow: hidden;
  border: 1px solid transparent; transition: all 0.2s;
  &:hover { border-color: var(--accent-primary); }
}

.wf-card-body {
  padding: 10px 12px; cursor: pointer;
}

.wf-card-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 3px;
}

.wf-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.wf-badge { font-size: 10px; color: var(--text-muted); background: var(--bg-primary); padding: 2px 8px; border-radius: 10px; }
.wf-desc { font-size: 11px; color: var(--text-muted); margin: 0; line-height: 1.4; }

.wf-card-actions {
  display: flex; gap: 2px; padding: 0 12px 6px; justify-content: flex-end;
}

.btn-action {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; cursor: pointer; border-radius: var(--radius-sm);
  color: var(--text-muted); font-size: 12px;
  &:hover { background: var(--bg-hover); color: var(--text-primary); }
  &--del:hover { color: var(--accent-danger); }
}

// ─── Detail ───

.detail-view {
  display: flex; flex-direction: column; gap: 10px; overflow-y: auto; flex: 1;
}

.detail-header {
  display: flex; align-items: flex-start; gap: 8px;
}

.btn-back {
  width: 28px; height: 28px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-card); border: none; color: var(--text-secondary);
  cursor: pointer; border-radius: var(--radius-sm);
  &:hover { background: var(--bg-hover); color: var(--text-primary); }
}

.detail-title {
  display: flex; flex-direction: column; gap: 2px; flex: 1;
  strong { font-size: 14px; color: var(--text-primary); }
}
.detail-desc { font-size: 11px; color: var(--text-muted); }

.step-overview {
  background: var(--bg-card); border-radius: var(--radius-md); padding: 10px;
}
.step-tree { display: flex; flex-direction: column; gap: 3px; }
.tree-step {
  display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: var(--radius-sm); font-size: 12px;
  .step-icon { width: 20px; text-align: center; font-size: 14px; }
  .step-label { flex: 1; color: var(--text-primary); }
  .step-badge { font-size: 10px; padding: 1px 6px; border-radius: 6px; background: var(--bg-primary); color: var(--text-muted); }
  // 节点状态样式
  .step-status-icon { width: 16px; text-align: center; font-size: 11px; }
  .step-executor { font-size: 10px; padding: 1px 4px; border-radius: 4px; background: var(--bg-primary); color: var(--text-muted); }
  .step-type-badge { font-size: 10px; color: var(--text-muted); }
  // 状态颜色
  &.status-pending { opacity: 0.6; }
  &.status-running { .step-status-icon { color: var(--accent-primary); } }
  &.status-waiting_for_user { .step-status-icon { color: var(--accent-warning); } }
  &.status-completed { .step-status-icon { color: var(--accent-success); } }
  &.status-failed { .step-status-icon { color: var(--accent-danger); } }
  &.status-skipped { opacity: 0.5; }
}

// ─── 节点状态面板 ───

.node-status-panel {
  background: var(--bg-card); border-radius: var(--radius-md); padding: 10px;

  .current-node {
    background: var(--bg-primary); border-radius: var(--radius-sm); padding: 10px; margin-bottom: 8px;
    border-left: 3px solid var(--accent-primary);
    &.waiting {
      border-left-color: var(--accent-warning);
      background: rgba(251, 191, 36, 0.1);
    }
    .node-header {
      display: flex; align-items: center; gap: 6px; margin-bottom: 4px;
    }
    .node-badge {
      font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 500;
      &.executor-ai { background: var(--accent-primary); color: white; }
      &.executor-human { background: var(--accent-warning); color: black; }
      &.executor-system { background: var(--text-muted); color: white; }
    }
    .node-type { font-size: 11px; color: var(--text-secondary); }
    .node-name { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
    .waiting-actions {
      .waiting-reason { font-size: 11px; color: var(--accent-warning); display: block; margin-bottom: 6px; }
      .action-buttons { display: flex; gap: 4px; flex-wrap: wrap; }
      .action-btn {
        padding: 4px 8px; border: none; border-radius: 4px; font-size: 11px; cursor: pointer; transition: all 0.2s;
        &.action-approve { background: var(--accent-success); color: white; &:hover { opacity: 0.9; } }
        &.action-edit_and_approve { background: var(--accent-primary); color: white; &:hover { opacity: 0.9; } }
        &.action-regenerate { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border-color); &:hover { border-color: var(--accent-primary); } }
        &.action-stop { background: transparent; color: var(--accent-danger); border: 1px solid var(--accent-danger); &:hover { background: var(--accent-danger); color: white; } }
      }
    }
    .node-progress {
      .progress-text { font-size: 11px; color: var(--accent-primary); }
    }
  }
}

// ─── 变量池面板 ───

.variable-pool-panel {
  background: var(--bg-card); border-radius: var(--radius-md); padding: 10px;

  .var-pool-list { display: flex; flex-direction: column; gap: 4px; }
  .var-pool-entry {
    display: flex; align-items: center; gap: 8px; padding: 4px 8px; background: var(--bg-primary); border-radius: 4px; font-size: 11px;
    .var-key { font-family: monospace; color: var(--accent-primary); min-width: 80px; }
    .var-value { flex: 1; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .var-source { font-size: 9px; padding: 1px 4px; border-radius: 3px; text-transform: uppercase; }
    &.source-user .var-source { background: var(--bg-hover); color: var(--text-muted); }
    &.source-ai .var-source { background: rgba(59, 130, 246, 0.2); color: var(--accent-primary); }
    &.source-system .var-source { background: rgba(148, 163, 184, 0.2); color: var(--text-secondary); }
    &.source-approved .var-source { background: rgba(74, 222, 128, 0.2); color: var(--accent-success); }
  }
}

.var-config, .run-logs { background: var(--bg-card); border-radius: var(--radius-md); padding: 10px; }

.var-field {
  display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
  label { font-size: 11px; color: var(--text-secondary); min-width: 50px; font-family: monospace; }
  input {
    flex: 1; padding: 4px 8px; font-size: 12px; background: var(--bg-primary);
    border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); outline: none;
    &:focus { border-color: var(--accent-primary); }
  }
}

.log-container {
  background: var(--bg-primary); border-radius: var(--radius-md); padding: 6px 8px;
  font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; overflow-y: auto; max-height: 150px;
}
.log-line { padding: 2px 4px; margin-bottom: 1px; }
.log-info { color: var(--text-secondary); }
.log-success { color: var(--accent-success); }
.log-warn { color: var(--accent-warning); }
.log-error { color: var(--accent-danger); }

.detail-actions {
  display: flex; gap: 6px;
  button { flex: 1; padding: 7px 12px; border: none; border-radius: var(--radius-md); font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 4px; }
}

.btn-run { background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); color: white; &:hover { opacity: 0.9; } }
.btn-stop { background: var(--accent-danger); color: white; &:hover { opacity: 0.9; } }
.btn-ghost { background: var(--bg-card); color: var(--text-secondary); &:hover { background: var(--bg-hover); color: var(--text-primary); } }

// ─── Editor ───

.editor-view {
  display: flex; flex-direction: column; gap: 10px; overflow-y: auto; flex: 1;
}

.btn-save {
  padding: 5px 12px; background: var(--accent-primary); color: white; border: none;
  border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; cursor: pointer; white-space: nowrap;
  &:hover { opacity: 0.9; } &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.editor-section {
  background: var(--bg-card); border-radius: var(--radius-md); padding: 10px;
}

.form-field {
  display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
  label { font-size: 11px; color: var(--text-secondary); min-width: 45px; }
  input {
    flex: 1; padding: 4px 8px; font-size: 12px; background: var(--bg-primary);
    border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); outline: none;
    &:focus { border-color: var(--accent-primary); }
    &:disabled { opacity: 0.5; }
  }
}

.var-row {
  display: flex; gap: 4px; margin-bottom: 4px;
  .var-key { flex: 1; width: 0; }
  .var-val { flex: 2; }
  input {
    padding: 3px 6px; font-size: 11px; background: var(--bg-primary);
    border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); outline: none;
    &:focus { border-color: var(--accent-primary); }
  }
}

.steps-section { flex: 1; }
.step-editor-list { display: flex; flex-direction: column; gap: 6px; min-height: 40px; }
.step-dragging { opacity: 0.5; outline: 2px dashed var(--accent-primary); outline-offset: -2px; }
</style>
