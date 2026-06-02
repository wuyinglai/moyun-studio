import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { FlowRun } from '@/components/flow/types'

export const useFlowStore = defineStore('flow', () => {
  const activeFlow = ref<FlowRun | null>(null)
  const nodeStartTimes = ref<Record<string, number>>({})

  function startLiteWriteFlow(_payload: {
    sourcePath?: string
    targetPath?: string
    isCandidate?: boolean
  }) {
    // 我们在 components/flow/liteFlowTemplates.ts 中定义了模板，但 store 不应该直接导入组件目录
    // 所以我们这里只创建一个基础结构，实际模板在 useFlowRun composable 中处理
    activeFlow.value = null
    nodeStartTimes.value = {}
  }

  function setActiveFlow(flow: FlowRun | null) {
    activeFlow.value = flow
  }

  function markNodeRunning(nodeId: string) {
    if (!activeFlow.value) return
    nodeStartTimes.value[nodeId] = Date.now()
    const node = activeFlow.value.nodes.find((n) => n.id === nodeId)
    if (node) {
      node.status = 'running'
    }
  }

  function markNodeSuccess(nodeId: string, outputs?: any[]) {
    if (!activeFlow.value) return
    const node = activeFlow.value.nodes.find((n) => n.id === nodeId)
    if (node) {
      node.status = 'success'
      if (outputs) {
        node.outputs = outputs
      }
      if (nodeStartTimes.value[nodeId]) {
        node.durationMs = Date.now() - nodeStartTimes.value[nodeId]
      }
    }
  }

  function markNodeError(nodeId: string, error: string) {
    if (!activeFlow.value) return
    const node = activeFlow.value.nodes.find((n) => n.id === nodeId)
    if (node) {
      node.status = 'error'
      node.error = error
      if (nodeStartTimes.value[nodeId]) {
        node.durationMs = Date.now() - nodeStartTimes.value[nodeId]
      }
      // 标记后续节点为跳过
      const idx = activeFlow.value.nodes.indexOf(node)
      if (idx >= 0) {
        for (let i = idx + 1; i < activeFlow.value.nodes.length; i++) {
          const nextNode = activeFlow.value.nodes[i]
          if (['pending', 'running'].includes(nextNode.status)) {
            markNodeSkipped(nextNode.id)
          }
        }
      }
    }
  }

  function markNodeSkipped(nodeId: string) {
    if (!activeFlow.value) return
    const node = activeFlow.value.nodes.find((n) => n.id === nodeId)
    if (node) {
      node.status = 'skipped'
    }
  }

  function resetFlow() {
    activeFlow.value = null
    nodeStartTimes.value = {}
  }

  return {
    activeFlow,
    startLiteWriteFlow,
    setActiveFlow,
    markNodeRunning,
    markNodeSuccess,
    markNodeError,
    markNodeSkipped,
    resetFlow,
  }
})
