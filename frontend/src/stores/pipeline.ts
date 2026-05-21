import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'
import type { PipelineDef, PipelineStepDetail, PipelineDetail as ApiPipelineDetail } from '@/shared/api/types'

/** UI-only: 管线步骤精简信息 */
export interface PipelineStepInfo {
  id: string
  label: string
}

/** UI-only: 管线列表项（含 source 字段） */
export interface PipelineInfo extends PipelineDef {
  source: 'system' | 'custom'
}

export type StepDetail = PipelineStepDetail

export type PipelineDetail = ApiPipelineDetail

export const usePipelineStore = defineStore('pipeline', () => {
  const pipelines = ref<PipelineInfo[]>([])
  const currentPipelineName = ref<string>('polish')
  const currentStepIndex = ref(0)
  const currentDetail = ref<PipelineDetail | null>(null)

  const currentPipeline = computed(() =>
    pipelines.value.find(p => p.name === currentPipelineName.value)
  )

  const currentStep = computed(() => {
    if (!currentDetail.value) return null
    return currentDetail.value.steps[currentStepIndex.value] || null
  })

  const currentPromptContent = computed(() => {
    return currentStep.value?.prompt_content || ''
  })

  async function fetchPipelines() {
    try {
      const data = await api.get<{ pipelines: PipelineInfo[]; total: number }>('/pipeline/list')
      if (data?.pipelines) {
        pipelines.value = data.pipelines
      }
    } catch (e) {
      console.warn('获取管线列表失败:', e)
    }
  }

  async function fetchPipelineDetail(name: string) {
    try {
      const data = await api.get<{ pipeline: PipelineDetail }>(API_ROUTES.pipelineDetail(name))
      if (data?.pipeline) {
        currentDetail.value = data.pipeline
      }
    } catch (e) {
      console.warn('获取管线详情失败:', e)
    }
  }

  async function selectPipeline(name: string) {
    currentPipelineName.value = name
    currentStepIndex.value = 0
    await fetchPipelineDetail(name)
  }

  function selectStep(index: number) {
    if (currentDetail.value && index >= 0 && index < currentDetail.value.steps.length) {
      currentStepIndex.value = index
    }
  }

  async function saveStepPrompt(stepId: string, content: string) {
    if (!currentDetail.value) return
    try {
      await api.put(API_ROUTES.pipelineDetail(currentPipelineName.value), {
        name: currentPipelineName.value,
        steps: [{ id: stepId, prompt_content: content }],
      })
      const step = currentDetail.value.steps.find(s => s.id === stepId)
      if (step) step.prompt_content = content
    } catch (e) {
      console.warn('保存 prompt 失败:', e)
    }
  }

  async function createCustomPipeline(
    name: string,
    label: string,
    steps: { id: string; label: string; prompt_content: string }[]
  ) {
    try {
      await api.post(API_ROUTES.pipelineCustom, { name, label, steps })
      await fetchPipelines()
    } catch (e) {
      console.warn('创建管线失败:', e)
      throw e
    }
  }

  return {
    pipelines,
    currentPipelineName,
    currentStepIndex,
    currentDetail,
    currentPipeline,
    currentStep,
    currentPromptContent,
    fetchPipelines,
    fetchPipelineDetail,
    selectPipeline,
    selectStep,
    saveStepPrompt,
    createCustomPipeline,
  }
})
