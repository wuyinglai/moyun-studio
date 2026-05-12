<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal modal--wide">

          <!-- 头部 -->
          <div class="modal-header">
            <h3 class="modal-title">
              <i class="fa-solid" :class="stepIcon"></i>
              {{ stepTitle }}
            </h3>
            <button class="modal-close" @click="close">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>

          <!-- 步骤1：创作参数 -->
          <div v-if="wizard.currentStep.value <= 1" class="modal-body">
            <p class="step-desc">选择创作参数，AI 将为你生成书名和创意</p>
            <div class="form-group">
              <label class="form-label">题材 *</label>
              <div class="btn-group">
                <button
                  v-for="opt in genreOptions"
                  :key="opt"
                  class="btn-option"
                  :class="{ active: wizard.params.value.genre === opt }"
                  @click="wizard.params.value.genre = opt"
                >{{ opt }}</button>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">基调</label>
                <div class="btn-group">
                  <button
                    v-for="opt in toneOptions"
                    :key="opt"
                    class="btn-option"
                    :class="{ active: wizard.params.value.tone === opt }"
                    @click="wizard.params.value.tone = opt"
                  >{{ opt }}</button>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">写作风格</label>
                <div class="btn-group">
                  <button
                    v-for="opt in styleOptions"
                    :key="opt"
                    class="btn-option"
                    :class="{ active: wizard.params.value.writing_style === opt }"
                    @click="wizard.params.value.writing_style = opt"
                  >{{ opt }}</button>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">作品规模</label>
              <div class="btn-group">
                <button
                  v-for="opt in scaleOptions"
                  :key="opt.value"
                  class="btn-option"
                  :class="{ active: wizard.params.value.target_word_count === opt.value }"
                  @click="wizard.params.value.target_word_count = opt.value"
                >
                  {{ opt.label }}
                  <span class="option-hint">{{ opt.hint }}</span>
                </button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">作者（可选）</label>
              <input
                v-model="wizard.params.value.author"
                type="text"
                class="form-input"
                placeholder="作者名"
              />
            </div>
          </div>

          <!-- 步骤1.5：书名创意 -->
          <div v-if="wizard.currentStep.value === 1.5" class="modal-body">
            <p class="step-desc">AI 为你生成了书名和创意，确认或编辑后继续</p>
            <div class="idea-box" v-if="wizard.bookIdea.value">
              <div class="form-group">
                <label class="form-label">书名</label>
                <input v-model="wizard.bookIdea.value.name" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">创意描述</label>
                <textarea
                  v-model="wizard.bookIdea.value.description"
                  class="form-textarea"
                  rows="5"
                ></textarea>
              </div>
            </div>
            <div v-else class="loading-box">
              <i class="fa-solid fa-spinner fa-spin"></i>
              <span>AI 正在生成创意...</span>
            </div>
          </div>

          <!-- 步骤2：生成大纲 -->
          <div v-if="wizard.currentStep.value === 2" class="modal-body">
            <p class="step-desc">AI 正在根据参数生成章节大纲...</p>
            <div class="loading-box">
              <i class="fa-solid fa-spinner fa-spin"></i>
              <span>AI 正在生成大纲，预计需要 1-2 分钟...</span>
            </div>
          </div>

          <!-- 步骤2.5：确认大纲 -->
          <div v-if="wizard.currentStep.value === 2.5" class="modal-body">
            <p class="step-desc">请确认大纲，编辑后点击确认</p>
            <div class="form-group">
              <label class="form-label">大纲内容（Jinja2 模板格式）</label>
              <textarea
                v-model="wizard.editedOutline.value"
                class="form-textarea"
                rows="12"
              ></textarea>
            </div>
            <div class="outline-info" v-if="wizard.outline.value">
              <span>预估 {{ wizard.estimatedChapters }} 章 / {{ wizard.estimatedVolumes }} 卷</span>
            </div>
          </div>

          <!-- 步骤3：完成 -->
          <div v-if="wizard.currentStep.value === 3" class="modal-body">
            <div class="success-box">
              <i class="fa-solid fa-circle-check"></i>
              <h4>项目创建成功！</h4>
              <p>项目 "{{ createdProjectName }}" 已创建，文件结构已生成。</p>
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="modal-footer">
            <button
              v-if="wizard.currentStep.value <= 1"
              class="btn btn-primary"
              :disabled="!wizard.params.value.genre || wizard.isGenerating.value"
              @click="startGenerate"
            >
              <i v-if="!wizard.isGenerating.value" class="fa-solid fa-magic"></i>
              <i v-else class="fa-solid fa-spinner fa-spin"></i>
              {{ wizard.isGenerating.value ? '生成中...' : '生成书名与创意' }}
            </button>

            <button
              v-if="wizard.currentStep.value === 1.5"
              class="btn btn-secondary"
              @click="wizard.editBookIdea()"
            >重新生成</button>
            <button
              v-if="wizard.currentStep.value === 1.5"
              class="btn btn-primary"
              @click="proceedToOutline"
              :disabled="wizard.isGenerating.value"
            >
              <i v-if="!wizard.isGenerating.value" class="fa-solid fa-magic"></i>
              <i v-else class="fa-solid fa-spinner fa-spin"></i>
              {{ wizard.isGenerating.value ? '创建项目中...' : '下一步：生成大纲' }}
            </button>

            <button
              v-if="wizard.currentStep.value === 2.5"
              class="btn btn-secondary"
              @click="wizard.editOutline()"
            >重新生成大纲</button>
            <button
              v-if="wizard.currentStep.value === 2.5"
              class="btn btn-primary"
              @click="startCreateProject"
              :disabled="wizard.isGenerating.value"
            >
              <i v-if="!wizard.isGenerating.value" class="fa-solid fa-check"></i>
              <i v-else class="fa-solid fa-spinner fa-spin"></i>
              {{ wizard.isGenerating.value ? '创建中...' : '确认并创建项目' }}
            </button>

            <button
              v-if="wizard.currentStep.value === 3"
              class="btn btn-primary"
              @click="close"
            >开始写作</button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useProjectWizard } from '@/composables/useProjectWizard'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'

const wizard = useProjectWizard()
const uiStore = useUIStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()

// 监听 wizard 步骤变化，step=2 时自动触发大纲生成
watch(
  () => wizard.currentStep.value,
  async (step) => {
    if (step === 2 && projectStore.currentProject && !wizard.outline.value) {
      // 刚创建完项目，进入步骤2时自动触发生成大纲
      await wizard.generateOutline(projectStore.currentProject.id)
    }
  }
)

const visible = computed(() => uiStore.modals.createProject)

const genreOptions = ['都市', '玄幻', '修仙', '科幻', '悬疑', '历史', '言情', '武侠']
const toneOptions = ['热血', '轻松', '悬疑', '治愈', '黑暗', '搞笑']
const styleOptions = ['细腻', '简洁', '幽默', '严肃', '抒情', '快节奏']
const scaleOptions = [
  { label: '5万字', value: 50000, hint: '≈ 28章' },
  { label: '10万字', value: 100000, hint: '≈ 56章' },
  { label: '15万字', value: 150000, hint: '≈ 84章' },
  { label: '20万字', value: 200000, hint: '≈ 112章' },
]

const stepTitle = computed(() => {
  const s = wizard.currentStep.value
  if (s <= 1) return '新建项目 - 创作参数'
  if (s === 1.5) return '书名与创意'
  if (s === 2) return '生成大纲中...'
  if (s === 2.5) return '确认大纲'
  return '创建完成'
})

const stepIcon = computed(() => {
  const s = wizard.currentStep.value
  if (s <= 1) return 'fa-feather-pointed'
  if (s === 1.5) return 'fa-lightbulb'
  if (s === 2) return 'fa-list-ol'
  if (s === 2.5) return 'fa-file-lines'
  return 'fa-circle-check'
})

const createdProjectName = computed(() => projectStore.currentProject?.name || '')

async function startGenerate() {
  await wizard.generateBookIdea()
}

async function startGenerateOutline() {
  if (!projectStore.currentProject) return
  await wizard.generateOutline(projectStore.currentProject.id)
}

async function proceedToOutline() {
  // 1. 先用当前书名创建项目（占位）
  await wizard.acceptBookIdea()
  // acceptBookIdea 内部已将 currentStep 设为 2
  // 2. 加载中，generateOutline 会自动在 step=2 时触发（通过 watch）
}

async function startCreateProject() {
  if (!projectStore.currentProject) return
  await wizard.acceptOutlineAndCreate()
}

function close() {
  wizard.reset()
  uiStore.closeCreateProject()
}
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--bg-secondary);
  border-radius: var(--radius-xl);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.modal--wide {
  max-width: 700px;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;
  i { color: var(--accent-primary); }
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all 0.2s;
  &:hover { background: var(--bg-card); color: var(--text-primary); }
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
}

.step-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn-option {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  font-family: inherit;
  &:hover { border-color: var(--accent-primary); color: var(--accent-primary); }
  &.active {
    background: var(--accent-primary);
    color: white;
    border-color: var(--accent-primary);
  }
  .option-hint { font-size: 11px; opacity: 0.7; margin-left: 4px; }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
  &:focus { border-color: var(--accent-primary); }
}

.form-textarea {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
  &:focus { border-color: var(--accent-primary); }
}

.idea-box,
.outline-info {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.loading-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-muted);
  font-size: 14px;
  i { color: var(--accent-primary); font-size: 20px; }
}

.success-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);
  i { color: var(--accent-success); font-size: 48px; }
  h4 { font-size: 18px; color: var(--text-primary); margin: 0; }
  p { font-size: 14px; margin: 0; text-align: center; }
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  &:disabled { opacity: 0.5; cursor: not-allowed; }
  &-primary {
    background: var(--accent-primary);
    color: white;
    &:hover:not(:disabled) { filter: brightness(1.1); }
  }
  &-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    &:hover:not(:disabled) { border-color: var(--accent-primary); }
  }
}

// 过渡动画
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
  .modal { transition: transform 0.2s ease; }
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  .modal { transform: scale(0.95); }
}
</style>
