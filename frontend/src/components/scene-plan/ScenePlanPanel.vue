<template>
  <div
    class="scene-plan-panel"
    data-testid="scene-plan-panel"
  >
    <div class="panel-header">
      <span class="panel-title">场景计划</span>
      <button
        class="btn-refresh"
        :disabled="loading"
        @click="handleLoad"
      >
        <i class="fa-solid fa-rotate"></i>
      </button>
    </div>

    <!-- 非场景文件提示 -->
    <div
      v-if="!isSceneFile"
      class="empty-state"
    >
      <i class="fa-solid fa-file-circle-xmark"></i>
      <span>当前文件不是场景文件</span>
      <span class="hint">Scene Plan 仅支持 sec-*.md 场景文件</span>
    </div>

    <!-- 场景文件操作区 -->
    <template v-else>
      <!-- 当前状态 -->
      <div class="status-bar">
        <span
          v-if="isEditMode"
          class="status-badge editing"
        >
          <i class="fa-solid fa-pen-to-square"></i> 编辑中
          <span v-if="isDirty" class="dirty-indicator">*</span>
        </span>
        <span
          v-else-if="savedScenePlan"
          class="status-badge saved"
        >
          <i class="fa-solid fa-check"></i> 已保存
        </span>
        <span
          v-else-if="generatedScenePlan"
          class="status-badge generated"
        >
          <i class="fa-solid fa-pen"></i> 已生成
        </span>
        <span
          v-else
          class="status-badge empty"
        >
          <i class="fa-solid fa-circle"></i> 未保存
        </span>
        <span
          v-if="currentTargetFile"
          class="current-file"
        >
          {{ currentTargetFile }}
        </span>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button
          v-if="!isEditMode"
          class="btn-action btn-load"
          :disabled="loading || generating || saving"
          @click="handleLoad"
        >
          <i class="fa-solid fa-folder-open"></i>
          加载
        </button>

        <!-- 使用 Scene Plan 开关 -->
        <div
          v-if="!isEditMode && displayScenePlan && validationResult?.valid"
          class="use-scene-plan-toggle"
        >
          <label class="toggle-label">
            <input
              type="checkbox"
              :checked="useScenePlanForGen"
              :disabled="!canUseScenePlan"
              @change="onUseScenePlanToggle"
            />
            <span class="toggle-text">Professional 生成时使用</span>
          </label>
        </div>
        <div
          v-if="!isEditMode && displayScenePlan && !validationResult?.valid"
          class="use-scene-plan-disabled"
        >
          <i class="fa-solid fa-lock"></i>
          <span>Scene Plan 无效，无法用于生成</span>
        </div>
        <div
          v-if="!isEditMode && !displayScenePlan"
          class="use-scene-plan-disabled"
        >
          <i class="fa-solid fa-file-circle-question"></i>
          <span>请先生成或加载 Scene Plan</span>
        </div>
        <button
          v-if="!isEditMode"
          class="btn-action btn-generate"
          :disabled="loading || generating || saving || !llmConnected"
          @click="handleGenerate"
        >
          <i class="fa-solid fa-wand-magic-sparkles"></i>
          生成
        </button>
        <button
          v-if="!isEditMode && displayScenePlan"
          class="btn-action btn-edit"
          :disabled="loading || generating || saving"
          @click="startEdit"
        >
          <i class="fa-solid fa-pen-to-square"></i>
          编辑 JSON
        </button>
        <button
          v-if="isEditMode"
          class="btn-action btn-cancel"
          :disabled="loading || generating || saving"
          @click="cancelEdit"
        >
          <i class="fa-solid fa-xmark"></i>
          取消
        </button>
        <button
          v-if="isEditMode"
          class="btn-action btn-validate"
          :disabled="loading || generating || saving || !isJsonValid"
          @click="doValidate"
        >
          <i class="fa-solid fa-check-double"></i>
          校验
        </button>
        <button
          v-if="!isEditMode"
          class="btn-action btn-save"
          :disabled="!canSave || saving"
          @click="handleSave"
        >
          <i class="fa-solid fa-floppy-disk"></i>
          保存
        </button>
        <button
          v-if="isEditMode"
          class="btn-action btn-save"
          :disabled="!canEditSave || saving"
          @click="handleEditSave"
        >
          <i class="fa-solid fa-floppy-disk"></i>
          保存
        </button>
      </div>

      <!-- 错误提示 -->
      <div
        v-if="errorMessage"
        class="error-message"
      >
        <i class="fa-solid fa-circle-exclamation"></i>
        {{ errorMessage }}
      </div>

      <!-- 冲突提示 -->
      <div
        v-if="conflictMessage"
        class="conflict-message"
      >
        <i class="fa-solid fa-triangle-exclamation"></i>
        {{ conflictMessage }}
        <div class="conflict-actions">
          <button
            class="btn-small"
            @click="handleOverwrite"
          >
            覆盖
          </button>
          <button
            class="btn-small"
            @click="conflictMessage = ''"
          >
            取消
          </button>
        </div>
      </div>

      <!-- 加载中 -->
      <div
        v-if="loading"
        class="loading-state"
      >
        <i class="fa-solid fa-spinner fa-spin"></i>
        加载中...
      </div>

      <!-- 生成中 -->
      <div
        v-if="generating"
        class="generating-state"
      >
        <i class="fa-solid fa-spinner fa-spin"></i>
        生成中...
      </div>

      <!-- 保存中 -->
      <div
        v-if="saving"
        class="saving-state"
      >
        <i class="fa-solid fa-spinner fa-spin"></i>
        保存中...
      </div>

      <!-- 校验中 -->
      <div
        v-if="validating"
        class="validating-state"
      >
        <i class="fa-solid fa-spinner fa-spin"></i>
        校验中...
      </div>

      <!-- JSON 解析错误 -->
      <div
        v-if="isEditMode && parseError"
        class="error-message"
      >
        <i class="fa-solid fa-circle-exclamation"></i>
        JSON 解析错误: {{ parseError }}
      </div>

      <!-- 校验结果 -->
      <div
        v-if="validationResult && !generating && !saving"
        class="validation-result"
      >
        <!-- valid 状态 -->
        <div
          class="validation-badge"
          :class="validationResult.valid ? 'valid' : 'invalid'"
        >
          <i
            :class="validationResult.valid ? 'fa-solid fa-check-circle' : 'fa-solid fa-xmark-circle'"
          ></i>
          {{ validationResult.valid ? '校验通过' : '校验失败' }}
        </div>

        <!-- 错误列表 -->
        <div
          v-if="validationResult.errors.length > 0"
          class="validation-errors"
        >
          <div class="validation-title">
            <i class="fa-solid fa-circle-exclamation"></i> 错误
          </div>
          <div
            v-for="(err, idx) in validationResult.errors"
            :key="idx"
            class="validation-item error"
          >
            {{ err.field }}: {{ err.message }}
          </div>
        </div>

        <!-- 警告列表 -->
        <div
          v-if="validationResult.warnings.length > 0"
          class="validation-warnings"
        >
          <div class="validation-title">
            <i class="fa-solid fa-triangle-exclamation"></i> 警告
          </div>
          <div
            v-for="(warn, idx) in validationResult.warnings"
            :key="idx"
            class="validation-item warning"
          >
            {{ warn.field }}: {{ warn.message }}
          </div>
        </div>
      </div>

      <!-- 编辑模式：JSON 编辑器 -->
      <div
        v-if="isEditMode"
        class="scene-plan-editor"
      >
        <div class="editor-header">
          <span>编辑 JSON</span>
        </div>
        <textarea
          v-model="editJsonString"
          class="editor-textarea"
          spellcheck="false"
          @input="onJsonInput"
        ></textarea>
      </div>

      <!-- 查看模式：JSON 预览 -->
      <div
        v-else-if="displayScenePlan"
        class="scene-plan-preview"
      >
        <div class="preview-header">
          <span>计划内容</span>
        </div>
        <pre class="preview-content">{{ formatJson(displayScenePlan) }}</pre>
      </div>

      <!-- 保存成功提示 -->
      <div
        v-if="savedPath"
        class="saved-path"
      >
        <i class="fa-solid fa-check"></i>
        已保存到: {{ savedPath }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useLLMStore } from '@/stores/llm'
import { useNotificationStore } from '@/stores/notification'
import { isSceneFile as checkIsSceneFile } from '@/modules/scene/scenePath'
import {
  generateScenePlan,
  saveScenePlan,
  loadScenePlan,
  validateScenePlan,
  setCurrentScenePlan,
  clearCurrentScenePlan,
  setUseScenePlanForGeneration,
  getUseScenePlanForGeneration,
  type ScenePlanData,
  type ScenePlanGenerateResponse,
} from '@/composables/useScenePlan'

const editorStore = useEditorStore()
const projectStore = useProjectStore()
const llmStore = useLLMStore()
const notification = useNotificationStore()

// 状态
const loading = ref(false)
const generating = ref(false)
const saving = ref(false)
const validating = ref(false)
const errorMessage = ref('')
const conflictMessage = ref('')
const savedPath = ref('')
const savedScenePlan = ref<ScenePlanData | null>(null)
const generatedScenePlan = ref<ScenePlanData | null>(null)
const validationResult = ref<{
  valid: boolean
  errors: Array<{ field: string; message: string }>
  warnings: Array<{ field: string; message: string }>
} | null>(null)
const lastLoadedTargetFile = ref('')
const autoLoadInProgress = ref(false)

// 编辑模式状态
const isEditMode = ref(false)
const editJsonString = ref('')
const isDirty = ref(false)
const parseError = ref('')
const editedScenePlan = ref<ScenePlanData | null>(null)

// Professional 生成时使用 Scene Plan 的开关状态
const useScenePlanForGen = ref(false)

// 是否可以使用 Scene Plan 进行生成
const canUseScenePlan = computed(() => {
  return displayScenePlan.value !== null && validationResult.value?.valid
})

// 计算属性
const currentTargetFile = computed(() => editorStore.currentFilePath || '')

const isSceneFile = computed(() => checkIsSceneFile(currentTargetFile.value))

const llmConnected = computed(() => llmStore.isConnected)

const displayScenePlan = computed(() => generatedScenePlan.value || savedScenePlan.value)

const canSave = computed(() => {
  if (!validationResult.value?.valid) return false
  if (!displayScenePlan.value) return false
  return true
})

const isJsonValid = computed(() => {
  return !parseError.value && editJsonString.value.trim().length > 0
})

const canEditSave = computed(() => {
  if (!isJsonValid.value) return false
  if (!validationResult.value?.valid) return false
  if (!editedScenePlan.value) return false
  return true
})

// 格式化 JSON
function formatJson(data: ScenePlanData | null): string {
  if (!data) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

// 加载已保存的 Scene Plan
async function doLoad(isAutoLoad = false) {
  if (!isSceneFile.value) return
  if (!projectStore.currentProject?.id) {
    if (!isAutoLoad) notification.warning('请先打开项目')
    return
  }

  if (
    isAutoLoad && lastLoadedTargetFile.value === currentTargetFile.value && savedScenePlan.value !== null
  ) {
    // 避免重复加载同一个文件
    return
  }

  loading.value = true
  autoLoadInProgress.value = isAutoLoad
  errorMessage.value = ''
  conflictMessage.value = ''
  savedPath.value = ''
  isEditMode.value = false

  try {
    const response = await loadScenePlan(
      projectStore.currentProject.id,
      currentTargetFile.value
    )

    lastLoadedTargetFile.value = currentTargetFile.value

    if (response.exists && response.scene_plan) {
      savedScenePlan.value = response.scene_plan
      generatedScenePlan.value = null
      validationResult.value = {
        valid: true,
        errors: [],
        warnings: [],
      }
      if (!isAutoLoad) notification.success('已加载保存的 Scene Plan')
    } else {
      savedScenePlan.value = null
      generatedScenePlan.value = null
      validationResult.value = null
      // 自动加载时不显示通知
      if (!isAutoLoad) notification.info('暂无保存的 Scene Plan')
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    errorMessage.value = `加载失败: ${msg}`
  } finally {
    loading.value = false
    autoLoadInProgress.value = false
  }
}

// 手动加载按钮处理
async function handleLoad() {
  await doLoad(false)
}

// 监听文件切换，自动加载
watch(currentTargetFile, (newFile) => {
  savedScenePlan.value = null
  generatedScenePlan.value = null
  validationResult.value = null
  errorMessage.value = ''
  conflictMessage.value = ''
  savedPath.value = ''
  isEditMode.value = false
  editJsonString.value = ''
  isDirty.value = false
  parseError.value = ''
  editedScenePlan.value = null

  if (newFile && isSceneFile.value && projectStore.currentProject?.id) {
    doLoad(true)
  }
}, { immediate: true })

// 组件挂载时尝试自动加载
onMounted(() => {
  if (currentTargetFile.value && isSceneFile.value && projectStore.currentProject?.id) {
    doLoad(true)
  }
})

// 生成 Scene Plan
async function handleGenerate() {
  if (!isSceneFile.value) return
  if (!projectStore.currentProject?.id) {
    notification.warning('请先打开项目')
    return
  }
  if (!llmConnected.value) {
    notification.warning('请先配置 LLM 连接')
    return
  }

  generating.value = true
  errorMessage.value = ''
  conflictMessage.value = ''
  savedPath.value = ''
  savedScenePlan.value = null
  isEditMode.value = false

  try {
    const response: ScenePlanGenerateResponse = await generateScenePlan({
      project_id: projectStore.currentProject.id,
      target_file: currentTargetFile.value,
      dry_run: true,
      include_raw_output: false,
    })

    if (response.scene_plan) {
      generatedScenePlan.value = response.scene_plan
      validationResult.value = {
        valid: response.valid,
        errors: response.errors,
        warnings: response.warnings,
      }
    } else {
      generatedScenePlan.value = null
      validationResult.value = {
        valid: false,
        errors: [{ field: 'scene_plan', message: '生成结果为空' }],
        warnings: [],
      }
      errorMessage.value = '生成结果为空'
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    errorMessage.value = `生成失败: ${msg}`
  } finally {
    generating.value = false
  }
}

// 保存 Scene Plan（查看模式）
async function handleSave() {
  if (!canSave.value) return
  if (!projectStore.currentProject?.id) {
    notification.warning('请先打开项目')
    return
  }

  saving.value = true
  errorMessage.value = ''
  conflictMessage.value = ''
  savedPath.value = ''

  try {
    const scenePlanToSave = displayScenePlan.value!
    const response = await saveScenePlan({
      project_id: projectStore.currentProject.id,
      target_file: currentTargetFile.value,
      scene_plan: scenePlanToSave,
      overwrite: false,
    })

    if (response.saved) {
      savedPath.value = response.path || ''
      savedScenePlan.value = scenePlanToSave
      generatedScenePlan.value = null
      notification.success('Scene Plan 已保存')
    } else if (response.conflict) {
      conflictMessage.value = response.message || '文件已存在，是否覆盖？'
    } else {
      errorMessage.value = response.message || '保存失败'
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    errorMessage.value = `保存失败: ${msg}`
  } finally {
    saving.value = false
  }
}

// 开始编辑
function startEdit() {
  if (!displayScenePlan.value) return
  isEditMode.value = true
  editJsonString.value = formatJson(displayScenePlan.value)
  isDirty.value = false
  parseError.value = ''
  editedScenePlan.value = { ...displayScenePlan.value }
}

// 取消编辑
function cancelEdit() {
  isEditMode.value = false
  editJsonString.value = ''
  isDirty.value = false
  parseError.value = ''
  editedScenePlan.value = null
}

// JSON 输入处理
function onJsonInput() {
  isDirty.value = true
  parseError.value = ''
  editedScenePlan.value = null

  try {
    if (editJsonString.value.trim()) {
      editedScenePlan.value = JSON.parse(editJsonString.value) as ScenePlanData
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    parseError.value = msg
  }
}

// 校验 Scene Plan
async function doValidate() {
  if (!isJsonValid.value || !editedScenePlan.value) return
  validating.value = true
  errorMessage.value = ''
  try {
    const response = await validateScenePlan(editedScenePlan.value)
    validationResult.value = {
      valid: response.valid,
      errors: response.errors,
      warnings: response.warnings,
    }
    if (response.valid) {
      notification.success('校验通过')
    } else {
      notification.warning('校验失败')
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    errorMessage.value = `校验失败: ${msg}`
  } finally {
    validating.value = false
  }
}

// 保存编辑后的 Scene Plan
async function handleEditSave() {
  if (!canEditSave.value || !editedScenePlan.value) return
  if (!projectStore.currentProject?.id) {
    notification.warning('请先打开项目')
    return
  }

  saving.value = true
  errorMessage.value = ''
  conflictMessage.value = ''
  savedPath.value = ''

  try {
    const response = await saveScenePlan({
      project_id: projectStore.currentProject.id,
      target_file: currentTargetFile.value,
      scene_plan: editedScenePlan.value,
      overwrite: false,
    })

    if (response.saved) {
      savedPath.value = response.path || ''
      savedScenePlan.value = editedScenePlan.value
      generatedScenePlan.value = null
      isEditMode.value = false
      editJsonString.value = ''
      isDirty.value = false
      parseError.value = ''
      editedScenePlan.value = null
      notification.success('Scene Plan 已保存')
    } else if (response.conflict) {
      conflictMessage.value = response.message || '文件已存在，是否覆盖？'
    } else {
      errorMessage.value = response.message || '保存失败'
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    errorMessage.value = `保存失败: ${msg}`
  } finally {
    saving.value = false
  }
}

// 覆盖保存
async function handleOverwrite() {
  let scenePlanToSave: ScenePlanData | null = null
  if (isEditMode.value) {
    scenePlanToSave = editedScenePlan.value
  } else {
    scenePlanToSave = displayScenePlan.value
  }

  if (!scenePlanToSave) return
  if (!projectStore.currentProject?.id) return

  conflictMessage.value = ''
  saving.value = true

  try {
    const response = await saveScenePlan({
      project_id: projectStore.currentProject.id,
      target_file: currentTargetFile.value,
      scene_plan: scenePlanToSave,
      overwrite: true,
    })

    if (response.saved) {
      savedPath.value = response.path || ''
      savedScenePlan.value = scenePlanToSave
      generatedScenePlan.value = null
      if (isEditMode.value) {
        isEditMode.value = false
        editJsonString.value = ''
        isDirty.value = false
        parseError.value = ''
        editedScenePlan.value = null
      }
      notification.success('Scene Plan 已覆盖保存')
    } else {
      errorMessage.value = response.message || '覆盖保存失败'
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    errorMessage.value = `覆盖保存失败: ${msg}`
  } finally {
    saving.value = false
  }
}

// 切换 Professional 生成时使用 Scene Plan 的开关
function onUseScenePlanToggle(event: Event) {
  const target = event.target as HTMLInputElement
  const enabled = target.checked
  useScenePlanForGen.value = enabled
  setUseScenePlanForGeneration(enabled)
  if (enabled) {
    notification.info('已启用：Professional 生成时将使用当前 Scene Plan')
  } else {
    notification.info('已关闭：Professional 生成时不使用 Scene Plan')
  }
}

// 更新全局共享状态
function updateGlobalScenePlanState() {
  const plan = displayScenePlan.value
  const valid = validationResult.value?.valid || false
  const saved = savedScenePlan.value !== null
  setCurrentScenePlan(plan, valid, currentTargetFile.value, saved)
}

// 监听状态变化，更新全局状态
watch([displayScenePlan, validationResult, currentTargetFile], () => {
  updateGlobalScenePlanState()
}, { deep: true })

// 组件挂载时初始化全局状态
onMounted(() => {
  if (currentTargetFile.value && isSceneFile.value && projectStore.currentProject?.id) {
    doLoad(true)
  }
  // 初始化开关状态
  useScenePlanForGen.value = getUseScenePlanForGeneration()
})

// 监听文件切换，清除全局状态
watch(currentTargetFile, (newFile) => {
  savedScenePlan.value = null
  generatedScenePlan.value = null
  validationResult.value = null
  errorMessage.value = ''
  conflictMessage.value = ''
  savedPath.value = ''
  isEditMode.value = false
  editJsonString.value = ''
  isDirty.value = false
  parseError.value = ''
  editedScenePlan.value = null
  useScenePlanForGen.value = false

  // 清除全局状态
  clearCurrentScenePlan()
  setUseScenePlanForGeneration(false)

  if (newFile && isSceneFile.value && projectStore.currentProject?.id) {
    doLoad(true)
  }
}, { immediate: true })
</script>

<style scoped lang="scss">
.scene-plan-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: 12px;
  gap: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .panel-title {
    font-weight: 600;
    font-size: 14px;
    color: var(--text-primary);
  }

  .btn-refresh {
    padding: 4px 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 4px;

    &:hover:not(:disabled) {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 8px;
  color: var(--text-muted);
  text-align: center;

  i {
    font-size: 32px;
    opacity: 0.5;
  }

  .hint {
    font-size: 12px;
    color: var(--text-faint);
  }
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;

    &.saved {
      background: rgba(34, 197, 94, 0.15);
      color: var(--accent-success);
    }

    &.generated {
      background: rgba(59, 130, 246, 0.15);
      color: var(--accent-primary);
    }

    &.empty {
      background: var(--bg-hover);
      color: var(--text-muted);
    }

    &.editing {
      background: rgba(245, 158, 11, 0.15);
      color: var(--accent-warning);

      .dirty-indicator {
        font-weight: bold;
      }
    }
  }

  .current-file {
    font-size: 11px;
    color: var(--text-faint);
    font-family: monospace;
  }
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;

  .btn-action {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    background: var(--bg-card);
    color: var(--text-secondary);
    border-radius: var(--radius-md);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: var(--bg-hover);
      color: var(--text-primary);
      border-color: var(--border-color);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    &.btn-generate {
      color: var(--accent-primary);
      border-color: rgba(59, 130, 246, 0.3);

      &:hover:not(:disabled) {
        background: rgba(59, 130, 246, 0.1);
      }
    }

    &.btn-edit {
      color: var(--accent-warning);
      border-color: rgba(245, 158, 11, 0.3);

      &:hover:not(:disabled) {
        background: rgba(245, 158, 11, 0.1);
      }
    }

    &.btn-validate {
      color: var(--accent-primary);
      border-color: rgba(59, 130, 246, 0.3);

      &:hover:not(:disabled) {
        background: rgba(59, 130, 246, 0.1);
      }
    }

    &.btn-cancel {
      color: var(--text-muted);
      border-color: rgba(156, 163, 175, 0.3);

      &:hover:not(:disabled) {
        background: var(--bg-hover);
      }
    }

    &.btn-save {
      color: var(--accent-success);
      border-color: rgba(34, 197, 94, 0.3);

      &:hover:not(:disabled) {
        background: rgba(34, 197, 94, 0.1);
      }
    }
  }
}

.error-message {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-md);
  color: var(--accent-danger);
  font-size: 12px;

  i {
    margin-top: 2px;
  }
}

.conflict-message {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: var(--radius-md);
  color: var(--accent-warning);
  font-size: 12px;

  .conflict-actions {
    display: flex;
    gap: 4px;
    margin-left: auto;

    .btn-small {
      padding: 2px 8px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-secondary);
      border-radius: 4px;
      font-size: 11px;
      cursor: pointer;

      &:hover {
        background: var(--bg-hover);
      }
    }
  }
}

.loading-state,
.generating-state,
.saving-state,
.validating-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  color: var(--text-muted);
  font-size: 12px;
}

.validation-result {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .validation-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: var(--radius-md);
    font-size: 12px;
    font-weight: 500;

    &.valid {
      background: rgba(34, 197, 94, 0.1);
      color: var(--accent-success);
    }

    &.invalid {
      background: rgba(239, 68, 68, 0.1);
      color: var(--accent-danger);
    }
  }

  .validation-errors,
  .validation-warnings {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .validation-title {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 2px;
    }

    .validation-item {
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 4px;

      &.error {
        background: rgba(239, 68, 68, 0.08);
        color: var(--accent-danger);
      }

      &.warning {
        background: rgba(234, 179, 8, 0.08);
        color: var(--accent-warning);
      }
    }
  }
}

.scene-plan-preview,
.scene-plan-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;

  .preview-header,
  .editor-header {
    padding: 6px 12px;
    background: var(--bg-card);
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border-color);
  }

  .preview-content {
    margin: 0;
    padding: 12px;
    background: var(--bg-card);
    font-family: monospace;
    font-size: 11px;
    color: var(--text-secondary);
    overflow-x: auto;
    max-height: 300px;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .editor-textarea {
    width: 100%;
    min-height: 300px;
    max-height: 500px;
    padding: 12px;
    background: var(--bg-card);
    color: var(--text-secondary);
    font-family: monospace;
    font-size: 11px;
    border: none;
    resize: vertical;
    outline: none;
    line-height: 1.5;
  }
}

.saved-path {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: var(--radius-md);
  color: var(--accent-success);
  font-size: 11px;
  font-family: monospace;
}
</style>
