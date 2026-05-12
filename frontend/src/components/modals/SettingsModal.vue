<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal">
          <!-- 头部 -->
          <div class="modal-header">
            <h3 class="modal-title">
              <i class="fa-solid fa-gear"></i>
              设置
            </h3>
            <button class="modal-close" @click="close">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>

          <!-- Tab 切换 -->
          <div class="modal-tabs">
            <button
              class="modal-tab"
              :class="{ active: activeTab === 'llm' }"
              @click="activeTab = 'llm'"
            >
              <i class="fa-solid fa-brain"></i>
              AI 设置
            </button>
            <button
              class="modal-tab"
              :class="{ active: activeTab === 'theme' }"
              @click="activeTab = 'theme'"
            >
              <i class="fa-solid fa-palette"></i>
              外观
            </button>
          </div>

          <!-- 内容 -->
          <div class="modal-body">
            <!-- LLM 设置 -->
            <div v-if="activeTab === 'llm'" class="settings-section">
              <div class="form-group">
                <label class="form-label">API Provider</label>
                <select v-model="config.apiType" class="form-input">
                  <option value="openai">OpenAI</option>
                  <option value="deepseek">DeepSeek</option>
                  <option value="azure">Azure OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama (本地)</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">API Key</label>
                <div class="input-with-toggle">
                  <input
                    v-model="config.apiKey"
                    :type="showApiKey ? 'text' : 'password'"
                    class="form-input"
                    placeholder="sk-..."
                  />
                  <button class="btn-toggle" @click="showApiKey = !showApiKey">
                    <i :class="showApiKey ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
                  </button>
                </div>
              </div>

              <!-- DeepSeek 配置 -->
              <div v-if="config.apiType === 'deepseek'" class="form-group">
                <label class="form-label">DeepSeek API 地址</label>
                <input
                  v-model="config.apiUrl"
                  type="text"
                  class="form-input"
                  placeholder="https://api.deepseek.com"
                />
              </div>
              <!-- Ollama 配置 -->
              <div v-if="config.apiType === 'ollama'" class="form-group">
                <label class="form-label">Ollama 地址</label>
                <input
                  v-model="config.apiUrl"
                  type="text"
                  class="form-input"
                  placeholder="http://localhost:11434"
                />
              </div>

              <div class="form-group">
                <label class="form-label">模型</label>
                <input
                  v-model="config.model"
                  type="text"
                  class="form-input"
                  placeholder="gpt-4, claude-3-opus, llama3..."
                />
                <span class="form-hint">常用模型：gpt-4, gpt-3.5-turbo, claude-3-opus, claude-3-sonnet</span>
              </div>

              <div class="form-group">
                <label class="form-label">
                  <input type="checkbox" v-model="config.thinking" />
                  启用 Thinking 模式
                </label>
                <span class="form-hint">让 AI 输出思考过程（仅支持部分模型）</span>
              </div>

              <!-- 连接测试 -->
              <div class="connection-test">
                <button
                  class="btn btn-secondary"
                  @click="testConnection"
                  :disabled="isTesting"
                >
                  <i v-if="isTesting" class="fa-solid fa-spinner fa-spin"></i>
                  <i v-else class="fa-solid fa-plug"></i>
                  {{ isTesting ? '测试中...' : '测试连接' }}
                </button>
                <span v-if="testResult" class="test-result" :class="testResult.status">
                  {{ testResult.message }}
                </span>
              </div>
            </div>

            <!-- 主题设置 -->
            <div v-if="activeTab === 'theme'" class="settings-section">
              <div class="form-group">
                <label class="form-label">主题</label>
                <div class="theme-options">
                  <button
                    v-for="t in themes"
                    :key="t.id"
                    class="theme-option"
                    :class="{ active: currentTheme === t.id }"
                    @click="setTheme(t.id)"
                  >
                    <div class="theme-preview" :style="{ background: t.preview }"></div>
                    <span>{{ t.name }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部 -->
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="close">取消</button>
            <button class="btn btn-primary" @click="saveSettings">
              <i class="fa-solid fa-check"></i>
              保存
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useLLMStore } from '@/stores/llm'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notification'

const llmStore = useLLMStore()
const uiStore = useUIStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.settings)
const activeTab = ref<'llm' | 'theme'>('llm')
const showApiKey = ref(false)
const isTesting = ref(false)
const testResult = ref<{ status: 'success' | 'error'; message: string } | null>(null)

const config = ref({
  apiType: 'openai' as const,
  apiKey: '',
  apiUrl: 'https://api.openai.com/v1',
  model: 'gpt-4',
  thinking: false,
})

const currentTheme = computed(() => uiStore.theme)
const themes = [
  { id: 'dark', name: '深邃夜紫', preview: 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)' },
  { id: 'green', name: '墨绿护眼', preview: 'linear-gradient(135deg, #1a1f1a, #242a24, #2d362d)' },
  { id: 'gray', name: '经典炭灰', preview: 'linear-gradient(135deg, #1f1f1f, #2d2d2d, #3d3d3d)' },
]

// 加载当前配置
watch(visible, (val) => {
  if (val) {
    config.value = { ...llmStore.config }
    testResult.value = null
  }
})

async function testConnection() {
  isTesting.value = true
  testResult.value = null

  try {
    await llmStore.saveConfig(config.value as typeof llmStore.config)
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

function setTheme(theme: string) {
  uiStore.setTheme(theme as 'dark' | 'green' | 'gray')
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
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
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

  i {
    color: var(--accent-primary);
  }
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

  &:hover {
    background: var(--bg-card);
    color: var(--text-primary);
  }
}

.modal-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.modal-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;

  &:hover {
    color: var(--text-primary);
  }

  &.active {
    color: var(--accent-primary);
    border-bottom-color: var(--accent-primary);
  }
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent-primary);
  }
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

  &::placeholder {
    color: var(--text-muted);
  }

  &:focus {
    border-color: var(--accent-primary);
  }
}

.input-with-toggle {
  position: relative;
  display: flex;

  .form-input {
    padding-right: 40px;
  }

  .btn-toggle {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;

    &:hover {
      color: var(--text-primary);
    }
  }
}

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.connection-test {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
}

.test-result {
  font-size: 13px;

  &.success {
    color: var(--accent-success);
  }

  &.error {
    color: var(--accent-danger);
  }
}

.theme-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--border-color);
  }

  &.active {
    border-color: var(--accent-primary);
  }

  span {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.theme-preview {
  width: 100%;
  height: 40px;
  border-radius: var(--radius-sm);
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

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &-primary {
    background: var(--accent-primary);
    color: white;

    &:hover:not(:disabled) {
      filter: brightness(1.1);
    }
  }

  &-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);

    &:hover:not(:disabled) {
      border-color: var(--accent-primary);
    }
  }
}

// 过渡动画
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;

  .modal {
    transition: transform 0.2s ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .modal {
    transform: scale(0.95);
  }
}
</style>
