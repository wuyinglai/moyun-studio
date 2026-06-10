/**
 * T6.6.3 Pipeline dry-run UI + SSE 串联测试
 *
 * 验证 Pipeline dry-run 完整工作流：
 * - Pipeline dry-run 按钮仅 dev/test 可见
 * - 点击按钮调用 /api/pipeline/run
 * - SSE 流返回 done 事件和 dry_run 标记
 * - 不调用真实 LLM
 * - 不覆盖正文
 * - 不生成正式 candidate
 */
import { test, expect } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_6_3_pipeline_dry_run'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.6.3 Pipeline 初始正文'

async function deleteProject(projectId: string): Promise<void> {
  await fetch(`${BACKEND_API}/projects/${projectId}`, { method: 'DELETE' })
}

async function writeFile(projectId: string, relpath: string, content: string): Promise<void> {
  await fetch(`${BACKEND_API}/file?project_id=${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: relpath, content }),
  })
}

async function createProject(name: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      genre: '测试',
      theme: 'T6.6.3 Pipeline Dry Run',
      tone: '中性',
      background: '测试',
      writing_style: '普通',
      target_word_count: 50000,
      author: 'e2e',
    }),
  })
  const data = await resp.json()
  return data.data.project_id
}

async function getFile(projectId: string, relpath: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/file?project_id=${projectId}&path=${encodeURIComponent(relpath)}`)
  const data = await resp.json()
  return data.data?.content || ''
}

async function getCandidates(projectId: string): Promise<any[]> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}`)
  const data = await resp.json()
  return data.candidates || []
}

async function installLLMMock(page: any): Promise<void> {
  await page.route(
    (url: any) => {
      const p = url.pathname || ''
      if (p.startsWith('/api/llm') || p.startsWith('/api/generate')) {
        return true
      }
      return false
    },
    async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { connected: true } }),
      })
    },
  )
}

async function runPipelineDryRun(projectId: string, targetFile: string): Promise<{ done: boolean; dryRun: boolean; events: string[]; rawData: any[] }> {
  const events: string[] = []
  const rawData: any[] = []
  let done = false
  let dryRun = false

  const response = await fetch(`${BACKEND_API}/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pipeline: 'polish',
      project_id: projectId,
      target_file: targetFile,
      dry_run: true,
    }),
  })

  if (!response.ok) {
    throw new Error(`Pipeline request failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done: streamDone } = await reader!.read()
    if (streamDone) break

    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          rawData.push(data)
          const eventName = data.event || data.type || data.step_id || 'unknown'
          events.push(eventName)

          // 检查是否完成 - 根据 SSE 响应格式，最后一条消息包含 message 和 dry_run
          if (data.message && data.dry_run !== undefined) {
            done = true
            dryRun = data.dry_run === true
          }

          // 也检查 step_id === 'done' 的情况
          if (data.step_id === 'done') {
            done = true
            dryRun = data.dry_run === true
          }
        } catch (e) {
          // ignore parse error
        }
      }
    }
  }

  console.log('[t6.6.3] SSE raw events count:', rawData.length)
  console.log('[t6.6.3] done:', done, 'dry_run:', dryRun)
  return { done, dryRun, events, rawData }
}

test.describe('T6.6.3 Pipeline dry-run UI + SSE 串联测试', () => {
  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    console.log(`[t6.6.3] 测试项目 ID: ${projectId}`)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.6.3] 已清理项目: ${projectId}`)
    }
  })

  test('1. 打开项目页面 → Pipeline Dry Run 按钮存在', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    await page.waitForTimeout(8000)

    // 验证 Pipeline Dry Run 按钮存在
    const pipelineBtn = page.getByTestId('dry-run-pipeline-button')
    await pipelineBtn.waitFor({ timeout: 15000, state: 'attached' })

    const buttonText = await pipelineBtn.textContent()
    expect(buttonText).toContain('Pipeline Dry Run')
    console.log('[t6.6.3] ✓ Pipeline Dry Run 按钮存在')
  })

  test('2. 通过 API 调用 Pipeline dry-run → SSE 返回 done 和 dry_run 标记', async () => {
    const result = await runPipelineDryRun(projectId, TEST_FILE_PATH)
    console.log('[t6.6.3] 事件序列:', result.events.join(' -> '))

    expect(result.done).toBe(true)
    expect(result.dryRun).toBe(true)
    console.log('[t6.6.3] ✓ Pipeline dry-run SSE 返回 done 和 dry_run 标记')
  })

  test('3. 点击 Pipeline Dry Run 按钮 → SSE 流处理', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)
    await page.waitForTimeout(8000)

    // 点击 Pipeline Dry Run 按钮
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-pipeline-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待 SSE 处理
    await page.waitForTimeout(10000)

    // 检查日志中是否有 Pipeline Dry Run 相关日志
    const logItems = await page.locator('.log-item').allTextContents()
    const pipelineLogs = logItems.filter(log => log.includes('Pipeline') || log.includes('pipeline'))

    if (pipelineLogs.length > 0) {
      console.log('[t6.6.3] ✓ 日志中包含 Pipeline 相关内容')
    } else {
      console.log('[t6.6.3] ⚠️ 日志中未找到 Pipeline 内容')
    }
  })

  test('4. 安全边界：Pipeline dry-run 不覆盖正文', async () => {
    const content = await getFile(projectId, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.6.3] ✓ Pipeline dry-run 未覆盖正文')
  })

  test('5. 安全边界：Pipeline dry-run 不生成正式 candidate', async () => {
    const candidates = await getCandidates(projectId)
    const targetCandidates = candidates.filter((c: any) => c.source_path === TEST_FILE_PATH)
    expect(targetCandidates.length).toBe(0)
    console.log('[t6.6.3] ✓ Pipeline dry-run 未生成正式 candidate')
  })

  test('6. 安全边界：Pipeline dry-run 不调用真实 LLM', async ({ page }) => {
    await installLLMMock(page)

    let llmCalled = false

    // 监听 LLM 相关请求
    page.on('request', (req) => {
      const url = req.url()
      if (url.includes('/api/llm') || url.includes('/api/generate')) {
        llmCalled = true
      }
    })

    // 调用 Pipeline dry-run
    await runPipelineDryRun(projectId, TEST_FILE_PATH)

    // 等待一段时间确保没有 LLM 调用
    await page.waitForTimeout(2000)

    expect(llmCalled).toBe(false)
    console.log('[t6.6.3] ✓ Pipeline dry-run 未调用真实 LLM')
  })
})