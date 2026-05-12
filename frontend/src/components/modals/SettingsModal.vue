<template>
  <a-modal
    :open="visible"
    title="设置"
    :width="500"
    @cancel="close"
    @ok="saveSettings"
    :confirm-loading="isTesting"
  >
    <div class="settings-modal">
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="llm" tab="AI 设置">
          <template #tab>
            <span><i class="fa-solid fa-brain"></i> AI 设置</span>
          </template>

          <a-form layout="vertical">
            <a-form-item label="API Provider">
              <a-select v-model:value="config.apiType" placeholder="选择 API 提供商">
                <a-select-option value="openai">OpenAI</a-select-option>
                <a-select-option value="deepseek">DeepSeek</a-select-option>
                <a-select-option value="azure">Azure OpenAI</a-select-option>
                <a-select-option value="anthropic">Anthropic</a-select-option>
                <a-select-option value="ollama">Ollama (本地)</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="API Key">
              <a-input-password
                v-model:value="config.apiKey"
                placeholder="sk-..."
                :visibility-toggle="true"
              />
            </a-form-item>

            <a-form-item v-if="config.apiType === 'deepseek'" label="DeepSeek API 地址">
              <a-input v-model:value="config.apiUrl" placeholder="https://api.deepseek.com" />
            </a-form-item>

            <a-form-item v-if="config.apiType === 'ollama'" label="Ollama 地址">
              <a-input v-model:value="config.apiUrl" placeholder="http://localhost:11434" />
            </a-form-item>

            <a-form-item label="模型">
              <a-select
                v-model:value="config.model"
                style="width: 100%;"
                placeholder="输入或选择模型名称"
                show-search
                :allow-clear="true"
              >
                <a-select-option
                  v-for="m in llmStore.availableModels"
                  :key="m"
                  :value="m"
                >{{ m }}</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item>
              <a-checkbox v-model:checked="config.thinking">
                启用 Thinking 模式
              </a-checkbox>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px">
                让 AI 输出思考过程（仅支持部分模型）
              </div>
            </a-form-item>

            <a-divider>连接测试</a-divider>

            <a-space>
              <a-button @click="testConnection" :loading="isTesting">
                <i class="fa-solid fa-plug"></i>
                测试连接
              </a-button>
              <a-button @click="fetchModels" :loading="isFetchingModels">
                <i class="fa-solid fa-list"></i>
                获取模型列表
              </a-button>
              <a-alert
                v-if="testResult"
                :type="testResult.status"
                :message="testResult.message"
                show-icon
              />
            </a-space>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="automation" tab="自动化">
          <template #tab>
            <span><i class="fa-solid fa-robot"></i> 自动化</span>
          </template>

          <a-form layout="vertical">
            <a-form-item label="自动化等级">
              <div style="margin-bottom: 8px; font-size: 13px; color: var(--text-secondary);">
                控制 AI 任务的执行方式
              </div>
              <a-radio-group v-model:value="autoMode" button-style="solid">
                <a-radio-button value="L1">
                  <div style="display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 4px 8px;">
                    <strong>L1 半自动</strong>
                    <span style="font-size: 12px; opacity: 0.7;">每步需确认</span>
                  </div>
                </a-radio-button>
                <a-radio-button value="L2">
                  <div style="display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 4px 8px;">
                    <strong>L2 连续</strong>
                    <span style="font-size: 12px; opacity: 0.7;">自动连续执行</span>
                  </div>
                </a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="theme" tab="外观">
          <template #tab>
            <span><i class="fa-solid fa-palette"></i> 外观</span>
          </template>

          <a-form layout="vertical">
            <a-form-item label="主题">
              <a-radio-group v-model:value="currentTheme" button-style="solid">
                <a-radio-button v-for="t in themes" :key="t.id" :value="t.id">
                  <span style="display: flex; align-items: center; gap: 8px">
                    <div
                      class="theme-preview"
                      :style="{ background: t.preview }"
                    ></div>
                    {{ t.name }}
                  </span>
                </a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useLLMStore } from '@/stores/llm'
import type { LLMConfig } from '@/stores/llm'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notification'

const llmStore = useLLMStore()
const uiStore = useUIStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.settings)
const activeTab = ref('llm')
const isTesting = ref(false)
const isFetchingModels = ref(false)
const testResult = ref<{ status: 'success' | 'error'; message: string } | null>(null)

const config = ref({
  apiType: 'openai',
  apiKey: '',
  apiUrl: 'https://api.openai.com/v1',
  model: 'gpt-4',
  thinking: false,
} as LLMConfig)

const currentTheme = computed(() => uiStore.theme)
const themes = [
  { id: 'dark', name: '深邃夜紫', preview: 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)' },
  { id: 'green', name: '墨绿护眼', preview: 'linear-gradient(135deg, #1a1f1a, #242a24, #2d362d)' },
  { id: 'gray', name: '经典炭灰', preview: 'linear-gradient(135deg, #1f1f1f, #2d2d2d, #3d3d3d)' },
]

const autoMode = ref(localStorage.getItem('moyun-auto-mode') || 'L1')
watch(autoMode, (val) => {
  localStorage.setItem('moyun-auto-mode', val)
})

watch(visible, (val) => {
  if (val) {
    config.value = { ...llmStore.config }
    testResult.value = null
    autoMode.value = localStorage.getItem('moyun-auto-mode') || 'L1'
  }
})

async function fetchModels() {
  isFetchingModels.value = true
  try {
    await llmStore.saveConfig(config.value)
    await llmStore.fetchModels()
    notification.success(`已获取 ${llmStore.availableModels.length} 个可用模型`)
  } catch {
    notification.error('获取模型列表失败')
  } finally {
    isFetchingModels.value = false
  }
}

async function testConnection() {
  isTesting.value = true
  testResult.value = null

  try {
    await llmStore.saveConfig(config.value)
    const success = await llmStore.testConnection()

    if (success) {
      testResult.value = { status: 'success', message: '连接成功！' }
    } else {
      testResult.value = { status: 'error', message: '连接失败，请检查配置' }
    }
  } catch (e: any) {
    testResult.value = { status: 'error', message: e.message || '连接失败' }
  } finally {
    isTesting.value = false
  }
}

async function saveSettings() {
  try {
    await llmStore.saveConfig(config.value)
    notification.success('设置已保存')
    close()
  } catch (e) {
    notification.error('保存失败')
  }
}

function close() {
  uiStore.closeSettings()
}
</script>

<style scoped lang="scss">
.settings-modal {
  .theme-preview {
    width: 24px;
    height: 18px;
    border-radius: 2px;
  }
}
</style>
