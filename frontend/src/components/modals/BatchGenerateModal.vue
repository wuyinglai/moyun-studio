<template>
  <a-modal
    :open="visible"
    title="批量生成章节"
    :width="640"
    @cancel="close"
    :footer="null"
    :destroy-on-close="true"
  >
    <div class="batch-gen-modal">
      <!-- 选择范围 -->
      <a-form layout="vertical">
        <!-- 卷选择 -->
        <a-form-item label="卷范围">
          <a-space>
            <a-select
              v-model:value="volumeNumber"
              style="width: 120px;"
              placeholder="全部卷"
              allow-clear
            >
              <a-select-option
                v-for="v in availableVolumes"
                :key="v"
                :value="v"
              >第{{ v }}卷</a-select-option>
            </a-select>
            <span class="range-hint">留空则全部卷</span>
          </a-space>
        </a-form-item>

        <!-- 章选择 -->
        <a-form-item label="章范围">
          <a-space>
            <a-select
              v-model:value="chapterNumber"
              style="width: 120px;"
              placeholder="全部章"
              allow-clear
            >
              <a-select-option
                v-for="ch in availableChapters"
                :key="ch"
                :value="ch"
              >第{{ ch }}章</a-select-option>
            </a-select>
            <span class="range-hint">留空则全部章</span>
          </a-space>
        </a-form-item>

        <!-- 节选择 -->
        <a-form-item label="节">
          <a-checkbox-group v-model:value="sectionNumbers">
            <a-checkbox value="1">第1节</a-checkbox>
            <a-checkbox value="2">第2节</a-checkbox>
            <a-checkbox value="3">第3节</a-checkbox>
            <a-checkbox value="4">第4节</a-checkbox>
          </a-checkbox-group>
          <div class="range-hint" style="margin-top: 4px;">留空则全部节</div>
        </a-form-item>
      </a-form>

      <!-- 预览 -->
      <div v-if="previewTargets >= 0" class="preview-area">
        <a-alert type="info" show-icon>
          <template #message>
            将生成 <strong>{{ previewTargets }}</strong> 个文件
            <template v-if="volumeNumber">（第{{ volumeNumber }}卷）</template>
            <template v-if="chapterNumber">（第{{ chapterNumber }}章）</template>
            <template v-if="sectionNumbers.length">（{{ sectionNumbers.map(s => '第' + s + '节').join('、') }}）</template>
          </template>
        </a-alert>
      </div>

      <!-- 操作 -->
      <div class="actions">
        <a-button @click="close">取消</a-button>
        <a-button
          type="primary"
          :loading="isGenerating"
          :disabled="previewTargets <= 0"
          @click="handleGenerate"
        >
          <template #icon><i class="fa-solid fa-wand-magic-sparkles"></i></template>
          {{ isGenerating ? '生成中...' : '开始生成' }}
        </a-button>
      </div>

      <!-- 进度 -->
      <div v-if="isGenerating" class="progress-area">
        <a-progress :percent="progressPercent" :status="progressStatus" />
        <div class="progress-text">
          已完成 {{ progressDone }} / {{ previewTargets }} 个文件
        </div>
      </div>

      <!-- 结果 -->
      <div v-if="results.length > 0" class="results-area">
        <a-table
          :data-source="results"
          :columns="resultColumns"
          :pagination="false"
          size="small"
          row-key="target_file"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="record.status === 'success' ? 'green' : 'red'">
                {{ record.status === 'success' ? '成功' : '失败' }}
              </a-tag>
            </template>
            <template v-if="column.key === 'word_count'">
              {{ record.word_count?.toLocaleString() || '-' }} 字
            </template>
          </template>
        </a-table>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useGenerationStore } from '@/stores/generation'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import { useLLMStore } from '@/stores/llm'
import type { BatchGenerateItem } from '@/types/chat'

const uiStore = useUIStore()
const projectStore = useProjectStore()
const generationStore = useGenerationStore()
const notification = useNotificationStore()
const llmStore = useLLMStore()

const visible = computed(() => uiStore.modals.batchGenerate)

const volumeNumber = ref<number | undefined>(undefined)
const chapterNumber = ref<number | undefined>(undefined)
const sectionNumbers = ref<string[]>([])
const isGenerating = ref(false)
const progressDone = ref(0)
const results = ref<BatchGenerateItem[]>([])
const previewTargets = ref(-1)

const progressPercent = computed(() => {
  if (previewTargets.value <= 0) return 0
  return Math.round((progressDone.value / previewTargets.value) * 100)
})

const progressStatus = computed(() => {
  if (results.value.some(r => r.status === 'error')) return 'exception'
  if (progressDone.value >= previewTargets.value && previewTargets.value > 0) return 'success'
  return 'active'
})

const resultColumns = [
  { title: '文件', dataIndex: 'target_file', key: 'target_file', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80 },
  { title: '字数', dataIndex: 'word_count', key: 'word_count', width: 80 },
  { title: '错误', dataIndex: 'error', key: 'error', ellipsis: true },
]

// 从文件树中扫描可用卷和章
const availableVolumes = computed(() => {
  const vols: number[] = []
  const tree = fileStore.tree || []
  for (const node of tree) {
    const m = node.name.match(/^vol-0*(\d+)$/)
    if (m) vols.push(parseInt(m[1]))
  }
  return vols.sort((a, b) => a - b)
})

const availableChapters = computed(() => {
  const chs: number[] = []
  const tree = fileStore.tree || []
  const volDir = tree.find(n => n.name === `vol-${String(volumeNumber.value).padStart(2, '0')}`)
  if (volDir?.children) {
    for (const node of volDir.children) {
      const m = node.name.match(/^ch-0*(\d+)$/)
      if (m) chs.push(parseInt(m[1]))
    }
  }
  return chs.sort((a, b) => a - b)
})

// 估算目标数
watch([volumeNumber, chapterNumber, sectionNumbers], () => {
  // 简单估算
  let n = 4 // 默认4节/章
  if (sectionNumbers.value.length > 0) n = sectionNumbers.value.length
  let chapters = 0
  if (chapterNumber.value) {
    chapters = 1
  } else if (volumeNumber.value) {
    chapters = availableChapters.value.length || 12
  } else {
    chapters = availableVolumes.value.length * 12 || 12
  }
  previewTargets.value = chapters * n
}, { immediate: true })

// 重置状态
watch(visible, (v) => {
  if (v) {
    volumeNumber.value = undefined
    chapterNumber.value = undefined
    sectionNumbers.value = []
    isGenerating.value = false
    progressDone.value = 0
    results.value = []
  }
})

async function handleGenerate() {
  if (!projectStore.currentProject) return
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    return
  }

  isGenerating.value = true
  progressDone.value = 0
  results.value = []

  try {
    const response = await generationStore.batchGenerate({
      project_id: projectStore.currentProject.id,
      volume_number: volumeNumber.value || null,
      chapter_number: chapterNumber.value || null,
      section_numbers: sectionNumbers.value.length > 0 ? sectionNumbers.value.map(s => parseInt(s)) : null,
    })

    results.value = response.tasks || []
    progressDone.value = (response.succeeded || 0) + (response.failed || 0)

    // 保存每个文件的 prompt 到 editorStore，供右侧面板展示
    if (projectStore.currentProject) {
      const prefix = projectStore.currentProject.id + '/'
      const editorStore = useEditorStore()
      for (const task of results.value) {
        if (task.prompt && task.target_file.startsWith(prefix)) {
          const filePath = task.target_file.slice(prefix.length)
          editorStore.setFilePrompt(filePath, task.prompt)
        }
      }
    }

    if (response.succeeded > 0) {
      notification.success(`成功生成 ${response.succeeded} 个文件`)
      fileStore.refreshTree()
    }
    if (response.failed > 0) {
      notification.warning(`失败 ${response.failed} 个文件`)
    }
  } catch (e) {
    notification.error('批量生成失败')
  } finally {
    isGenerating.value = false
  }
}

function close() {
  uiStore.closeBatchGenerate()
}
</script>

<style scoped lang="scss">
.batch-gen-modal {
  .range-hint {
    font-size: 12px;
    color: var(--text-muted);
  }

  .preview-area {
    margin-bottom: 16px;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-bottom: 16px;
  }

  .progress-area {
    margin-bottom: 16px;
    padding: 16px;
    background: var(--bg-card);
    border-radius: var(--radius-md);

    .progress-text {
      margin-top: 8px;
      font-size: 13px;
      color: var(--text-secondary);
      text-align: center;
    }
  }

  .results-area {
    max-height: 300px;
    overflow-y: auto;
  }
}
</style>
