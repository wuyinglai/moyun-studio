<template>
  <a-modal
    :open="visible"
    title="新建项目"
    :width="700"
    :closable="true"
    @cancel="close"
  >
    <template #title>
      <span style="display: flex; align-items: center; gap: 10px;">
        <i class="fa-solid fa-feather-pointed" style="color: var(--accent-primary);"></i>
        新建项目
      </span>
    </template>

    <p class="step-desc">选择创作参数，AI 将为你生成小说</p>

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

    <template #footer>
      <a-button
        type="primary"
        :disabled="!wizard.params.value.genre || wizard.isGenerating.value || creatingFile"
        :loading="wizard.isGenerating.value || creatingFile"
        @click="handleCreate"
      >
        <template #icon>
          <i v-if="!wizard.isGenerating.value" class="fa-solid fa-magic"></i>
        </template>
        {{ wizard.isGenerating.value ? '创建中...' : '生成并打开' }}
      </a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectWizard } from '@/composables/useProjectWizard'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useCustomParamsStore } from '@/stores/customParams'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const wizard = useProjectWizard()
const uiStore = useUIStore()
const projectStore = useProjectStore()
const fileStore = useFileStore()
const customParamsStore = useCustomParamsStore()
const notification = useNotificationStore()

// M0501-1~5 自定义参数管理
const editingCategory = ref<string | null>(null)
const newOptionInput = ref('')
const creatingFile = ref(false)

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

async function handleCreate() {
  creatingFile.value = true
  try {
    const project = await wizard.createProject(wizard.params.value)
    if (!project) return

    try {
      // 创建书名与创意文件
      await fileStore.createFile(project.id, '书名与创意.md', '')
    } catch {
      notification.error('项目已创建，但初始化文件失败')
      close()
      router.push(`/project/${project.id}`)
      return
    }

    // 记录需要在项目打开后自动生成
    projectStore.setPendingGeneration({
      filePath: '书名与创意.md',
      prompt: `你是一位专业的小说创作助手。用户选择了「${wizard.params.value.genre}」题材，请生成一个吸引人的书名和创意描述。`,
      promptType: 'generate/title',
      extraVars: {
        genre: wizard.params.value.genre || '',
        tone: wizard.params.value.tone || '',
        theme: wizard.params.value.theme || '',
        background: wizard.params.value.background || '',
        writing_style: wizard.params.value.writing_style || '',
      },
    })

    // 关闭弹窗
    close()

    // 跳转到编辑器
    router.push(`/project/${project.id}`)
  } catch (e: any) {
    notification.error(e.message || '创建项目失败')
  } finally {
    creatingFile.value = false
  }
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
