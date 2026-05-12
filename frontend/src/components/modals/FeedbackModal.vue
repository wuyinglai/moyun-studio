<template>
  <a-modal
    :open="visible"
    title="用户反馈管理"
    :width="700"
    @cancel="close"
    :footer="null"
  >
    <div class="feedback-modal">
      <!-- 新建反馈 -->
      <a-collapse ghost>
        <a-collapse-panel key="new" header="提交新反馈">
          <a-form layout="inline" class="feedback-form">
            <a-form-item label="类型">
              <a-select v-model:value="newFeedback.type" style="width: 140px;">
                <a-select-option value="suggestion">建议</a-select-option>
                <a-select-option value="error">错误</a-select-option>
                <a-select-option value="improvement">改进</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="满意度">
              <a-select v-model:value="newFeedback.satisfaction" style="width: 100px;" allow-clear>
                <a-select-option value="满意">满意</a-select-option>
                <a-select-option value="一般">一般</a-select-option>
                <a-select-option value="不满意">不满意</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="位置">
              <a-input v-model:value="newFeedback.location" placeholder="章节路径" style="width: 200px;" />
            </a-form-item>
            <a-form-item label="内容" style="width: 100%;">
              <a-textarea v-model:value="newFeedback.content" placeholder="反馈内容" :rows="2" />
            </a-form-item>
            <a-button type="primary" @click="submitFeedback" :disabled="!newFeedback.content" size="small">
              <template #icon><i class="fa-solid fa-paper-plane"></i></template>
              提交
            </a-button>
          </a-form>
        </a-collapse-panel>
      </a-collapse>

      <!-- 反馈列表 -->
      <a-spin :spinning="isLoading">
        <a-empty v-if="feedbacks.length === 0" description="暂无反馈" style="margin-top: 24px;" />
        <a-list v-else :data-source="feedbacks" item-layout="horizontal" style="margin-top: 16px;">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <a-tag :color="typeColor(item.type)">{{ typeLabel(item.type) }}</a-tag>
                  <span :class="{ 'resolved-text': item.resolved }">{{ item.content }}</span>
                </template>
                <template #description>
                  <div class="feedback-meta">
                    <span v-if="item.location">位置: {{ item.location }}</span>
                    <span v-if="item.satisfaction_level">满意度: {{ item.satisfaction_level }}</span>
                    <span>{{ formatTime(item.created_at) }}</span>
                  </div>
                </template>
              </a-list-item-meta>
              <template #actions>
                <a-button
                  v-if="!item.resolved"
                  size="small"
                  type="primary"
                  ghost
                  @click="resolveFeedback(item.id)"
                >
                  标记已解决
                </a-button>
                <a-tag v-else color="green">已解决</a-tag>
              </template>
            </a-list-item>
          </template>
        </a-list>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'

const uiStore = useUIStore()
const projectStore = useProjectStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.feedback)

interface Feedback {
  id: string
  chapter_path: string
  type: string
  content: string
  location?: string
  satisfaction_level?: string
  resolved: boolean
  created_at: string
}

const feedbacks = ref<Feedback[]>([])
const isLoading = ref(false)
const newFeedback = ref({ type: 'suggestion', satisfaction: '', location: '', content: '' })

watch(visible, async (val) => {
  if (val) {
    await loadFeedbacks()
  }
})

async function loadFeedbacks() {
  if (!projectStore.currentProject) return
  isLoading.value = true
  try {
    feedbacks.value = await api.get<Feedback[]>(`/feedback/${projectStore.currentProject.id}`)
  } catch {
    feedbacks.value = []
  } finally {
    isLoading.value = false
  }
}

async function submitFeedback() {
  if (!projectStore.currentProject || !newFeedback.value.content) return
  try {
    await api.post(`/feedback/${projectStore.currentProject.id}`, {
      chapter_path: newFeedback.value.location || '',
      type: newFeedback.value.type,
      content: newFeedback.value.content,
      location: newFeedback.value.location,
      satisfaction_level: newFeedback.value.satisfaction || null,
    })
    notification.success('反馈已提交')
    newFeedback.value = { type: 'suggestion', satisfaction: '', location: '', content: '' }
    await loadFeedbacks()
  } catch {
    notification.error('提交反馈失败')
  }
}

async function resolveFeedback(feedbackId: string) {
  if (!projectStore.currentProject) return
  try {
    await api.patch(`/feedback/${projectStore.currentProject.id}/${feedbackId}`, {
      resolved: true,
    })
    notification.success('反馈已标记为已解决')
    await loadFeedbacks()
  } catch {
    notification.error('操作失败')
  }
}

function typeColor(type: string): string {
  switch (type) {
    case 'error': return 'red'
    case 'suggestion': return 'blue'
    case 'improvement': return 'orange'
    default: return 'default'
  }
}

function typeLabel(type: string): string {
  switch (type) {
    case 'error': return '错误'
    case 'suggestion': return '建议'
    case 'improvement': return '改进'
    default: return type
  }
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
  uiStore.closeFeedback()
}
</script>

<style scoped lang="scss">
.feedback-modal {
  .feedback-form {
    width: 100%;
  }

  .feedback-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .resolved-text {
    text-decoration: line-through;
    opacity: 0.6;
  }
}
</style>
