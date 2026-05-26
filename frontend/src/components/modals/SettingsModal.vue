<template>
  <a-modal
    :open="visible"
    title="设置"
    :width="500"
    :confirm-loading="false"
    ok-text="保存设置"
    cancel-text="取消"
    @cancel="close"
    @ok="saveSettings"
  >
    <div class="settings-modal">
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane
          key="llm"
          tab="AI 设置"
        >
          <template #tab>
            <span><i class="fa-solid fa-brain" /> AI 设置</span>
          </template>

          <a-form layout="vertical">
            <a-form-item label="API Provider">
              <a-select
                v-model:value="config.apiType"
                placeholder="选择 API 提供商"
                data-testid="llm-provider-select"
              >
                <a-select-option value="openai">
                  OpenAI
                </a-select-option>
                <a-select-option value="deepseek">
                  DeepSeek
                </a-select-option>
                <a-select-option value="anthropic">
                  Anthropic
                </a-select-option>
                <a-select-option value="ollama">
                  Ollama (本地)
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="API Key">
              <a-input-password
                v-model:value="config.apiKey"
                placeholder="sk-..."
                :visibility-toggle="true"
              />
            </a-form-item>

            <a-form-item
              v-if="config.apiType === 'deepseek'"
              label="DeepSeek API 地址"
            >
              <a-input
                v-model:value="config.apiUrl"
                placeholder="https://api.deepseek.com"
                data-testid="llm-base-url-input"
              />
            </a-form-item>

            <a-form-item
              v-if="config.apiType === 'ollama'"
              label="Ollama 地址"
            >
              <a-input
                v-model:value="config.apiUrl"
                placeholder="http://localhost:11434"
                data-testid="llm-base-url-input"
              />
            </a-form-item>

            <a-form-item label="模型">
              <a-input
                v-model:value="config.model"
                placeholder="输入模型名称，如 gpt-4、deepseek-chat"
                style="width: 100%;"
              />
              <div
                v-if="llmStore.availableModels.length > 0"
                style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px;"
              >
                <a-tag
                  v-for="m in llmStore.availableModels"
                  :key="m"
                  style="cursor: pointer;"
                  :color="config.model === m ? 'blue' : undefined"
                  @click="selectModel(m)"
                >
                  {{ m }}
                </a-tag>
              </div>
            </a-form-item>

            <a-form-item>
              <a-checkbox v-model:checked="config.thinking">
                启用 Thinking 模式
              </a-checkbox>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px">
                让 AI 输出思考过程（仅支持部分模型）
              </div>
            </a-form-item>

            <a-divider>后端服务</a-divider>

            <a-form-item label="后端服务地址">
              <a-input
                v-model:value="backendUrl"
                placeholder="留空则使用 Vite 代理（默认）"
              />
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px; display: flex; gap: 8px; align-items: center;">
                <span>例如 http://127.0.0.1:8001</span>
                <a-button
                  size="small"
                  @click="resetBackendUrl"
                >
                  恢复默认
                </a-button>
                <a-button
                  size="small"
                  type="primary"
                  @click="applyBackendUrl"
                >
                  应用
                </a-button>
              </div>
            </a-form-item>

            <a-divider>连接测试</a-divider>

            <a-space wrap>
              <a-button
                :loading="isTesting"
                :disabled="isTesting"
                data-testid="llm-test-button"
                @click="testConnection"
              >
                <i class="fa-solid fa-plug" />
                测试连接
              </a-button>
              <a-button
                :loading="isFetchingModels"
                :disabled="isFetchingModels"
                @click="fetchModels"
              >
                <i class="fa-solid fa-list" />
                获取模型列表
              </a-button>
              <a-button
                v-if="isTesting || isFetchingModels"
                danger
                @click="cancelRequest"
              >
                <i class="fa-solid fa-stop" />
                取消
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

        <a-tab-pane
          key="automation"
          tab="自动化"
        >
          <template #tab>
            <span><i class="fa-solid fa-robot" /> 自动化</span>
          </template>

          <a-form layout="vertical">
            <a-form-item label="自动化等级">
              <div style="margin-bottom: 8px; font-size: 13px; color: var(--text-secondary);">
                控制 AI 任务的执行方式
              </div>
              <a-radio-group
                v-model:value="autoMode"
                button-style="solid"
              >
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

        <a-tab-pane
          key="theme"
          tab="外观"
        >
          <template #tab>
            <span><i class="fa-solid fa-palette" /> 外观</span>
          </template>

          <a-form layout="vertical">
            <a-form-item label="主题">
              <a-radio-group
                v-model:value="currentTheme"
                button-style="solid"
              >
                <a-radio-button
                  v-for="t in themes"
                  :key="t.id"
                  :value="t.id"
                >
                  <span style="display: flex; align-items: center; gap: 8px">
                    <div
                      class="theme-preview"
                      :style="{ background: t.preview }"
                    />
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
import { saveConfig as saveRemoteConfig } from '@/services/configService'
import { useBackendCheck } from '@/composables/useBackendCheck'

const llmStore = useLLMStore()
const uiStore = useUIStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.settings)
const activeTab = ref('llm')
const isTesting = ref(false)
const isFetchingModels = ref(false)
const testResult = ref<{ status: 'success' | 'error'; message: string } | null>(null)
let testAbortController: AbortController | null = null
let fetchAbortController: AbortController | null = null

const { customUrl, setCustomUrl, resetUrl, checkBackend } = useBackendCheck()
const backendUrl = ref(customUrl.value)

function applyBackendUrl() {
  setCustomUrl(backendUrl.value)
  notification.success('后端地址已更新，正在重新检测...')
  // 重新检测连通性
  setTimeout(() => checkBackend(), 500)
}

function resetBackendUrl() {
  backendUrl.value = ''
  resetUrl()
  notification.success('已恢复默认后端地址，正在重新检测...')
  setTimeout(() => checkBackend(), 500)
}

const config = ref({
  apiType: 'openai',
  apiKey: '',
  apiUrl: 'https://api.openai.com/v1',
  model: 'gpt-4',
  thinking: false,
} as LLMConfig)

const currentTheme = computed({
  get: () => uiStore.theme,
  set: (value) => uiStore.setTheme(value),
})
const themes = [
  { id: 'dark', name: '深邃夜紫', preview: 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)' },
  { id: 'green', name: '墨绿护眼', preview: 'linear-gradient(135deg, #1a1f1a, #242a24, #2d362d)' },
  { id: 'gray', name: '经典炭灰', preview: 'linear-gradient(135deg, #1f1f1f, #2d2d2d, #3d3d3d)' },
]

const autoMode = ref((() => {
  try {
    return localStorage.getItem('moyun-auto-mode') || 'L1'
  } catch {
    return 'L1'
  }
})())
watch(autoMode, (val) => {
  try {
    localStorage.setItem('moyun-auto-mode', val)
  } catch { /* localStorage 不可用时忽略 */ }
  // G0104 同步到后端 .config.json
  saveRemoteConfig({ autoMode: val }).catch(() => {})
})

watch(visible, (val) => {
  if (val) {
    config.value = { ...llmStore.config }
    testResult.value = null
    try {
      autoMode.value = localStorage.getItem('moyun-auto-mode') || 'L1'
    } catch {
      autoMode.value = 'L1'
    }
    backendUrl.value = customUrl.value
  } else {
    // 关闭弹窗时取消所有进行中的请求
    cancelRequest(true)
  }
})

function selectModel(model: string) {
  config.value.model = model
}

function cancelRequest(silent = false) {
  if (testAbortController) {
    testAbortController.abort()
    testAbortController = null
  }
  if (fetchAbortController) {
    fetchAbortController.abort()
    fetchAbortController = null
  }
  isTesting.value = false
  isFetchingModels.value = false
  if (!silent) {
    notification.info('已取消请求')
  }
}

async function fetchModels() {
  if (isFetchingModels.value) return
  isFetchingModels.value = true
  fetchAbortController = new AbortController()
  try {
    await llmStore.saveConfig(config.value)
    await llmStore.fetchModels(fetchAbortController.signal)
    if (!fetchAbortController.signal.aborted) {
      notification.success(`已获取 ${llmStore.availableModels.length} 个可用模型`)
    }
  } catch {
    if (!fetchAbortController?.signal.aborted) {
      notification.error('获取模型列表失败')
    }
  } finally {
    if (fetchAbortController) {
      isFetchingModels.value = false
      fetchAbortController = null
    }
  }
}

async function testConnection() {
  if (isTesting.value) return
  isTesting.value = true
  testResult.value = null
  testAbortController = new AbortController()

  try {
    await llmStore.saveConfig(config.value)
    const success = await llmStore.testConnection(testAbortController.signal)

    if (!testAbortController.signal.aborted) {
      if (success) {
        testResult.value = { status: 'success', message: '连接成功！' }
      } else {
        testResult.value = { status: 'error', message: '连接失败，请检查配置' }
      }
    }
  } catch (e: unknown) {
    if (!testAbortController?.signal.aborted) {
      testResult.value = { status: 'error', message: (e instanceof Error ? e.message : '') || '连接失败' }
    }
  } finally {
    if (testAbortController) {
      isTesting.value = false
      testAbortController = null
    }
  }
}

async function saveSettings() {
  try {
    await llmStore.saveConfig(config.value)
    notification.success('设置已保存')
    close()
  } catch {
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
