/** 工作流任务引导 — ⚡快捷 标签页的步骤引导
 *
 * 模块级单例状态，useWorkflowGuide() 在所有组件中返回同一实例。
 *
 * L1: 每步完成后暂停，paused=true，用户点"写下一部分"恢复。
 * L2: 自动连续执行，用户可停止，停止后 paused=true，"写下一部分"恢复。
 */

import { ref, computed } from 'vue'
import api from '@/services/api'
import { useFileGeneration } from './useFileGeneration'
import { useNotificationStore } from '@/stores/notification'
import { useTaskStore } from '@/stores/task'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'

export type StepStatus = 'pending' | 'running' | 'done' | 'waiting'

export interface GuideStepItem {
  id: string
  label: string
  type: string
  pipeline?: string
  output?: string | null
  status: StepStatus
}

// ── 模块级单例状态 ────────────────────────────────

const _steps = ref<GuideStepItem[]>([])
const _currentStepIndex = ref(-1)
const _isRunning = ref(false)
const _paused = ref(false)
const _shouldStop = ref(false)
const _workflowName = ref('full-novel')
const _workflowLabel = ref('')
const _error = ref<string | null>(null)

// ── Composable ─────────────────────────────────────

export function useWorkflowGuide() {
  const fileGen = useFileGeneration()
  const notification = useNotificationStore()
  const taskStore = useTaskStore()

  const currentStep = computed(() =>
    _currentStepIndex.value >= 0 && _currentStepIndex.value < _steps.value.length
      ? _steps.value[_currentStepIndex.value]
      : null,
  )

  const progress = computed(() => {
    if (_steps.value.length === 0) return { done: 0, total: 0, percent: 0 }
    const done = _steps.value.filter(s => s.status === 'done' || s.status === 'waiting').length
    return { done, total: _steps.value.length, percent: Math.round(done / _steps.value.length * 100) }
  })

  /** 是否有正在等待恢复的步骤（L1 待确认 / L2 已停止） */
  const isPaused = computed(() => _paused.value)

  /** 从后端加载工作流定义 */
  async function loadWorkflow(name = 'full-novel') {
    try {
      const res = await api.get<{ workflow: any }>(`/workflows/${name}`)
      const wf = res?.workflow
      if (!wf) {
        _error.value = '未找到工作流'
        _steps.value = []
        return
      }
      _workflowName.value = wf.name
      _workflowLabel.value = wf.label

      _steps.value = wf.steps.map((s: any) => ({
        id: s.id,
        label: s.label,
        type: s.type,
        pipeline: s.pipeline,
        output: s.output,
        status: 'pending' as StepStatus,
      }))
      _error.value = null
    } catch (e: any) {
      _error.value = e.message || '加载工作流失败'
      _steps.value = []
    }
  }

  function getAutoMode(): string {
    return localStorage.getItem('moyun-auto-mode') || 'L1'
  }

  /** 从当前 stepIndex 开始执行 */
  async function runFromCurrent(projectId: string, filePath: string) {
    const step = _steps.value[_currentStepIndex.value]
    if (!step) {
      finishWorkflow()
      return
    }

    step.status = 'running'
    _paused.value = false

    // 在 LLM 工作堆栈中显示当前步骤
    const wfTaskId = `wf-${step.id}-${Date.now()}`
    const wfTaskName = `工作流: ${step.label}`

    try {
      if (step.type === 'pipeline' && step.pipeline) {
        taskStore.addLog('info', `执行: ${step.label}`)
        taskStore.addTask(wfTaskId, wfTaskName)
        taskStore.startTask(wfTaskId)

        // 使用工作流定义的 output 路径（如有），否则用当前文件
        const targetFile = step.output || filePath

        await fileGen.runPipeline(projectId, targetFile, step.pipeline)

        taskStore.completeTask(wfTaskId)
        taskStore.addLog('success', `完成: ${wfTaskName}`)

        // pipeline 完成后：如果是新文件，刷新文件树并打开
        if (step.output && step.output !== filePath) {
          const fileStore = useFileStore()
          const editorStore = useEditorStore()
          await fileStore.loadTree(projectId)
          const node = { name: step.output.split('/').pop() || '', path: step.output, type: 'file' as const }
          fileStore.openFile(node)
          editorStore.setCurrentFile(step.output)
          try {
            const content = await fileStore.readFile(projectId, step.output)
            if (content) editorStore.loadContent(step.output, content.content || '')
          } catch { /* file may not exist yet */ }
        }
      } else {
        await new Promise(r => setTimeout(r, 300))
      }

      if (!_isRunning.value) return

      step.status = 'done'
      taskStore.addLog('success', `完成: ${step.label}`)

      // L1: 每步完成后暂停，等待"写下一部分"
      if (getAutoMode() === 'L1' && _currentStepIndex.value < _steps.value.length - 1) {
        step.status = 'waiting'
        _paused.value = true
        taskStore.addLog('info', `⏸${step.label} 完成，点"写下一部分"继续`)
      } else {
        advanceAndRun(projectId, filePath)
      }
    } catch (e: any) {
      if (!_isRunning.value) return
      step.status = 'done'
      taskStore.failTask(wfTaskId)
      taskStore.addLog('error', `失败: ${step.label} — ${e.message}`)
      advanceAndRun(projectId, filePath)
    }
  }

  function advanceAndRun(projectId: string, filePath: string) {
    // L2 停止标记：停下来等待恢复
    if (_shouldStop.value) {
      _shouldStop.value = false
      _paused.value = true
      taskStore.addLog('info', `⏹ 已停止，点"写下一部分"继续`)
      return
    }
    _currentStepIndex.value++
    runFromCurrent(projectId, filePath)
  }

  function finishWorkflow() {
    _isRunning.value = false
    _paused.value = false
    _currentStepIndex.value = -1
    taskStore.addLog('success', '🎉 工作流全部完成')
  }

  // ─── 公开方法 ──────────────────────────────────────

  /** 开始工作流（从第1步） */
  async function start(projectId: string, filePath: string) {
    if (_isRunning.value) return
    if (!projectId || !filePath) {
      notification.warning('请先打开一个文件和项目')
      return
    }
    if (_steps.value.length === 0) {
      await loadWorkflow()
      if (_steps.value.length === 0) {
        notification.error('无法加载工作流')
        return
      }
    }

    _resetState()
    _isRunning.value = true
    _currentStepIndex.value = 0
    notification.info('工作流开始执行')
    await runFromCurrent(projectId, filePath)
  }

  /** 恢复执行（L1 确认 / L2 停止后继续） */
  async function resume(projectId: string, filePath: string) {
    if (!_paused.value || !_isRunning.value) return

    // L1: 当前步骤在 waiting 状态
    const step = _steps.value[_currentStepIndex.value]
    if (step?.status === 'waiting') {
      step.status = 'done'
      _currentStepIndex.value++
      await runFromCurrent(projectId, filePath)
      return
    }

    // L2 停止后恢复：从当前已完成的下一步开始
    if (_currentStepIndex.value < _steps.value.length) {
      _currentStepIndex.value++
      await runFromCurrent(projectId, filePath)
    } else {
      finishWorkflow()
    }
  }

  /** 停止工作流（L2：完成当前步后暂停） */
  function stopAfterCurrent() {
    if (!_isRunning.value) return
    if (getAutoMode() === 'L1') {
      // L1 已经暂停，无事可做
      return
    }
    // L2: 标记停止，当前步骤完成后不再继续
    _shouldStop.value = true
    fileGen.cancelGeneration()
    taskStore.addLog('warning', '⏹ 将在当前步骤完成后停止')
  }

  /** 立即停止（不等待当前步） */
  function stopNow() {
    _isRunning.value = false
    _paused.value = false
    _shouldStop.value = false
    _currentStepIndex.value = -1
    fileGen.cancelGeneration()
    taskStore.addLog('warning', '⏹ 工作流已停止')
  }

  function _resetState() {
    _shouldStop.value = false
    _paused.value = false
    _steps.value.forEach(s => (s.status = 'pending'))
  }

  /** 重置所有步骤状态 */
  function reset() {
    _isRunning.value = false
    _paused.value = false
    _shouldStop.value = false
    _currentStepIndex.value = -1
    _steps.value.forEach(s => (s.status = 'pending'))
  }

  return {
    // 只读状态
    steps: _steps,
    currentStepIndex: _currentStepIndex,
    isRunning: _isRunning,
    isPaused,
    workflowName: _workflowName,
    workflowLabel: _workflowLabel,
    error: _error,
    currentStep,
    progress,
    // 方法
    loadWorkflow,
    start,
    resume,
    stopAfterCurrent,
    stopNow,
    reset,
  }
}
