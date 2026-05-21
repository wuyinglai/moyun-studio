<template>
  <a-modal
    :open="visible"
    title="智能提取"
    :width="580"
    :footer="null"
    :destroy-on-close="true"
    @cancel="close"
  >
    <div class="extract-modal">
      <a-form layout="vertical">
        <a-form-item label="源文件">
          <a-input
            v-model:value="sourceFile"
            placeholder="选择当前编辑的文件或手动输入路径"
            :disabled="!!currentFilePath"
          >
            <template #addonAfter>
              <a-tooltip title="使用当前文件">
                <i
                  class="fa-solid fa-file"
                  style="cursor: pointer;"
                  @click="useCurrentFile"
                />
              </a-tooltip>
            </template>
          </a-input>
        </a-form-item>

        <a-form-item label="提取类型">
          <a-select
            v-model:value="extractType"
            style="width: 200px;"
          >
            <a-select-option value="character">
              角色
            </a-select-option>
            <a-select-option value="plot">
              情节
            </a-select-option>
            <a-select-option value="scene">
              场景
            </a-select-option>
            <a-select-option value="summary">
              摘要
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>

      <div class="actions">
        <a-button @click="close">
          取消
        </a-button>
        <a-button
          type="primary"
          :loading="isExtracting"
          :disabled="!sourceFile"
          @click="handleExtract"
        >
          <template #icon>
            <i class="fa-solid fa-brain" />
          </template>
          {{ isExtracting ? '提取中...' : '开始提取' }}
        </a-button>
      </div>

      <!-- 结果 -->
      <div
        v-if="result"
        class="result-area"
      >
        <a-divider />
        <a-alert
          type="success"
          show-icon
        >
          <template #message>
            <strong>{{ result.title }}</strong>
          </template>
          <template #description>
            <div class="result-meta">
              <span>类型: {{ typeLabel(result.type) }}</span>
              <span>源文件: {{ result.source_file }}</span>
              <span>{{ formatTime(result.created_at) }}</span>
            </div>
            <div class="result-content">
              {{ result.content }}
            </div>
          </template>
        </a-alert>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { useGenerationStore } from '@/stores/generation'
import { useNotificationStore } from '@/stores/notification'
import { useLLMStore } from '@/stores/llm'
import type { ExtractTaskRequest, ExtractTaskResponse } from '@/types/chat'

const uiStore = useUIStore()
const editorStore = useEditorStore()
const projectStore = useProjectStore()
const generationStore = useGenerationStore()
const notification = useNotificationStore()
const llmStore = useLLMStore()

const visible = computed(() => uiStore.modals.extract)

const sourceFile = ref('')
const extractType = ref<string>('character')
const isExtracting = ref(false)
const result = ref<ExtractTaskResponse | null>(null)

const currentFilePath = computed(() => editorStore.currentFilePath)

watch(visible, (v) => {
  if (v) {
    sourceFile.value = currentFilePath.value || ''
    extractType.value = 'character'
    isExtracting.value = false
    result.value = null
  }
})

function useCurrentFile() {
  if (currentFilePath.value) {
    sourceFile.value = currentFilePath.value
  }
}

async function handleExtract() {
  if (!projectStore.currentProject || !sourceFile.value) return
  if (!llmStore.isConnected) {
    notification.warning('请先配置 LLM 连接')
    return
  }

  isExtracting.value = true
  result.value = null

  try {
    const res = await generationStore.extractTask({
      project_id: projectStore.currentProject.id,
      type: extractType.value as ExtractTaskRequest['type'],
      source_file: sourceFile.value,
    })
    result.value = res
    notification.success('提取完成')
  } catch (e: unknown) {
    notification.error(`提取失败: ${e instanceof Error ? e.message : '未知错误'}`)
  } finally {
    isExtracting.value = false
  }
}

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    character: '角色',
    plot: '情节',
    scene: '场景',
    summary: '摘要',
  }
  return map[type] || type
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function close() {
  uiStore.closeExtract()
}
</script>

<style scoped lang="scss">
.extract-modal {
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
  }

  .result-area {
    margin-top: 16px;

    .result-meta {
      display: flex;
      gap: 12px;
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 8px;
    }

    .result-content {
      margin-top: 8px;
      padding: 12px;
      background: var(--bg-card);
      border-radius: var(--radius-md);
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      max-height: 300px;
      overflow-y: auto;
    }
  }
}
</style>
