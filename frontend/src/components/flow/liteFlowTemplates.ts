import type { FlowNode } from './types'

export function createLiteWriteFlowTemplate({
  sourcePath,
  targetPath,
  isCandidate,
}: {
  sourcePath?: string
  targetPath?: string
  isCandidate?: boolean
}): FlowNode[] {
  const nodes: FlowNode[] = [
    {
      id: 'current_scene_input',
      label: '当前场景输入',
      description: '读取当前场景的内容和位置',
      type: 'input',
      status: 'pending',
      outputs: sourcePath
        ? [
            {
              id: 'source-file',
              label: '当前场景文件',
              kind: 'file',
              path: sourcePath,
            },
          ]
        : [],
    },
    {
      id: 'infer_next_path',
      label: '推导下一场景路径',
      description: '根据当前场景，计算下一场景的文件路径',
      type: 'process',
      status: 'pending',
      outputs: targetPath
        ? [
            {
              id: 'target-file',
              label: '目标场景文件',
              kind: 'file',
              path: targetPath,
            },
          ]
        : [],
    },
    {
      id: 'read_story_memory',
      label: '读取故事记忆',
      description: '读取故事引擎、近期上下文、场景记忆和章节元数据',
      type: 'memory',
      status: 'pending',
      outputs: [
        { id: 'story-engine', label: '故事引擎', kind: 'json' },
        { id: 'recent-context', label: '近期上下文', kind: 'text' },
        { id: 'chapter-meta', label: '章节元数据', kind: 'json' },
      ],
    },
    {
      id: 'build_prompt',
      label: '构建 Prompt',
      description: '把当前场景、故事记忆、用户要求和爽点结合成最终 Prompt',
      type: 'process',
      status: 'pending',
    },
    {
      id: 'call_llm',
      label: '调用 LLM',
      description: isCandidate ? '调用 LLM 生成候选稿正文' : '调用 LLM 生成场景正文',
      type: 'llm',
      status: 'pending',
    },
    {
      id: 'quality_check',
      label: '质量检查',
      description: '检查生成内容的逻辑、爽点和连续性',
      type: 'quality',
      status: 'pending',
    },
    {
      id: 'save_or_candidate',
      label: isCandidate ? '创建候选稿' : '保存文件',
      description: isCandidate
        ? '把生成的内容保存为候选稿，不覆盖原文'
        : '把生成的内容保存到文件系统',
      type: isCandidate ? 'candidate' : 'file',
      status: 'pending',
      outputs: targetPath
        ? [
            {
              id: 'output-file',
              label: isCandidate ? '候选稿文件' : '保存的场景',
              kind: 'file',
              path: targetPath,
            },
          ]
        : [],
    },
    {
      id: 'update_memory',
      label: '更新故事记忆',
      description: '更新故事引擎、近期上下文和场景记忆，保证后续连续性',
      type: 'memory',
      status: 'pending',
    },
    {
      id: 'refresh_ui',
      label: '刷新编辑器',
      description: '打开生成的文件并在编辑器中显示',
      type: 'ui',
      status: 'pending',
    },
  ]

  return nodes
}
