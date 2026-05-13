import { ref } from 'vue'
import { useEditorStore } from '@/stores/editor'

// Module-level singleton refs -- shared across all consumers
const _isGenerating = ref(false)
const _currentPrompt = ref('')
let _abortController: AbortController | null = null

export function useFileGeneration() {
  const editorStore = useEditorStore()

  /**
   * 对指定文件进行流式生成
   */
  async function generateToFile(
    projectId: string,
    filePath: string,
    prompt?: string,
    extraVars?: Record<string, string>,
    promptType?: string,
  ) {
    if (_isGenerating.value) return

    _isGenerating.value = true
    _currentPrompt.value = prompt || ''
    _abortController = new AbortController()

    // 记录当前 prompt 与该文件的关联
    if (prompt) {
      editorStore.setFilePrompt(filePath, prompt)
    }

    try {
      // 确保编辑器已打开该文件
      editorStore.setCurrentFile(filePath)

      const body: Record<string, unknown> = {
        project_id: projectId,
        file_path: filePath,
        prompt_type: promptType || 'generate/continuation',
        extra_vars: { ...(extraVars || {}) },
        mode: 'append',
        stream: true,
      }

      if (prompt) {
        body.extra_vars = { ...(body.extra_vars as Record<string, string>), user_prompt: prompt }
      }

      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: _abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      await parseSSEStream(reader, (delta) => {
        editorStore.appendContent(delta)
      }, (prompt) => {
        _currentPrompt.value = prompt
        editorStore.setFilePrompt(filePath, prompt)
      })

      _isGenerating.value = false
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // 用户取消，不报错
      } else {
        throw e
      }
    } finally {
      _isGenerating.value = false
      _abortController = null
    }
  }

  function cancelGeneration() {
    _abortController?.abort()
    _isGenerating.value = false
  }

  /**
   * 运行管线（流式输出到编辑器）
   */
  async function runPipeline(
    projectId: string,
    filePath: string,
    pipelineName: string,
  ) {
    if (_isGenerating.value) return

    _isGenerating.value = true
    _currentPrompt.value = ''
    _abortController = new AbortController()

    try {
      editorStore.setCurrentFile(filePath)

      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pipeline: pipelineName,
          project_id: projectId,
          target_file: filePath,
          output_mode: pipelineName === 'generate' ? 'append' : 'overwrite',
        }),
        signal: _abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      await parseSSEStream(reader, (delta) => {
        editorStore.appendContent(delta)
      }, (prompt) => {
        _currentPrompt.value = prompt
        editorStore.setFilePrompt(filePath, prompt)
      })

    } catch (e: any) {
      if (e.name !== 'AbortError') throw e
    } finally {
      _isGenerating.value = false
      _abortController = null
    }
  }

  /**
   * 解析 SSE 流，提取 delta 内容
   */
  async function parseSSEStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onDelta: (delta: string) => void,
    onPrompt?: (prompt: string) => void,
  ): Promise<void> {
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
            if (currentEvent === 'prompt' && parsed.prompt && onPrompt) {
              onPrompt(parsed.prompt)
            } else if (parsed.delta) {
              onDelta(parsed.delta)
            } else if (parsed.content) {
              onDelta(parsed.content)
            }
          } catch {
            // 跳过非 JSON 行
          }
        }
      }
    }
  }

  return {
    isGenerating: _isGenerating,
    currentPrompt: _currentPrompt,
    generateToFile,
    runPipeline,
    cancelGeneration,
  }
}
