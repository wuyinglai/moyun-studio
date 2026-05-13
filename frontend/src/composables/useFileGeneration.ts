import { ref } from 'vue'
import { useEditorStore } from '@/stores/editor'

export function useFileGeneration() {
  const editorStore = useEditorStore()
  const isGenerating = ref(false)
  const currentPrompt = ref('')
  const progress = ref({ current: 0, total: 0 })
  let abortController: AbortController | null = null

  /**
   * 对指定文件进行流式生成
   */
  async function generateToFile(
    projectId: string,
    filePath: string,
    prompt?: string,
  ) {
    if (isGenerating.value) return

    isGenerating.value = true
    currentPrompt.value = prompt || ''
    abortController = new AbortController()

    try {
      // 确保编辑器已打开该文件
      editorStore.setCurrentFile(filePath)

      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          file_path: filePath,
          prompt_type: 'generate/chapter',
          extra_vars: prompt ? { user_prompt: prompt } : {},
          mode: 'append',
          stream: true,
        }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      await parseSSEStream(reader, (delta) => {
        editorStore.appendContent(delta)
      })

      isGenerating.value = false
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // 用户取消，不报错
      } else {
        throw e
      }
    } finally {
      isGenerating.value = false
      abortController = null
    }
  }

  function cancelGeneration() {
    abortController?.abort()
    isGenerating.value = false
  }

  /**
   * 解析 SSE 流，提取 delta 内容
   */
  async function parseSSEStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onDelta: (delta: string) => void,
  ): Promise<void> {
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6))
            if (parsed.delta) {
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
    isGenerating,
    currentPrompt,
    progress,
    generateToFile,
    cancelGeneration,
  }
}
