<template>
  <a-modal
    :open="visible"
    title="版本对比"
    :width="800"
    @cancel="close"
    :footer="null"
  >
    <div class="compare-modal">
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="旧版本">
              <a-textarea
                v-model:value="oldText"
                :rows="8"
                placeholder="输入旧版本内容"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="新版本">
              <a-textarea
                v-model:value="newText"
                :rows="8"
                placeholder="输入新版本内容"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <div class="compare-actions">
          <a-button @click="loadCurrentVersion">加载当前编辑器内容</a-button>
          <a-button type="primary" @click="compare" :loading="isComparing">
            <template #icon><i class="fa-solid fa-code-compare"></i></template>
            对比
          </a-button>
        </div>
      </a-form>

      <div v-if="diffResult" class="diff-result">
        <a-divider>差异结果</a-divider>
        <div class="diff-stats">
          <span class="stat-added">+{{ diffResult.added_lines }} 行</span>
          <span class="stat-removed">-{{ diffResult.removed_lines }} 行</span>
        </div>
        <pre class="diff-content" v-text="diffResult.diff"></pre>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useEditorStore } from '@/stores/editor'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

const uiStore = useUIStore()
const editorStore = useEditorStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.compare)
const oldText = ref('')
const newText = ref('')
const isComparing = ref(false)

interface CompareResult {
  diff: string
  has_diff: boolean
  added_lines: number
  removed_lines: number
}

const diffResult = ref<CompareResult | null>(null)

function loadCurrentVersion() {
  const path = editorStore.currentFilePath
  if (!path) {
    notification.warning('没有打开的文件')
    return
  }
  newText.value = editorStore.getContent(path)
  notification.success('已加载当前编辑器内容')
}

async function compare() {
  if (!oldText.value && !newText.value) {
    notification.warning('请填写至少一个版本的内容')
    return
  }
  isComparing.value = true
  diffResult.value = null
  try {
    diffResult.value = await api.post<CompareResult>('/compare', {
      old_text: oldText.value,
      new_text: newText.value,
    })
  } catch {
    notification.error('对比失败')
  } finally {
    isComparing.value = false
  }
}

function close() {
  uiStore.closeCompare()
  oldText.value = ''
  newText.value = ''
  diffResult.value = null
}
</script>

<style scoped lang="scss">
.compare-modal {
  .compare-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }

  .diff-result {
    margin-top: 16px;
  }

  .diff-stats {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
  }

  .stat-added {
    color: var(--accent-success);
    font-weight: 600;
    font-size: 14px;
  }

  .stat-removed {
    color: var(--accent-danger);
    font-weight: 600;
    font-size: 14px;
  }

  .diff-content {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 16px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    line-height: 1.6;
    max-height: 400px;
    overflow: auto;
    white-space: pre;
    color: var(--text-primary);
  }
}
</style>
