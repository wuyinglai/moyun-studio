<template>
  <div
    class="step-editor-card"
    :style="{ marginLeft: depth * 16 + 'px' }"
  >
    <div class="step-editor-header">
      <div class="step-drag-handle">
        <button
          class="btn-icon-sm"
          aria-label="上移步骤"
          :disabled="!canMoveUp"
          title="上移"
          @click="$emit('move-up')"
        >
          ↑
        </button>
        <button
          class="btn-icon-sm"
          aria-label="下移步骤"
          :disabled="!canMoveDown"
          title="下移"
          @click="$emit('move-down')"
        >
          ↓
        </button>
        <span
          class="step-order"
          @click="expanded = !expanded"
        >{{ index + 1 }}</span>
      </div>
      <input
        v-model="local.label"
        class="step-label-input"
        placeholder="步骤名称"
        @input="emitUpdate"
      >
      <select
        class="step-type-select"
        :value="local.type"
        @change="changeType"
      >
        <option value="pipeline">
          管线
        </option>
        <option value="loop">
          循环
        </option>
        <option value="file">
          文件
        </option>
      </select>
      <button
        class="btn-icon-sm btn-remove"
        aria-label="删除步骤"
        title="删除"
        @click="$emit('remove')"
      >
        ✕
      </button>
    </div>

    <div
      v-if="expanded"
      class="step-config"
    >
      <template v-if="local.type === 'pipeline'">
        <div class="cfg-row">
          <label>管线</label>
          <input
            v-model="local.pipeline"
            placeholder="generate/blueprint"
            @input="emitUpdate"
          >
        </div>
        <div class="cfg-row">
          <label>输出路径</label>
          <input
            v-model="local.output"
            placeholder="projects/{{project_id}}/..."
            @input="emitUpdate"
          >
        </div>
        <div class="cfg-row">
          <label>模式</label>
          <select
            v-model="local.output_mode"
            @change="emitUpdate"
          >
            <option value="write_scene">
              写入场景
            </option>
            <option value="candidate">
              候选稿
            </option>
            <option value="append">
              追加
            </option>
            <option value="dimension_file">
              设定提取
            </option>
          </select>
        </div>
        <div class="cfg-row">
          <label>输入文件</label>
          <input
            v-model="local.input"
            placeholder="可选，{{steps.xxx.output}}"
            @input="emitUpdate"
          >
        </div>
      </template>

      <template v-if="local.type === 'loop'">
        <div class="cfg-row">
          <label>次数</label>
          <input
            v-model="local.count"
            placeholder="10 或 {{variables.xxx}}"
            @input="emitUpdate"
          >
        </div>
        <div class="cfg-row">
          <label>变量名</label>
          <input
            v-model="local.var"
            placeholder="i"
            @input="emitUpdate"
          >
        </div>
        <div class="sub-steps-section">
          <div class="sub-steps-header">
            <span class="section-label">子步骤</span>
            <button
              class="btn-icon"
              aria-label="添加子步骤"
              @click="addSubStep"
            >
              <i class="fa-solid fa-plus" />
            </button>
          </div>
          <StepEditor
            v-for="(sub, si) in local.steps"
            :key="sub.id"
            :step="sub"
            :depth="depth + 1"
            :index="si"
            :can-move-up="si > 0"
            :can-move-down="si < (local.steps?.length || 0) - 1"
            @update="(s: WorkflowStep) => updateSubStep(si, s)"
            @remove="removeSubStep(si)"
            @move-up="moveSubStep(si, -1)"
            @move-down="moveSubStep(si, 1)"
          />
          <div
            v-if="!local.steps || local.steps.length === 0"
            class="no-vars"
          >
            暂无子步骤
          </div>
        </div>
      </template>

      <template v-if="local.type === 'file'">
        <div class="cfg-row">
          <label>操作</label>
          <select
            v-model="local.action"
            @change="emitUpdate"
          >
            <option value="mkdir">
              创建目录
            </option>
            <option value="copy">
              复制文件
            </option>
            <option value="delete">
              删除
            </option>
          </select>
        </div>
        <div class="cfg-row">
          <label>路径</label>
          <input
            v-model="local.path"
            placeholder="projects/.../dir"
            @input="emitUpdate"
          >
        </div>
        <div
          v-if="local.action === 'copy'"
          class="cfg-row"
        >
          <label>源路径</label>
          <input
            v-model="local.input"
            placeholder="来源路径"
            @input="emitUpdate"
          >
        </div>
        <div
          v-if="local.action === 'copy'"
          class="cfg-row"
        >
          <label>目标路径</label>
          <input
            v-model="local.output"
            placeholder="目标路径"
            @input="emitUpdate"
          >
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { WorkflowStep } from '@/composables/useWorkflow'

const props = defineProps<{
  step: WorkflowStep
  depth: number
  index: number
  canMoveUp: boolean
  canMoveDown: boolean
}>()

const emit = defineEmits<{
  'update': [step: WorkflowStep]
  'remove': []
  'move-up': []
  'move-down': []
}>()

const local = ref<WorkflowStep>(clone(props.step))
const expanded = ref(true)

watch(() => props.step, (s) => { local.value = clone(s) }, { deep: true })

function clone(s: WorkflowStep): WorkflowStep {
  return { ...s, steps: s.steps ? JSON.parse(JSON.stringify(s.steps)) : [] }
}

function emitUpdate() { emit('update', { ...local.value }) }

function changeType(e: Event) {
  const type = (e.target as HTMLSelectElement).value
  const s = local.value
  s.type = type
  if (type === 'pipeline') {
    s.pipeline = s.pipeline || ''; s.output = s.output || ''; s.output_mode = 'write_scene'
    s.action = undefined; s.path = undefined; s.count = undefined; s.var = undefined; s.steps = []
  } else if (type === 'loop') {
    s.count = '10'; s.var = 'i'; s.steps = []
    s.pipeline = undefined; s.action = undefined; s.path = undefined
  } else if (type === 'file') {
    s.action = 'mkdir'; s.path = s.path || ''
    s.pipeline = undefined; s.count = undefined; s.var = undefined; s.steps = []
  }
  emitUpdate()
}

function genId(): string {
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}

function addSubStep() {
  if (!local.value.steps) local.value.steps = []
  local.value.steps.push({ id: genId(), label: '子步骤', type: 'pipeline', pipeline: '', output: '', output_mode: 'write_scene' })
  emitUpdate()
}

function updateSubStep(idx: number, s: WorkflowStep) {
  if (local.value.steps) local.value.steps[idx] = s
  emitUpdate()
}

function removeSubStep(idx: number) {
  if (local.value.steps) local.value.steps.splice(idx, 1)
  emitUpdate()
}

function moveSubStep(idx: number, dir: -1 | 1) {
  if (!local.value.steps) return
  const t = idx + dir
  if (t < 0 || t >= local.value.steps.length) return
  const tmp = local.value.steps[t]
  local.value.steps[t] = local.value.steps[idx]
  local.value.steps[idx] = tmp
  emitUpdate()
}
</script>

<style scoped lang="scss">
.step-editor-card {
  background: var(--bg-primary); border-radius: var(--radius-md);
  border: 1px solid var(--border-color); overflow: hidden;
}

.step-editor-header {
  display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  background: var(--bg-card); border-bottom: 1px solid var(--border-color);
}

.step-drag-handle {
  display: flex; align-items: center; gap: 2px;
}

.step-order {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  min-width: 16px; text-align: center; cursor: pointer;
}

.step-label-input {
  flex: 1; padding: 3px 6px; font-size: 12px; border: 1px solid transparent;
  background: transparent; color: var(--text-primary); border-radius: var(--radius-sm);
  outline: none; min-width: 0;
  &:focus { border-color: var(--accent-primary); background: var(--bg-primary); }
}

.step-type-select {
  font-size: 11px; padding: 2px 4px; background: var(--bg-primary);
  border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  color: var(--text-secondary); outline: none; cursor: pointer;
}

.step-config {
  padding: 8px; display: flex; flex-direction: column; gap: 6px;
}

.cfg-row {
  display: flex; align-items: center; gap: 6px;
  label { font-size: 11px; color: var(--text-secondary); min-width: 50px; flex-shrink: 0; }
  input, select {
    flex: 1; padding: 3px 6px; font-size: 11px; background: var(--bg-card);
    border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-primary); outline: none;
    &:focus { border-color: var(--accent-primary); }
  }
}

.btn-icon {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; color: var(--text-muted);
  cursor: pointer; border-radius: var(--radius-sm); font-size: 11px;
  &:hover { background: var(--bg-hover); color: var(--text-primary); }
}

.btn-icon-sm {
  width: 20px; height: 20px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: none; color: var(--text-muted);
  cursor: pointer; border-radius: 4px; font-size: 11px;
  &:hover { background: var(--bg-hover); color: var(--text-primary); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
  &.btn-remove:hover { color: var(--accent-danger); }
}

.section-label {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.3px;
}

.sub-steps-section { margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-color); }
.sub-steps-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }

.no-vars { font-size: 11px; color: var(--text-muted); text-align: center; padding: 6px; }
</style>
