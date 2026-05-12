<template>
  <a-modal
    :open="visible"
    title="Token 计数"
    :width="500"
    @cancel="close"
    :footer="null"
  >
    <div class="token-count-modal">
      <a-form layout="vertical">
        <a-form-item label="计数来源">
          <a-radio-group v-model:value="source" button-style="solid">
            <a-radio-button value="editor">当前编辑器内容</a-radio-button>
            <a-radio-button value="prompt">当前 Prompt 内容</a-radio-button>
          </a-radio-group>
        </a-form-item>

        <a-form-item label="模型">
          <a-select v-model:value="model" style="width: 100%;" placeholder="选择模型">
            <a-select-option v-for="m in llmStore.availableModels" :key="m" :value="m">
              {{ m }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-button type="primary" @click="countTokens" :loading="isCounting" :disabled="!model">
          <template #icon><i class="fa-solid fa-calculator"></i></template>
          计算 Token
        </a-button>
      </a-form>

      <div v-if="result" class="token-result">
        <a-divider>计数结果</a-divider>
        <div class="result-grid">
          <div class="result-item">
            <span class="result-label">Token 数</span>
            <span class="result-value">{{ result.tokens.toLocaleString() }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">模型</span>
            <span class="result-value">{{ result.model }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">最大上下文</span>
            <span class="result-value">{{ result.max_context.toLocaleString() }}</span>
          </div>
          <div class="result-item" :class="{ warning: result.remaining < 1000, danger: result.remaining < 100 }">
            <span class="result-label">剩余 Token</span>
            <span class="result-value">{{ result.remaining.toLocaleString() }}</span>
          </div>
        </div>
        <a-progress
          v-if="result.max_context > 0"
          :percent="Math.round((result.tokens / result.max_context) * 100)"
          :status="result.remaining < 100 ? 'exception' : result.remaining < 1000 ? 'active' : 'success'"
          :show-info="true"
        />
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useLLMStore } from '@/stores/llm'
import { useEditorStore } from '@/stores/editor'
import { useRightPanelStore } from '@/stores/rightPanel'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

const uiStore = useUIStore()
const llmStore = useLLMStore()
const editorStore = useEditorStore()
const rightPanelStore = useRightPanelStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.tokenCount)
const source = ref<'editor' | 'prompt'>('editor')
const model = ref(llmStore.config.model || '')
const isCounting = ref(false)

interface TokenResult {
  tokens: number
  model: string
  max_context: number
  remaining: number
}

const result = ref<TokenResult | null>(null)

async function countTokens() {
  if (!model.value) {
    notification.warning('请选择模型')
    return
  }

  const text = source.value === 'editor'
    ? editorStore.getContent(editorStore.currentFilePath || '')
    : rightPanelStore.promptContent

  if (!text) {
    notification.warning(source.value === 'editor' ? '编辑器内容为空' : 'Prompt 内容为空')
    return
  }

  isCounting.value = true
  result.value = null
  try {
    result.value = await api.post<TokenResult>('/tokens/count', {
      text,
      model: model.value,
    })
  } catch {
    notification.error('Token 计数失败')
  } finally {
    isCounting.value = false
  }
}

function close() {
  uiStore.closeTokenCount()
  result.value = null
}
</script>

<style scoped lang="scss">
.token-count-modal {
  .token-result {
    margin-top: 16px;
  }

  .result-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .result-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px;
    background: var(--bg-card);
    border-radius: var(--radius-md);
  }

  .result-label {
    font-size: 12px;
    color: var(--text-muted);
  }

  .result-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .result-item.warning .result-value {
    color: var(--accent-warning);
  }

  .result-item.danger .result-value {
    color: var(--accent-danger);
  }
}
</style>
