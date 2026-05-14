import { ref, readonly } from 'vue'
import api from '@/services/api'

export interface WorkflowStep {
  id: string
  label: string
  type: string
  pipeline?: string
  count?: string
  var?: string
  action?: string
  input?: string
  path?: string
  output?: string
  output_mode?: string
  steps?: WorkflowStep[]
}

export interface Workflow {
  name: string
  label: string
  description: string
  variables: Record<string, string>
  steps: WorkflowStep[]
}

export interface WorkflowRunState {
  run_id: string
  workflow: string
  project_id: string
  status: string
  completed_paths: string[]
  updated_at: string
}

const _workflows = ref<Workflow[]>([])
const _isLoading = ref(false)
const _isRunning = ref(false)
const _currentRunId = ref<string | null>(null)
const _runLogs = ref<string[]>([])

export function useWorkflow() {
  async function fetchWorkflows() {
    _isLoading.value = true
    try {
      const data = await api.get<{ workflows: Workflow[] }>('/workflows')
      _workflows.value = data?.workflows || []
    } catch (e) {
      console.warn('获取工作流列表失败:', e)
    } finally {
      _isLoading.value = false
    }
  }

  async function fetchWorkflowDetail(name: string): Promise<Workflow | null> {
    try {
      const data = await api.get<{ workflow: Workflow }>(`/workflows/${name}`)
      return data?.workflow || null
    } catch (e) {
      console.warn('获取工作流详情失败:', e)
      return null
    }
  }

  async function runWorkflow(
    workflowName: string,
    projectId: string,
    variables: Record<string, string> = {},
    onEvent?: (event: string, data: any) => void,
  ): Promise<void> {
    if (_isRunning.value) return
    _isRunning.value = true
    _runLogs.value = []

    try {
      const response = await fetch('/api/workflows/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow: workflowName,
          project_id: projectId,
          variables,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6))
              const runId = parsed.run_id || parsed.runId
              if (runId) _currentRunId.value = runId

              if (currentEvent === 'workflow_error') {
                _runLogs.value.push(`[错误] ${parsed.message}`)
              } else if (currentEvent === 'step_start') {
                _runLogs.value.push(`[步骤] 开始: ${parsed.label}`)
              } else if (currentEvent === 'step_done') {
                _runLogs.value.push(`[步骤] 完成: ${parsed.label}`)
              } else if (currentEvent === 'step_skip') {
                _runLogs.value.push(`[步骤] 跳过: ${parsed.label}`)
              } else if (currentEvent === 'loop_iteration') {
                _runLogs.value.push(`[循环] ${parsed.label}: ${parsed.current}/${parsed.total}`)
              } else if (currentEvent === 'workflow_done') {
                _runLogs.value.push('[完成] 工作流执行完成')
              } else if (currentEvent === 'workflow_stopped') {
                _runLogs.value.push('[停止] 用户已停止')
              }

              if (onEvent) onEvent(currentEvent, parsed)
            } catch {
              // 跳过非 JSON 行
            }
          }
        }
      }
    } catch (e: any) {
      _runLogs.value.push(`[错误] ${e.message}`)
    } finally {
      _isRunning.value = false
    }
  }

  async function stopWorkflow(runId: string): Promise<boolean> {
    try {
      await api.post(`/workflows/stop/${runId}`)
      _runLogs.value.push('[停止] 已发送停止信号')
      return true
    } catch (e) {
      console.warn('停止工作流失败:', e)
      return false
    }
  }

  async function getRunStatus(runId: string): Promise<WorkflowRunState | null> {
    try {
      const data = await api.get<{ run: WorkflowRunState }>(`/workflows/runs/${runId}`)
      return data?.run || null
    } catch {
      return null
    }
  }

  async function saveWorkflow(data: {
    name: string
    label: string
    description?: string
    variables?: Record<string, string>
    steps: WorkflowStep[]
  }): Promise<boolean> {
    try {
      await api.post('/workflows/save', data)
      await fetchWorkflows()
      return true
    } catch (e) {
      console.warn('保存工作流失败:', e)
      return false
    }
  }

  async function deleteWorkflow(name: string): Promise<boolean> {
    try {
      await api.delete(`/workflows/${name}`)
      await fetchWorkflows()
      return true
    } catch (e) {
      console.warn('删除工作流失败:', e)
      return false
    }
  }

  return {
    workflows: readonly(_workflows),
    isLoading: readonly(_isLoading),
    isRunning: readonly(_isRunning),
    currentRunId: readonly(_currentRunId),
    runLogs: readonly(_runLogs),
    fetchWorkflows,
    fetchWorkflowDetail,
    runWorkflow,
    stopWorkflow,
    getRunStatus,
    saveWorkflow,
    deleteWorkflow,
  }
}
