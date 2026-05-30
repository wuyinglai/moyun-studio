import { ref, readonly, shallowRef } from 'vue'
import api from '@/services/api'
import { API_BASE, API_ROUTES } from '@/shared/api/routes'

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
  output_key?: string
  steps?: WorkflowStep[]
  // 节点元信息
  node_type?: string
  node_label?: string
  executor?: string
  executor_label?: string
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

// 节点状态
export type NodeStatus = 'pending' | 'running' | 'waiting_for_user' | 'completed' | 'failed' | 'skipped'

// 运行中的节点信息
export interface RunningNode {
  step_id: string
  label: string
  type: string
  path: string
  node_type: string
  node_label: string
  executor: string
  executor_label: string
  status: NodeStatus
  waiting_for_user: boolean
  waiting_reason: string
  actions: string[]
  input?: string
  output_key?: string
  output?: string
}

// 变量池条目
export interface VariablePoolEntry {
  key: string
  value: string
  source: 'user' | 'ai' | 'system' | 'approved'
}

const _workflows = ref<Workflow[]>([])
const _isLoading = ref(false)
const _isRunning = ref(false)
const _isPaused = ref(false)
const _currentRunId = ref<string | null>(null)
const _runLogs = ref<string[]>([])

// 节点状态
const _currentNode = shallowRef<RunningNode | null>(null)
const _nodeStates = ref<Record<string, NodeStatus>>({})
const _variablePool = ref<VariablePoolEntry[]>([])
const _stepsPreview = ref<WorkflowStep[]>([])

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
    onEvent?: (event: string, data: unknown) => void,
  ): Promise<boolean> {
    if (_isRunning.value) return false
    _isRunning.value = true
    _isPaused.value = false
    _runLogs.value = []
    _currentNode.value = null
    _nodeStates.value = {}
    _variablePool.value = []
    _stepsPreview.value = []
    let succeeded = false
    let failed = false

    try {
      const response = await fetch(API_BASE + API_ROUTES.workflowsRun, {
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
                failed = true
                _runLogs.value.push(`[错误] ${parsed.message}`)
                if (_currentNode.value?.step_id) {
                  _nodeStates.value[_currentNode.value.step_id] = 'failed'
                }
                _currentNode.value = null
              } else if (currentEvent === 'workflow_start') {
                _runLogs.value.push(`[开始] 工作流: ${parsed.label}`)
                // 保存步骤预览
                _stepsPreview.value = parsed.steps_preview || []
                // 初始化变量池
                _variablePool.value = Object.entries(parsed.variables || {}).map(([key, value]) => ({
                  key,
                  value: String(value),
                  source: 'user' as const,
                }))
                // 初始化节点状态
                for (const step of _stepsPreview.value) {
                  _nodeStates.value[step.id] = 'pending'
                }
              } else if (currentEvent === 'step_start') {
                _runLogs.value.push(`[${parsed.executor_label || 'AI'}] 开始: ${parsed.label} (${parsed.node_label || parsed.type})`)
                _nodeStates.value[parsed.step_id] = 'running'
                _currentNode.value = {
                  step_id: parsed.step_id,
                  label: parsed.label,
                  type: parsed.type,
                  path: parsed.path,
                  node_type: parsed.node_type || parsed.type,
                  node_label: parsed.node_label || parsed.label,
                  executor: parsed.executor || 'ai',
                  executor_label: parsed.executor_label || 'AI',
                  status: 'running',
                  waiting_for_user: parsed.waiting_for_user || false,
                  waiting_reason: parsed.waiting_reason || '',
                  actions: parsed.actions || [],
                  output: '',
                }
              } else if (currentEvent === 'step_waiting') {
                _isPaused.value = true
                _nodeStates.value[parsed.step_id] = 'waiting_for_user'
                _currentNode.value = {
                  ...(_currentNode.value || {
                    step_id: parsed.step_id || parsed.current_node || '',
                    label: parsed.label || parsed.current_node || '人工节点',
                    type: parsed.type || 'human_review',
                    path: parsed.path || '',
                    node_type: parsed.node_type || parsed.type || 'human_review',
                    node_label: parsed.node_label || parsed.label || '人工节点',
                    executor: parsed.executor || 'human',
                    executor_label: parsed.executor_label || '用户',
                  }),
                  status: 'waiting_for_user',
                  waiting_for_user: true,
                  waiting_reason: parsed.waiting_reason,
                  actions: parsed.actions,
                  input: parsed.input,
                  output_key: parsed.output_key,
                }
              } else if (currentEvent === 'workflow_paused') {
                _isPaused.value = true
                _isRunning.value = false
                const stepId = parsed.step_id || parsed.current_node
                if (stepId) {
                  _nodeStates.value[stepId] = 'waiting_for_user'
                  _currentNode.value = {
                    step_id: stepId,
                    label: parsed.label || stepId,
                    type: parsed.type || 'human_review',
                    path: parsed.path,
                    node_type: parsed.node_type || parsed.type || 'human_review',
                    node_label: parsed.node_label || parsed.label || '人工节点',
                    executor: parsed.executor || 'human',
                    executor_label: parsed.executor_label || '用户',
                    status: 'waiting_for_user',
                    waiting_for_user: true,
                    waiting_reason: parsed.waiting_reason || '',
                    actions: parsed.actions || parsed.available_actions || [],
                    input: parsed.input || parsed.waiting_input || '',
                    output_key: parsed.output_key,
                    output: '',
                  }
                }
              } else if (currentEvent === 'step_done') {
                const logMsg = `[${parsed.executor_label || 'AI'}] 完成: ${parsed.label}`
                _runLogs.value.push(logMsg)
                _nodeStates.value[parsed.step_id] = 'completed'
                if (_currentNode.value?.step_id === parsed.step_id) {
                  _currentNode.value = null
                }
                // 如果有输出，更新变量池
                if (parsed.output) {
                  _variablePool.value.push({
                    key: `step_${parsed.step_id}_output`,
                    value: parsed.output,
                    source: 'ai' as const,
                  })
                }
              } else if (currentEvent === 'step_skip') {
                _runLogs.value.push(`[跳过] ${parsed.label}`)
                _nodeStates.value[parsed.step_id] = 'skipped'
              } else if (currentEvent === 'loop_iteration') {
                _runLogs.value.push(`[循环] ${parsed.label}: ${parsed.current}/${parsed.total}`)
              } else if (currentEvent === 'variable_update') {
                _variablePool.value.push({
                  key: parsed.key,
                  value: parsed.value,
                  source: parsed.source as 'system' | 'ai' | 'user' | 'approved',
                })
              } else if (currentEvent === 'workflow_done') {
                succeeded = true
                _isPaused.value = false
                _runLogs.value.push('[完成] 工作流执行完成')
                _currentNode.value = null
              } else if (currentEvent === 'workflow_stopped') {
                failed = true
                _isPaused.value = false
                _runLogs.value.push('[停止] 用户已停止')
                _currentNode.value = null
              }

              if (onEvent) onEvent(currentEvent, parsed)
            } catch {
              // 跳过非 JSON 行
            }
          }
        }
      }
    } catch (e: unknown) {
      failed = true
      _runLogs.value.push(`[错误] ${e instanceof Error ? e.message : String(e)}`)
      _currentNode.value = null
    } finally {
      _isRunning.value = false
    }
    return succeeded && !failed
  }

  async function resumeWorkflow(
    runId: string,
    action: string,
    output: string = '',
    extraVars: Record<string, string> = {},
    onEvent?: (event: string, data: unknown) => void,
  ): Promise<boolean> {
    if (_isRunning.value) return false
    _isRunning.value = true
    let succeeded = false
    let failed = false

    try {
      const response = await fetch(API_BASE + API_ROUTES.workflowRunResume(runId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          output,
          extra_vars: extraVars,
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

              if (currentEvent === 'workflow_error') {
                failed = true
                _runLogs.value.push(`[错误] ${parsed.message}`)
                if (_currentNode.value?.step_id) {
                  _nodeStates.value[_currentNode.value.step_id] = 'failed'
                }
                _currentNode.value = null
              } else if (currentEvent === 'step_start') {
                _runLogs.value.push(`[${parsed.executor_label || 'AI'}] 开始: ${parsed.label} (${parsed.node_label || parsed.type})`)
                _nodeStates.value[parsed.step_id] = 'running'
                _currentNode.value = {
                  step_id: parsed.step_id,
                  label: parsed.label,
                  type: parsed.type,
                  path: parsed.path,
                  node_type: parsed.node_type || parsed.type,
                  node_label: parsed.node_label || parsed.label,
                  executor: parsed.executor || 'ai',
                  executor_label: parsed.executor_label || 'AI',
                  status: 'running',
                  waiting_for_user: parsed.waiting_for_user || false,
                  waiting_reason: parsed.waiting_reason || '',
                  actions: parsed.actions || [],
                  output: '',
                }
              } else if (currentEvent === 'step_waiting') {
                _isPaused.value = true
                _nodeStates.value[parsed.step_id] = 'waiting_for_user'
                _currentNode.value = {
                  ...(_currentNode.value || {
                    step_id: parsed.step_id || parsed.current_node || '',
                    label: parsed.label || parsed.current_node || '人工节点',
                    type: parsed.type || 'human_review',
                    path: parsed.path || '',
                    node_type: parsed.node_type || parsed.type || 'human_review',
                    node_label: parsed.node_label || parsed.label || '人工节点',
                    executor: parsed.executor || 'human',
                    executor_label: parsed.executor_label || '用户',
                  }),
                  status: 'waiting_for_user',
                  waiting_for_user: true,
                  waiting_reason: parsed.waiting_reason,
                  actions: parsed.actions,
                  input: parsed.input,
                  output_key: parsed.output_key,
                }
              } else if (currentEvent === 'workflow_paused') {
                _isPaused.value = true
                _isRunning.value = false
                const stepId = parsed.step_id || parsed.current_node
                if (stepId) {
                  _nodeStates.value[stepId] = 'waiting_for_user'
                  _currentNode.value = {
                    step_id: stepId,
                    label: parsed.label || stepId,
                    type: parsed.type || 'human_review',
                    path: parsed.path,
                    node_type: parsed.node_type || parsed.type || 'human_review',
                    node_label: parsed.node_label || parsed.label || '人工节点',
                    executor: parsed.executor || 'human',
                    executor_label: parsed.executor_label || '用户',
                    status: 'waiting_for_user',
                    waiting_for_user: true,
                    waiting_reason: parsed.waiting_reason || '',
                    actions: parsed.actions || parsed.available_actions || [],
                    input: parsed.input || parsed.waiting_input || '',
                    output_key: parsed.output_key,
                    output: '',
                  }
                }
              } else if (currentEvent === 'step_done') {
                const logMsg = `[${parsed.executor_label || 'AI'}] 完成: ${parsed.label}`
                _runLogs.value.push(logMsg)
                _nodeStates.value[parsed.step_id] = 'completed'
                if (_currentNode.value?.step_id === parsed.step_id) {
                  _currentNode.value = null
                }
                // 如果有输出，更新变量池
                if (parsed.output) {
                  _variablePool.value.push({
                    key: `step_${parsed.step_id}_output`,
                    value: parsed.output,
                    source: 'ai' as const,
                  })
                }
              } else if (currentEvent === 'step_skip') {
                _runLogs.value.push(`[跳过] ${parsed.label}`)
                _nodeStates.value[parsed.step_id] = 'skipped'
              } else if (currentEvent === 'loop_iteration') {
                _runLogs.value.push(`[循环] ${parsed.label}: ${parsed.current}/${parsed.total}`)
              } else if (currentEvent === 'variable_update') {
                _variablePool.value.push({
                  key: parsed.key,
                  value: parsed.value,
                  source: parsed.source as 'system' | 'ai' | 'user' | 'approved',
                })
              } else if (currentEvent === 'workflow_done') {
                succeeded = true
                _isPaused.value = false
                _runLogs.value.push('[完成] 工作流执行完成')
                _currentNode.value = null
              } else if (currentEvent === 'workflow_stopped') {
                failed = true
                _isPaused.value = false
                _runLogs.value.push('[停止] 用户已停止')
                _currentNode.value = null
              }

              if (onEvent) onEvent(currentEvent, parsed)
            } catch {
              // 跳过非 JSON 行
            }
          }
        }
      }
    } catch (e: unknown) {
      failed = true
      _runLogs.value.push(`[错误] ${e instanceof Error ? e.message : String(e)}`)
      _currentNode.value = null
    } finally {
      _isRunning.value = false
    }
    return succeeded && !failed
  }

  async function stopWorkflow(runId: string): Promise<boolean> {
    try {
      await api.post(API_ROUTES.workflowStop(runId))
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
      await api.post(API_ROUTES.workflowsSave, data)
      await fetchWorkflows()
      return true
    } catch (e) {
      console.warn('保存工作流失败:', e)
      return false
    }
  }

  async function deleteWorkflow(name: string): Promise<boolean> {
    try {
      await api.delete(API_ROUTES.workflowDetail(name))
      await fetchWorkflows()
      return true
    } catch (e) {
      console.warn('删除工作流失败:', e)
      return false
    }
  }

  // ─── Memory APIs ───────────────────────────────────────────────────

  interface MemoryUpdateResult {
    draft_update: string
    risk_level: 'low' | 'medium' | 'high'
    risk_reason: string
    updated_files: string[]
    requires_review: boolean
    content?: string
    scene_path?: string
  }

  async function updateMemory(
    projectId: string,
    content: string,
    scenePath?: string,
    chapterId?: string,
    forceReview = false
  ): Promise<MemoryUpdateResult | null> {
    try {
      const data = await api.post<MemoryUpdateResult>('/memory/update', {
        project_id: projectId,
        content,
        scene_path: scenePath,
        chapter_id: chapterId,
        force_review: forceReview,
      })
      return data || null
    } catch {
      return null
    }
  }

  interface MemoryStatus {
    project_id: string
    story_state_exists: boolean
    recent_context_exists: boolean
    recent_entries_count: number
    story_state_length: number
    recent_context_length: number
    last_updated: number | null
    story_engine_exists: boolean
    story_engine_length: number
    story_engine_mtime: number | null
    style_guide_exists: boolean
    style_guide_length: number
    style_guide_mtime: number | null
    recent_context_scene_limit: number
  }

  async function getMemoryStatus(projectId: string): Promise<MemoryStatus | null> {
    try {
      const data = await api.get<MemoryStatus>(`/memory/status/${projectId}`)
      return data || null
    } catch {
      return null
    }
  }

  // SSE 事件处理：记忆更新
  function handleMemoryEvents(eventSource: EventSource) {
    eventSource.addEventListener('memory_risk_assessment', (e) => {
      const data = JSON.parse(e.data)
      _runLogs.value.push(`[记忆风险] ${data.risk_level}: ${data.risk_reason}`)
    })

    eventSource.addEventListener('memory_update_done', (e) => {
      const data = JSON.parse(e.data)
      _runLogs.value.push(`[记忆更新] 已更新: ${data.updated_files.join(', ')}`)
    })
  }

  return {
    workflows: readonly(_workflows),
    isLoading: readonly(_isLoading),
    isRunning: readonly(_isRunning),
    isPaused: readonly(_isPaused),
    currentRunId: readonly(_currentRunId),
    runLogs: readonly(_runLogs),
    // 节点状态
    currentNode: readonly(_currentNode),
    nodeStates: readonly(_nodeStates),
    stepsPreview: readonly(_stepsPreview),
    variablePool: readonly(_variablePool),
    fetchWorkflows,
    fetchWorkflowDetail,
    runWorkflow,
    resumeWorkflow,
    stopWorkflow,
    getRunStatus,
    saveWorkflow,
    deleteWorkflow,
    // Memory APIs
    updateMemory,
    getMemoryStatus,
    handleMemoryEvents,
  }
}
