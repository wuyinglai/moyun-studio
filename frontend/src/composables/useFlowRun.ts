import { ref, computed } from 'vue'
import { useFlowStore } from '@/stores/flow'
import type { FlowNode, FlowArtifact } from '@/components/flow/types'
import { createLiteWriteFlowTemplate } from '@/components/flow/liteFlowTemplates'

export function useFlowRun() {
  const store = useFlowStore()
  const localNodeStartTimes = ref<Record<string, number>>({})

  const activeFlow = computed(() => store.activeFlow)

  function startLiteWriteFlow(payload: {
    sourcePath?: string
    targetPath?: string
    isCandidate?: boolean
  }) {
    const nodes = createLiteWriteFlowTemplate({
      sourcePath: payload.sourcePath,
      targetPath: payload.targetPath,
      isCandidate: payload.isCandidate,
    })
    store.setActiveFlow({
      id: `lite-write-${Date.now()}`,
      title: '写下一场景',
      description: payload.isCandidate ? '候选稿生成' : '场景生成',
      nodes,
    })
    localNodeStartTimes.value = {}

    markNodeSuccess('current_scene_input')
    markNodeRunning('infer_next_path')
  }

  function getNodeIndex(nodeId: string): number {
    if (!store.activeFlow) return -1
    return store.activeFlow.nodes.findIndex((n) => n.id === nodeId)
  }

  function updateNode(nodeId: string, update: Partial<FlowNode>) {
    if (!store.activeFlow) return
    const node = store.activeFlow.nodes.find((n) => n.id === nodeId)
    if (!node) return

    if (update.status && update.status !== node.status) {
      if (update.status === 'running') {
        localNodeStartTimes.value[nodeId] = Date.now()
      } else if (
        (update.status === 'success' || update.status === 'error') &&
        localNodeStartTimes.value[nodeId]
      ) {
        const duration = Date.now() - localNodeStartTimes.value[nodeId]
        update.durationMs = duration
      }
    }

    Object.assign(node, update)

    if (
      (update.status === 'success' || update.status === 'error') &&
      update.status !== node.status
    ) {
      if (update.status === 'error') {
        const idx = getNodeIndex(nodeId)
        if (idx >= 0) {
          for (let i = idx + 1; i < store.activeFlow.nodes.length; i++) {
            const nextNode = store.activeFlow.nodes[i]
            if (['pending', 'running'].includes(nextNode.status)) {
              markNodeSkipped(nextNode.id)
            }
          }
        }
      }
    }
    // 触发 store 更新
    store.setActiveFlow({ ...store.activeFlow })
  }

  function markNodeRunning(nodeId: string) {
    updateNode(nodeId, { status: 'running' })
  }

  function markNodeSuccess(nodeId: string, outputs?: FlowArtifact[]) {
    updateNode(nodeId, { status: 'success', outputs })
  }

  function markNodeError(nodeId: string, error: string) {
    updateNode(nodeId, { status: 'error', error })
  }

  function markNodeSkipped(nodeId: string) {
    updateNode(nodeId, { status: 'skipped' })
  }

  function resetFlow() {
    store.resetFlow()
    localNodeStartTimes.value = {}
  }

  return {
    activeFlow,
    startLiteWriteFlow,
    markNodeRunning,
    markNodeSuccess,
    markNodeError,
    markNodeSkipped,
    resetFlow,
  }
}
