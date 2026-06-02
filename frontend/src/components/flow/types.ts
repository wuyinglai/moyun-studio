export type FlowNodeStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'error'
  | 'skipped'

export type FlowNodeType =
  | 'input'
  | 'process'
  | 'llm'
  | 'file'
  | 'candidate'
  | 'memory'
  | 'ui'
  | 'quality'

export interface FlowArtifact {
  id: string
  label: string
  kind: 'file' | 'text' | 'prompt' | 'candidate' | 'json'
  path?: string
  preview?: string
  size?: number
}

export interface FlowNode {
  id: string
  label: string
  description?: string
  type: FlowNodeType
  status: FlowNodeStatus
  inputs?: FlowArtifact[]
  outputs?: FlowArtifact[]
  durationMs?: number
  error?: string
}

export interface FlowRun {
  id: string
  title: string
  description?: string
  nodes: FlowNode[]
}