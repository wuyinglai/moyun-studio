import type { FlowRun } from './types'

export const mockWriteNextFlow: FlowRun = {
  id: 'write-next-success',
  title: '写下一场景',
  description: '从当前场景推导下一场景路径，读取故事记忆，构建 Prompt，调用 LLM，质量检查，保存结果，更新记忆',
  nodes: [
    {
      id: 'input-current-scene',
      label: '当前场景输入',
      description: '获取当前编辑的场景文件',
      type: 'input',
      status: 'success',
      outputs: [
        {
          id: 'current-file',
          label: 'sec-003.md',
          kind: 'file',
          path: 'chapters/vol-01/ch-001/sec-003.md',
        },
      ],
      durationMs: 12,
    },
    {
      id: 'derive-next-path',
      label: '推导下一场景路径',
      description: '根据当前场景位置，计算下一个要写的场景路径',
      type: 'process',
      status: 'success',
      inputs: [
        {
          id: 'input-path',
          label: 'sec-003.md',
          kind: 'file',
          path: 'chapters/vol-01/ch-001/sec-003.md',
        },
      ],
      outputs: [
        {
          id: 'target-path',
          label: 'sec-004.md',
          kind: 'file',
          path: 'chapters/vol-01/ch-001/sec-004.md',
        },
      ],
      durationMs: 8,
    },
    {
      id: 'load-memory',
      label: '读取故事记忆',
      description: '加载故事引擎、近期上下文和章节元数据',
      type: 'memory',
      status: 'success',
      outputs: [
        {
          id: 'story-engine',
          label: 'story-engine.md',
          kind: 'file',
          path: 'story-engine.md',
        },
        {
          id: 'recent-context',
          label: 'recent-context.md',
          kind: 'file',
          path: 'recent-context.md',
        },
        {
          id: 'ch-meta',
          label: 'ch-meta.json',
          kind: 'json',
          path: 'chapters/vol-01/ch-001/ch-meta.json',
        },
      ],
      durationMs: 45,
    },
    {
      id: 'build-prompt',
      label: '构建 Prompt',
      description: '组合故事记忆、用户偏好和当前场景，构建完整提示词',
      type: 'process',
      status: 'success',
      inputs: [
        {
          id: 'memory-input',
          label: '记忆数据',
          kind: 'json',
        },
        {
          id: 'prefs-input',
          label: '写作偏好',
          kind: 'json',
        },
      ],
      outputs: [
        {
          id: 'final-prompt',
          label: 'Prompt',
          kind: 'prompt',
          preview: '第1卷第1章第4场景\n故事引擎：\n- 主角目标：证明自己...\n- 当前冲突：旧秩序压迫...\n写作偏好：\n- 文风：热血\n- 节奏：快节奏...',
        },
      ],
      durationMs: 23,
    },
    {
      id: 'call-llm',
      label: '调用 LLM',
      description: '向 AI 模型发送请求，生成场景内容',
      type: 'llm',
      status: 'success',
      inputs: [
        {
          id: 'prompt-input',
          label: 'Prompt',
          kind: 'prompt',
        },
      ],
      outputs: [
        {
          id: 'llm-output',
          label: '生成内容',
          kind: 'text',
          preview: '第1卷第1章第4场景\n\n林浩深吸一口气，手中长剑缓缓出鞘...',
        },
      ],
      durationMs: 8762,
    },
    {
      id: 'quality-check',
      label: '质量检查',
      description: '检查生成内容的逻辑、爽点和连续性',
      type: 'quality',
      status: 'success',
      inputs: [
        {
          id: 'content-input',
          label: '生成内容',
          kind: 'text',
        },
      ],
      outputs: [
        {
          id: 'quality-result',
          label: '质量报告',
          kind: 'json',
          preview: '{"score": 92, "feedback": "逻辑通顺，爽点兑现"}',
        },
      ],
      durationMs: 1234,
    },
    {
      id: 'save-result',
      label: '保存结果',
      description: '将生成内容写入目标场景文件',
      type: 'file',
      status: 'success',
      inputs: [
        {
          id: 'final-content',
          label: '最终内容',
          kind: 'text',
        },
      ],
      outputs: [
        {
          id: 'saved-file',
          label: 'sec-004.md',
          kind: 'file',
          path: 'chapters/vol-01/ch-001/sec-004.md',
        },
      ],
      durationMs: 15,
    },
    {
      id: 'update-memory',
      label: '更新故事记忆',
      description: '更新故事引擎、近期上下文和章节元数据',
      type: 'memory',
      status: 'success',
      inputs: [
        {
          id: 'new-content',
          label: '新场景内容',
          kind: 'text',
        },
      ],
      outputs: [
        {
          id: 'updated-engine',
          label: 'story-engine.md',
          kind: 'file',
          path: 'story-engine.md',
        },
        {
          id: 'updated-meta',
          label: 'ch-meta.json',
          kind: 'json',
          path: 'chapters/vol-01/ch-001/ch-meta.json',
        },
      ],
      durationMs: 38,
    },
    {
      id: 'refresh-ui',
      label: '刷新编辑器',
      description: '更新编辑器显示，准备下一场景选项',
      type: 'ui',
      status: 'success',
      durationMs: 42,
    },
  ],
}

export const mockErrorFlow: FlowRun = {
  id: 'write-next-error',
  title: '写下一场景（失败示例）',
  description: '模拟 LLM 请求超时的失败流程',
  nodes: [
    {
      id: 'input-current-scene',
      label: '当前场景输入',
      description: '获取当前编辑的场景文件',
      type: 'input',
      status: 'success',
      outputs: [
        {
          id: 'current-file',
          label: 'sec-003.md',
          kind: 'file',
          path: 'chapters/vol-01/ch-001/sec-003.md',
        },
      ],
      durationMs: 12,
    },
    {
      id: 'derive-next-path',
      label: '推导下一场景路径',
      description: '根据当前场景位置，计算下一个要写的场景路径',
      type: 'process',
      status: 'success',
      inputs: [
        {
          id: 'input-path',
          label: 'sec-003.md',
          kind: 'file',
        },
      ],
      outputs: [
        {
          id: 'target-path',
          label: 'sec-004.md',
          kind: 'file',
          path: 'chapters/vol-01/ch-001/sec-004.md',
        },
      ],
      durationMs: 8,
    },
    {
      id: 'load-memory',
      label: '读取故事记忆',
      description: '加载故事引擎、近期上下文和章节元数据',
      type: 'memory',
      status: 'success',
      durationMs: 45,
    },
    {
      id: 'build-prompt',
      label: '构建 Prompt',
      description: '组合故事记忆、用户偏好和当前场景',
      type: 'process',
      status: 'success',
      durationMs: 23,
    },
    {
      id: 'call-llm',
      label: '调用 LLM',
      description: '向 AI 模型发送请求，生成场景内容',
      type: 'llm',
      status: 'error',
      error: 'LLM timeout after 45s',
      durationMs: 45000,
    },
    {
      id: 'quality-check',
      label: '质量检查',
      description: '检查生成内容的逻辑、爽点和连续性（因上游失败跳过）',
      type: 'quality',
      status: 'skipped',
    },
    {
      id: 'save-result',
      label: '保存结果',
      description: '将生成内容写入目标场景文件（因上游失败跳过）',
      type: 'file',
      status: 'skipped',
    },
    {
      id: 'update-memory',
      label: '更新故事记忆',
      description: '更新故事引擎和章节元数据（因上游失败跳过）',
      type: 'memory',
      status: 'skipped',
    },
    {
      id: 'refresh-ui',
      label: '刷新编辑器',
      description: '更新编辑器显示（因上游失败跳过）',
      type: 'ui',
      status: 'skipped',
    },
  ],
}