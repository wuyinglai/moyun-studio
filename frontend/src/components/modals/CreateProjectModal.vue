<template>
  <a-modal
    :open="visible"
    :title="stepTitle"
    :footer="null"
    :width="700"
    :closable="true"
    @cancel="close"
  >
    <template #title>
      <span style="display: flex; align-items: center; gap: 10px;">
        <i class="fa-solid" :class="stepIcon" style="color: var(--accent-primary);"></i>
        {{ stepTitle }}
      </span>
    </template>

    <!-- 步骤1：创作参数 -->
    <div v-if="wizard.currentStep.value <= 1">
      <p class="step-desc">选择创作参数，AI 将为你生成书名和创意</p>
      
      <a-form layout="vertical" style="margin-top: 16px;">
        <a-form-item label="题材 *">
          <div class="param-header">
            <span></span>
            <button class="btn-edit-param" @click="toggleEditCategory('genre')" title="管理选项">
              <i class="fa-solid fa-pen"></i>
            </button>
          </div>
          <a-radio-group v-model:value="wizard.params.value.genre" button-style="solid">
            <a-radio-button v-for="opt in genreOptions" :key="opt" :value="opt">
              {{ opt }}
            </a-radio-button>
          </a-radio-group>
          <div v-if="editingCategory === 'genre'" class="param-edit-row">
            <a-input v-model:value="newOptionInput" placeholder="新增选项" size="small" @pressEnter="addCustomOption('genre')" />
            <a-button size="small" type="primary" @click="addCustomOption('genre')">添加</a-button>
            <div class="param-option-list">
              <span v-for="opt in genreOptions" :key="opt" class="param-option-tag">
                {{ opt }}
                <button class="btn-remove-option" @click="removeCustomOption('genre', opt)">&times;</button>
              </span>
            </div>
          </div>
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="基调">
              <div class="param-header">
                <span></span>
                <button class="btn-edit-param" @click="toggleEditCategory('tone')" title="管理选项">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </div>
              <a-radio-group v-model:value="wizard.params.value.tone" button-style="solid">
                <a-radio-button v-for="opt in toneOptions" :key="opt" :value="opt">
                  {{ opt }}
                </a-radio-button>
              </a-radio-group>
              <div v-if="editingCategory === 'tone'" class="param-edit-row">
                <a-input v-model:value="newOptionInput" placeholder="新增选项" size="small" @pressEnter="addCustomOption('tone')" />
                <a-button size="small" type="primary" @click="addCustomOption('tone')">添加</a-button>
                <div class="param-option-list">
                  <span v-for="opt in toneOptions" :key="opt" class="param-option-tag">
                    {{ opt }}
                    <button class="btn-remove-option" @click="removeCustomOption('tone', opt)">&times;</button>
                  </span>
                </div>
              </div>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="写作风格">
              <div class="param-header">
                <span></span>
                <button class="btn-edit-param" @click="toggleEditCategory('writing_style')" title="管理选项">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </div>
              <a-radio-group v-model:value="wizard.params.value.writing_style" button-style="solid">
                <a-radio-button v-for="opt in styleOptions" :key="opt" :value="opt">
                  {{ opt }}
                </a-radio-button>
              </a-radio-group>
              <div v-if="editingCategory === 'writing_style'" class="param-edit-row">
                <a-input v-model:value="newOptionInput" placeholder="新增选项" size="small" @pressEnter="addCustomOption('writing_style')" />
                <a-button size="small" type="primary" @click="addCustomOption('writing_style')">添加</a-button>
                <div class="param-option-list">
                  <span v-for="opt in styleOptions" :key="opt" class="param-option-tag">
                    {{ opt }}
                    <button class="btn-remove-option" @click="removeCustomOption('writing_style', opt)">&times;</button>
                  </span>
                </div>
              </div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="背景">
              <div class="param-header">
                <span></span>
                <button class="btn-edit-param" @click="toggleEditCategory('background')" title="管理选项">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </div>
              <a-radio-group v-model:value="wizard.params.value.background" button-style="solid">
                <a-radio-button v-for="opt in bgOptions" :key="opt" :value="opt">
                  {{ opt }}
                </a-radio-button>
              </a-radio-group>
              <div v-if="editingCategory === 'background'" class="param-edit-row">
                <a-input v-model:value="newOptionInput" placeholder="新增选项" size="small" @pressEnter="addCustomOption('background')" />
                <a-button size="small" type="primary" @click="addCustomOption('background')">添加</a-button>
                <div class="param-option-list">
                  <span v-for="opt in bgOptions" :key="opt" class="param-option-tag">
                    {{ opt }}
                    <button class="btn-remove-option" @click="removeCustomOption('background', opt)">&times;</button>
                  </span>
                </div>
              </div>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="主题">
              <div class="param-header">
                <span></span>
                <button class="btn-edit-param" @click="toggleEditCategory('theme')" title="管理选项">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </div>
              <a-radio-group v-model:value="wizard.params.value.theme" button-style="solid">
                <a-radio-button v-for="opt in themeOptions" :key="opt" :value="opt">
                  {{ opt }}
                </a-radio-button>
              </a-radio-group>
              <div v-if="editingCategory === 'theme'" class="param-edit-row">
                <a-input v-model:value="newOptionInput" placeholder="新增选项" size="small" @pressEnter="addCustomOption('theme')" />
                <a-button size="small" type="primary" @click="addCustomOption('theme')">添加</a-button>
                <div class="param-option-list">
                  <span v-for="opt in themeOptions" :key="opt" class="param-option-tag">
                    {{ opt }}
                    <button class="btn-remove-option" @click="removeCustomOption('theme', opt)">&times;</button>
                  </span>
                </div>
              </div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="作品规模">
          <a-radio-group v-model:value="wizard.params.value.target_word_count" button-style="solid">
            <a-radio-button v-for="opt in scaleOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
              <span style="font-size: 11px; opacity: 0.7; margin-left: 4px;">{{ opt.hint }}</span>
            </a-radio-button>
          </a-radio-group>
        </a-form-item>

        <a-form-item label="作者（可选）">
          <a-input v-model:value="wizard.params.value.author" placeholder="作者名" />
        </a-form-item>
      </a-form>
    </div>

    <!-- 步骤1.5：书名创意 -->
    <div v-if="wizard.currentStep.value === 1.5">
      <p class="step-desc">AI 为你生成了书名和创意，确认或编辑后继续</p>
      
      <div v-if="wizard.bookIdea.value" style="margin-top: 16px;">
        <a-card>
          <a-form layout="vertical">
            <a-form-item label="书名">
              <a-input v-model:value="wizard.bookIdea.value.name" />
            </a-form-item>
            <a-form-item label="创意描述">
              <a-textarea v-model:value="wizard.bookIdea.value.description" :rows="5" />
            </a-form-item>
          </a-form>
        </a-card>
      </div>
      
      <div v-else style="text-align: center; padding: 40px;">
        <a-spin size="large" tip="AI 正在生成创意...">
          <div style="padding: 30px;" />
        </a-spin>
      </div>
    </div>

    <!-- 步骤2：生成大纲 -->
    <div v-if="wizard.currentStep.value === 2">
      <p class="step-desc">AI 正在根据参数生成章节大纲...</p>
      <div style="text-align: center; padding: 40px;">
        <a-spin size="large" tip="AI 正在生成大纲，预计需要 1-2 分钟...">
          <div style="padding: 30px;" />
        </a-spin>
      </div>
    </div>

    <!-- 步骤2.5：确认大纲 -->
    <div v-if="wizard.currentStep.value === 2.5">
      <p class="step-desc">请确认大纲，编辑后点击确认</p>
      
      <a-form layout="vertical" style="margin-top: 16px;">
        <a-form-item label="大纲内容（Jinja2 模板格式）">
          <a-textarea v-model:value="wizard.editedOutline.value" :rows="12" />
        </a-form-item>
      </a-form>
      
      <div v-if="wizard.outline.value" style="margin-top: 8px; color: var(--text-muted);">
        <span>预估 {{ wizard.estimatedChapters }} 章 / {{ wizard.estimatedVolumes }} 卷</span>
      </div>
    </div>

    <!-- 步骤3：完成 -->
    <div v-if="wizard.currentStep.value === 3">
      <a-result
        status="success"
        title="项目创建成功！"
        :sub-title="`项目 '${createdProjectName}' 已创建，文件结构已生成。`"
      />
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: 12px;">
        <!-- 步骤1 -->
        <template v-if="wizard.currentStep.value <= 1">
          <a-button
            type="primary"
            :disabled="!wizard.params.value.genre || wizard.isGenerating.value"
            :loading="wizard.isGenerating.value"
            @click="startGenerate"
          >
            <template #icon>
              <i v-if="!wizard.isGenerating.value" class="fa-solid fa-magic"></i>
            </template>
            {{ wizard.isGenerating.value ? '生成中...' : '生成书名与创意' }}
          </a-button>
        </template>

        <!-- 步骤1.5 -->
        <template v-if="wizard.currentStep.value === 1.5">
          <a-button @click="wizard.editBookIdea()">重新生成</a-button>
          <a-button
            type="primary"
            :disabled="wizard.isGenerating.value"
            :loading="wizard.isGenerating.value"
            @click="proceedToOutline"
          >
            <template #icon>
              <i v-if="!wizard.isGenerating.value" class="fa-solid fa-magic"></i>
            </template>
            {{ wizard.isGenerating.value ? '创建项目中...' : '下一步：生成大纲' }}
          </a-button>
        </template>

        <!-- 步骤2.5 -->
        <template v-if="wizard.currentStep.value === 2.5">
          <a-button @click="wizard.editOutline()">重新生成大纲</a-button>
          <a-button
            type="primary"
            :disabled="wizard.isGenerating.value"
            :loading="wizard.isGenerating.value"
            @click="startCreateProject"
          >
            <template #icon>
              <i v-if="!wizard.isGenerating.value" class="fa-solid fa-check"></i>
            </template>
            {{ wizard.isGenerating.value ? '创建中...' : '确认并创建项目' }}
          </a-button>
        </template>

        <!-- 步骤3 -->
        <template v-if="wizard.currentStep.value === 3">
          <a-button type="primary" @click="close">开始写作</a-button>
        </template>
      </div>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import { useProjectWizard } from '@/composables/useProjectWizard'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useCustomParamsStore } from '@/stores/customParams'

const wizard = useProjectWizard()
const uiStore = useUIStore()
const projectStore = useProjectStore()
const customParamsStore = useCustomParamsStore()

// M0501-1~5 自定义参数管理
const editingCategory = ref<string | null>(null)
const newOptionInput = ref('')

function toggleEditCategory(key: string) {
  editingCategory.value = editingCategory.value === key ? null : key
  newOptionInput.value = ''
}

function addCustomOption(key: string) {
  const val = newOptionInput.value.trim()
  if (val) {
    customParamsStore.addOption(key, val)
    newOptionInput.value = ''
  }
}

function removeCustomOption(key: string, option: string) {
  customParamsStore.removeOption(key, option)
}

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

<style scoped>
.step-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 16px 0;
}

.param-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.btn-edit-param {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.btn-edit-param:hover {
  background: var(--bg-card);
  color: var(--accent-primary);
}

.param-edit-row {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.param-option-list {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.param-option-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-remove-option {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  line-height: 1;
}

.btn-remove-option:hover {
  color: var(--accent-danger);
}
</style>
