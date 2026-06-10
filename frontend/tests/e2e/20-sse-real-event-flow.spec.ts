/**
 * T6.5.5 SSE / file.updated / candidate 事件真实跨进程 E2E 测试
 *
 * 验证：
 *  1) 真实后端发布 file.updated 事件后，浏览器能通过 EventSource 收到
 *  2) 前端收到事件后能正确响应
 *  3) SSE 连接状态正常
 *
 * 安全边界：
 *  - 项目名称使用 __e2e_t6_5_5_* 前缀
 *  - 测试结束后 DELETE /api/projects/{id} 清理
 *  - 不调用 llm / generate 等接口
 */
import { test, expect, type Page, type APIRequestContext } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_5_5_sse'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.5.5 初始内容'
const EXTERNAL_UPDATE_CONTENT = 'T6.5.5 外部更新内容'

async function apiCall(
  request: APIRequestContext,
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  data?: unknown,
): Promise<{ status: number; ok: boolean; body: any; raw: string }> {
  const url = `${BACKEND_API}${path}`
  let resp
  if (method === 'GET') {
    resp = await request.get(url)
  } else if (method === 'DELETE') {
    resp = await request.delete(url)
  } else if (data) {
    resp = await request.post(url, { data })
  } else {
    resp = await request.post(url)
  }
  const raw = await resp.text()
  let body: any = raw
  try {
    body = JSON.parse(raw)
  } catch {
    // 保持 raw
  }
  return { status: resp.status(), ok: resp.ok(), body, raw }
}

async function deleteProjectViaApi(request: APIRequestContext, projectId: string): Promise<void> {
  await apiCall(request, 'DELETE', `/projects/${projectId}`)
}

async function writeFileViaApi(
  request: APIRequestContext,
  projectId: string,
  relpath: string,
  content: string,
): Promise<{ status: number; ok: boolean; body: any }> {
  return apiCall(request, 'POST', `/file?project_id=${projectId}`, { path: relpath, content })
}

async function installLLMMock(page: Page): Promise<void> {
  await page.route(
    (url) => {
      const p = url.pathname || ''
      if (p.startsWith('/api/llm') || p.startsWith('/api/generate')) {
        return true
      }
      return false
    },
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { connected: true } }),
      })
    },
  )
}

test.describe('T6.5.5 SSE 真实事件流 E2E', () => {
  let projectId: string
  let cleaned = false

  test.beforeAll(async ({ request }) => {
    const r = await apiCall(request, 'POST', '/projects', {
      name: TEST_PROJECT_NAME,
      genre: '测试',
      theme: 'T6.5.5 SSE',
      tone: '中性',
      background: '测试',
      writing_style: '普通',
      target_word_count: 50000,
      author: 'e2e',
    })
    expect(r.ok).toBeTruthy()
    projectId = r.body?.data?.project_id
    expect(projectId).toBeTruthy()
    console.log(`[t6.5.5] 测试项目 ID: ${projectId}`)

    await apiCall(request, 'POST', `/file?project_id=${projectId}`, {
      path: TEST_FILE_PATH,
      content: INITIAL_CONTENT,
    })
  })

  test.afterAll(async ({ request }) => {
    if (projectId && !cleaned) {
      await deleteProjectViaApi(request, projectId)
      cleaned = true
      console.log(`[t6.5.5] 已清理项目: ${projectId}`)
    }
  })

  // ─── Test 1：验证 SSE 连接建立 ────────────
  test('1. 打开项目页面 → SSE 连接成功建立 → 无 SSE 错误', async ({ page }) => {
    await installLLMMock(page)

    const errors: string[] = []
    let sseConnected = false
    let sseEvents: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
        console.log('[CONSOLE ERROR]', msg.text())
      }
      if (msg.type() === 'log') {
        const text = msg.text()
        if (text.includes('SSE') || text.includes('connected')) {
          console.log('[SSE LOG]', text)
        }
      }
    })

    // 监听 SSE 事件
    page.on('response', async (response) => {
      const url = response.url()
      if (url.includes('/api/sse')) {
        console.log('[SSE RESPONSE]', url, response.status())
        if (response.status() === 200) {
          sseConnected = true
        }
      }
    })

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.cm-content')).toContainText(INITIAL_CONTENT, { timeout: 10000 })

    const sseErrors = errors.filter((e) => e.includes('SSE') || e.includes('EventSource') || e.includes('/api/sse'))
    expect(sseErrors).toEqual([], `不应有 SSE 相关错误，但发现: ${sseErrors.join(', ')}`)
    expect(sseConnected).toBe(true, 'SSE 连接应成功建立')
  })

  // ─── Test 2：后端发布 file.updated 事件，前端能收到并响应 ────────────
  test('2. 后端 API 写入文件触发 file.updated → 前端收到事件', async ({ page, request }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.cm-content')).toContainText(INITIAL_CONTENT, { timeout: 10000 })

    const receivedEvents: { type: string; data: any }[] = []
    
    // 通过 evaluate 监听前端事件
    await page.evaluate(() => {
      ;(window as any)._sseTestEvents = []
    })

    // 设置事件监听
    await page.evaluate(() => {
      const sseService = (window as any).sseService
      if (sseService) {
        sseService.on('file-updated', (data: any) => {
          ;(window as any)._sseTestEvents.push({ type: 'file-updated', data })
          console.log('[SSE TEST] file-updated received:', data)
        })
      }
    })

    // 通过 API 写入文件（这会触发 file.updated 事件）
    console.log('[t6.5.5] 通过 API 写入文件，触发 file.updated 事件...')
    const writeResp = await writeFileViaApi(request, projectId, TEST_FILE_PATH, EXTERNAL_UPDATE_CONTENT)
    expect(writeResp.ok || writeResp.status === 200).toBeTruthy()
    console.log('[t6.5.5] API 写入完成，等待前端收到事件...')

    // 等待事件被接收
    await page.waitForFunction(
      () => {
        const events = (window as any)._sseTestEvents || []
        return events.some((e: any) => e.type === 'file-updated')
      },
      { timeout: 15000 },
    )

    // 获取收到的事件
    const events = await page.evaluate(() => (window as any)._sseTestEvents || [])
    console.log('[t6.5.5] 前端收到的事件:', JSON.stringify(events, null, 2))
    
    const fileUpdatedEvent = events.find((e: any) => e.type === 'file-updated')
    expect(fileUpdatedEvent).toBeTruthy()
    expect(fileUpdatedEvent.data.path).toBeDefined()
    console.log('[t6.5.5] ✓ file-updated 事件已成功收到')
  })

  // ─── Test 3：验证 SSE Heartbeat 机制 ────────────
  test('3. SSE heartbeat 机制正常工作', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })

    // 等待至少一个 heartbeat 周期（15秒）
    await page.waitForTimeout(16000)

    // 检查是否有连接断开错误
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    await page.waitForTimeout(2000)

    const heartbeatErrors = errors.filter((e) => e.includes('heartbeat') || e.includes('disconnect'))
    expect(heartbeatErrors).toEqual([], `不应有 heartbeat 错误，但发现: ${heartbeatErrors.join(', ')}`)
  })

  // ─── Test 4：清理验证 ────────────
  test('4. 清理：DELETE /api/projects/{id} 后项目不再出现', async ({ request }) => {
    await deleteProjectViaApi(request, projectId)
    cleaned = true

    const list = await apiCall(request, 'GET', '/projects')
    expect(list.ok).toBeTruthy()
    const projects: any[] = list.body?.data?.projects || []
    const found = projects.find((p: any) => p.project_id === projectId || p.id === projectId)
    expect(found).toBeFalsy()
  })
})
