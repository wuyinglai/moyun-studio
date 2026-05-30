/** 工作流任务引导 — ⚡快捷 标签页的步骤引导
 *
 * 模块级单例状态，useWorkflowGuide() 在所有组件中返回同一实例。
 *
 * L1: 每步完成后暂停，paused=true，用户点"写下一场景"恢复。
 * L2: 自动连续执行，用户可停止，停止后 paused=true，"写下一场景"恢复。
 */

import { ref, computed, watch } from 'vue'
import api from '@/services/api'
import { useFileGeneration } from './useFileGeneration'
import { useNotificationStore } from '@/stores/notification'
import { useTaskStore } from '@/stores/task'
import { useFileStore } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useProjectStore } from '@/stores/project'
import { buildScenePath } from '@/modules/scene/scenePath'

export type StepStatus = 'pending' | 'running' | 'done' | 'waiting'

export interface GuideStepItem {
  id: string
  label: string
  type: string
  pipeline?: string
  output?: string | null
  status: StepStatus
}

/** 展开 loop 步骤为单个 pipeline 步骤列表 */
async function expandLoopStep(projectId: string, step: GuideStepItem): Promise<GuideStepItem[]> {
  type WfStep = { id: string; type: string; pipeline?: string; output?: string; steps?: WfStep[] }
  const res = await api.get<{ workflow: { steps: WfStep[] } }>(`/workflows/${_workflowName.value}`)
  const loopDef = res?.workflow?.steps?.find((s) => s.id === step.id)
  if (!loopDef?.steps) return []

  const chaptersLoop = loopDef.steps.find((s) => s.type === 'loop')
  if (!chaptersLoop?.steps) return []

  const genStep = chaptersLoop.steps.find((s) => s.type === 'pipeline' && s.pipeline)
  if (!genStep) return []

  const extractStep = chaptersLoop.steps.find((s) => s.pipeline === 'extract')
  const storyStateStep = chaptersLoop.steps.find((s) => s.pipeline === 'story-state')

  // 从项目 target_word_count 计算卷/章数量（和后端 wizard.py 算法一致）
  const projectStore = useProjectStore()
  const tgt = projectStore.currentProject?.target_word_count || 50000
  const sections = Math.max(1, Math.floor(tgt / 1800))
  const chCount = Math.ceil(sections / 4)
  const volCount = Math.max(1, Math.ceil(chCount / 12))

  const expanded: GuideStepItem[] = []
  for (let vol = 1; vol <= volCount; vol++) {
    for (let ch = 1; ch <= chCount; ch++) {
      const volPad = String(vol).padStart(2, '0')
      const chPad = String(ch).padStart(3, '0')

      const resolvePath = (t: string) =>
        t.replace('{{project_id}}', projectId).replace('{{vol|pad:2}}', volPad).replace('{{ch|pad:3}}', chPad)

      // 每章固定 4 节，逐节生成
      for (let sec = 1; sec <= 4; sec++) {
        const secPad = String(sec).padStart(3, '0')
        const secOutput = buildScenePath(vol, ch, sec)
        expanded.push({
          id: `vol-${volPad}-ch-${chPad}-sec-${secPad}`,
          label: `正文 第${vol}卷第${ch}章第${sec}场景`,
          type: 'pipeline',
          pipeline: genStep.pipeline,
          output: secOutput,
          status: 'pending',
        })
      }

      // extracts 只在每章执行一次
      if (extractStep?.output) {
        expanded.push({
          id: `vol-${volPad}-ch-${chPad}-extract`,
          label: `提取 第${vol}卷第${ch}章`,
          type: 'pipeline',
          pipeline: extractStep.pipeline,
          output: resolvePath(extractStep.output),
          status: 'pending',
        })
      }

      // story-state 每章更新一次
      if (storyStateStep?.pipeline) {
        expanded.push({
          id: `vol-${volPad}-ch-${chPad}-story`,
          label: `状态 第${vol}卷第${ch}章`,
          type: 'pipeline',
          pipeline: storyStateStep.pipeline,
          output: storyStateStep.output || '',
          status: 'pending',
        })
      }
    }
  }
  return expanded
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

  // 切换项目时自动重置工作流状态
  const projectStore = useProjectStore()
  watch(() => projectStore.currentProject?.id, () => {
    if (_isRunning.value) reset()
  })

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
      const res = await api.get<{ workflow: { name: string; label: string; steps: Array<{ id: string; label: string; type: string; pipeline?: string; output?: string | null }> } }>(`/workflows/${name}`)
      const wf = res?.workflow
      if (!wf) {
        _error.value = '未找到工作流'
        _steps.value = []
        return
      }
      _workflowName.value = wf.name
      _workflowLabel.value = wf.label

      _steps.value = (wf.steps as Array<{ id: string; label: string; type: string; pipeline?: string; output?: string | null }>).map((s) => ({
        id: s.id,
        label: s.label,
        type: s.type,
        pipeline: s.pipeline,
        output: s.output,
        status: 'pending' as StepStatus,
      }))
      _error.value = null
    } catch (e: unknown) {
      _error.value = (e instanceof Error ? e.message : '') || '加载工作流失败'
      _steps.value = []
    }
  }

  function getAutoMode(): string {
    try {
      return localStorage.getItem('moyun-auto-mode') || 'L1'
    } catch {
      return 'L1'
    }
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

        // 解析 step.output 中的模板变量
        const resolved = (step.output || '').replace('{{project_id}}', projectId)
        const targetFile = resolved || filePath

        if (resolved && resolved !== filePath) {
          const fileStore = useFileStore()
          const editorStore = useEditorStore()
          await fileStore.loadTree(projectId)
          const node = { name: resolved.split('/').pop() || '', path: resolved, type: 'file' as const }
          fileStore.openFile(node)
          editorStore.setCurrentFile(resolved)
          try {
            const content = await fileStore.readFile(projectId, resolved)
            if (content) editorStore.loadContent(resolved, content.content || '')
          } catch { /* file may not exist yet */ }
        }

        await fileGen.runPipeline(projectId, targetFile, step.pipeline, undefined, 'write_scene')

        taskStore.completeTask(wfTaskId)
        taskStore.addLog('success', `完成: ${wfTaskName}`)

        if (resolved && resolved !== filePath) {
          const fileStore = useFileStore()
          const editorStore = useEditorStore()
          await fileStore.loadTree(projectId)
          try {
            const content = await fileStore.readFile(projectId, resolved)
            if (content) {
              editorStore.loadContent(resolved, content.content || '')
              editorStore.contentSource = 'external'
            }
          } catch { /* file may not exist yet */ }
        }
      } else if (step.type === 'loop') {
        // 展开循环为单个 pipeline 步骤，实现逐节 L1 确认
        taskStore.addLog('info', `展开循环: ${step.label}`)
        const expanded = await expandLoopStep(projectId, step)
        if (expanded.length > 0) {
          // 替换当前步骤为展开后的步骤列表
          _steps.value.splice(_currentStepIndex.value, 1, ...expanded)
          // 重新执行当前索引（现在指向第一个展开步骤）
          await runFromCurrent(projectId, filePath)
          return
        }
        taskStore.addLog('warning', `无法展开循环: ${step.label}，跳过`)
      } else {
        // 其他类型（file 等）跳过
        taskStore.addLog('info', `跳过: ${step.label}`)
      }

      if (!_isRunning.value) return

      step.status = 'done'
      taskStore.addLog('success', `完成: ${step.label}`)

      // L1: 每步完成后暂停，等待"写下一场景"
      if (getAutoMode() === 'L1' && _currentStepIndex.value < _steps.value.length - 1) {
        step.status = 'waiting'
        _paused.value = true
        taskStore.addLog('info', `⏸${step.label} 完成，点"写下一场景"继续`)
      } else {
        advanceAndRun(projectId, filePath)
      }
    } catch (e: unknown) {
      if (!_isRunning.value) return
      step.status = 'done'
      taskStore.failTask(wfTaskId)
      taskStore.addLog('error', `失败: ${step.label} — ${e instanceof Error ? e.message : String(e)}`)
      advanceAndRun(projectId, filePath)
    }
  }

  function advanceAndRun(projectId: string, filePath: string) {
    // L2 停止标记：停下来等待恢复
    if (_shouldStop.value) {
      _shouldStop.value = false
      _paused.value = true
      taskStore.addLog('info', `⏹ 已停止，点"写下一场景"继续`)
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
