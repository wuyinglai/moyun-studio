import { ref } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useFileStore } from '@/stores/file'
import { useFileMetaStore } from '@/stores/fileMeta'

// Module-level singleton refs -- shared across all consumers
const _isGenerating = ref(false)
const _currentPrompt = ref('')
let _abortController: AbortController | null = null

/**
 * GenerationEmitter - 统一事件分发中心
 * useFileGeneration 通过 fetch+ReadableStream 解析 SSE 事件，
 * 通过此 Emitter 分发给其他组件，避免与 useSSE (EventSource) 重复处理
 */
export class GenerationEmitter extends EventTarget {
  emit(type: string, data: unknown) {
    this.dispatchEvent(new CustomEvent(type, { detail: data }))
  }
}

// 导出单例，供 useSSE 订阅
export const generationEmitter = new GenerationEmitter()

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

    // 检测并发写入风险
    const fileStore = useFileStore()
    if (fileStore.unsavedFiles.has(filePath)) {
      const notification = useNotificationStore()
      notification.warning(`文件有未保存的编辑，AI 生成后可能覆盖您的修改`)
    }

    _isGenerating.value = true
    _currentPrompt.value = ''
    _abortController = new AbortController()

    try {
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

      // 通过 generationEmitter → useSSE → handleEvent 统一处理 generation 事件
      // 不再直接写入 store，避免重复写入
      // 将 filePath 作为事件detail的一部分传递，以便正确更新文件
      const filePathForEmitter = filePath
      await parseSSEStream(reader, (_delta) => {
        // delta 事件由 useSSE 通过 generationEmitter 监听并处理
        // filePath 已在 closure 中，通过 emitter detail 传递
      }, (prompt) => {
        _currentPrompt.value = prompt
        editorStore.setFilePrompt(filePathForEmitter, prompt)
      }, filePathForEmitter)

      // 生成成功后保存元数据（含 user_prompt，供重新生成使用）
      const savedExtraVars = { ...(extraVars || {}) }
      if (prompt) {
        savedExtraVars.user_prompt = prompt
      }
      useFileMetaStore().saveMeta(projectId, filePath, {
        promptType: promptType || 'generate/continuation',
        extraVars: savedExtraVars,
        generatedAt: new Date().toISOString(),
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

    // 检测并发写入风险
    const fileStore = useFileStore()
    if (fileStore.unsavedFiles.has(filePath)) {
      const notification = useNotificationStore()
      notification.warning(`文件有未保存的编辑，AI 生成后可能覆盖您的修改`)
    }

    _isGenerating.value = true
    _currentPrompt.value = ''
    _abortController = new AbortController()

    try {
      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pipeline: pipelineName,
          project_id: projectId,
          target_file: filePath,
          output_mode: 'overwrite',
        }),
        signal: _abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      // 通过 generationEmitter → useSSE → handleEvent 统一处理 generation 事件
      // 不再直接写入 store，避免重复写入
      // 将 filePath 作为事件detail的一部分传递，以便正确更新文件
      const filePathForEmitter = filePath
      await parseSSEStream(reader, (_delta) => {
        // delta 事件由 useSSE 通过 generationEmitter 监听并处理
        // filePath 已在 closure 中，通过 emitter detail 传递
      }, (prompt) => {
        _currentPrompt.value = prompt
        editorStore.setFilePrompt(filePathForEmitter, prompt)
      }, filePathForEmitter)

      // 管线写入文件后，从磁盘重新加载内容到编辑器
      try {
        const fileStore = useFileStore()
        const result = await fileStore.readFile(projectId, filePathForEmitter)
        if (result?.content) {
          editorStore.loadContent(filePathForEmitter, result.content)
          // 强制标记为外部更新，触发 CodeMirror watcher 刷新编辑器
          editorStore.contentSource = 'external'
        }
      } catch {
        // 文件可能不存在或读取失败，静默忽略
      }

    } catch (e: any) {
      if (e.name !== 'AbortError') throw e
    } finally {
      _isGenerating.value = false
      _abortController = null
    }
  }

  /**
   * 解析 SSE 流，提取 delta 内容，同时通过 generationEmitter 分发事件
   * 这样 useSSE 可以统一处理所有事件，避免 SSE EventSource 和 fetch 流重复处理
   * @param onDelta 回调（已废弃，保留为空实现）
   * @param onPrompt prompt 事件回调
   * @param targetFilePath 目标文件路径，用于 generation 事件的 detail
   */
  async function parseSSEStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onDelta: (delta: string) => void,
    onPrompt?: (prompt: string) => void,
    targetFilePath?: string,
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
            if (currentEvent === 'error') {
              // 抛出错误而非仅通过 emitter
              throw new Error(parsed.message || '管线执行出错')
            }
            // 通过 generationEmitter 分发所有事件，供 useSSE 统一处理
            // 对于 generation 事件，注入 targetFilePath 以便正确更新文件
            if (currentEvent === 'generation' && targetFilePath) {
              parsed._targetFilePath = targetFilePath
            }
            generationEmitter.emit(currentEvent || 'message', parsed)
            // 原有回调逻辑保留（但 delta 写入已移除，由 useSSE 通过 emitter 处理）
            if (currentEvent === 'prompt' && parsed.prompt && onPrompt) {
              onPrompt(parsed.prompt)
            } else if ((parsed.delta || parsed.content) && onDelta) {
              onDelta(parsed.delta || parsed.content)
            }
          } catch {
            // SSR 流中包含 heartbeat 等非 JSON 行，静默跳过
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
