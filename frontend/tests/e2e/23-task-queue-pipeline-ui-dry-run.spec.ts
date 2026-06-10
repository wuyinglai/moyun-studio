/**
 * T6.5.8 Pipeline / TaskQueue dry-run 前端可见性 E2E 测试
 *
 * 验证：
 * 1. TaskQueue dry-run 任务通过浏览器 API 提交成功
 * 2. Pipeline dry-run SSE 事件流可观测
 * 3. dry-run 安全边界验证
 *
 * 注意：前端 UI 没有 dry_run 参数入口，
 * 本测试验证"浏览器内 API → 后端 dry-run → 任务可见"链路。
 */
import { test, expect, type Page } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

// 使用 Vite proxy 时用 '/api'，直接后端时用 'http://127.0.0.1:8000/api'
const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_5_8_ui_dry_run'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.5.8 初始内容'

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
      theme: 'T6.5.8 UI dry-run',
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

test.describe('T6.5.8 Pipeline / TaskQueue dry-run 前端可见性 E2E', () => {
  let projectId: string
  let cleaned = false

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    console.log(`[t6.5.8] 测试项目 ID: ${projectId}`)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
  })

  test.afterAll(async () => {
    if (projectId && !cleaned) {
      await deleteProject(projectId)
      cleaned = true
      console.log(`[t6.5.8] 已清理项目: ${projectId}`)
    }
  })

  // ─── Test 1：TaskQueue dry-run 任务可见性 ────────────
  test('1. 提交 dry-run 任务 → 任务状态可查询', async ({ page }) => {
    await installLLMMock(page)

    // 打开项目页面（验证基础加载）
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })

    // 通过浏览器内 fetch 提交 dry-run 任务
    const apiBase = BACKEND_API
    const taskResult = await page.evaluate(async ({ pid, apiBase }) => {
      const resp = await fetch(`${apiBase}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_category: 'generate',
          template_type: 'chapter',
          project_id: pid,
          variables: {},
          dry_run: true,
        }),
      })
      return resp.json()
    }, { pid: projectId, apiBase })

    expect(taskResult.success).toBe(true)
    expect(taskResult.data.task_id).toBeTruthy()
    const taskId = taskResult.data.task_id
    console.log(`[t6.5.8] 提交 dry-run 任务 ID: ${taskId}`)

    // 等待任务执行完成
    await page.waitForTimeout(5000)

    // 验证任务状态可查询
    const taskDetail = await page.evaluate(async ({ tid, apiBase }) => {
      const resp = await fetch(`${apiBase}/tasks/${tid}`)
      return resp.json()
    }, { tid: taskId, apiBase: BACKEND_API })

    expect(taskDetail.success).toBe(true)
    expect(taskDetail.data.task_id).toBe(taskId)
    expect(taskDetail.data.status).toBeDefined()
    console.log(`[t6.5.8] 任务状态: ${taskDetail.data.status}`)
  })

  // ─── Test 2：Pipeline dry-run SSE 事件 ────────────
  test('2. Pipeline dry-run SSE 事件流可观测', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })

    // 触发 Pipeline dry-run
    const pipelineResult = await page.evaluate(async ({ pid, filePath, apiBase }) => {
      const resp = await fetch(`${apiBase}/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pipeline: 'generate',
          project_id: pid,
          target_file: filePath,
          output_mode: 'write_scene',
          dry_run: true,
        }),
      })
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      let done = false
      let data = ''
      while (!done) {
        const { value, done: d } = await reader!.read()
        done = d
        if (value) {
          data += decoder.decode(value, { stream: !done })
        }
      }
      return { success: resp.ok, events: data }
    }, { pid: projectId, filePath: TEST_FILE_PATH, apiBase: BACKEND_API })

    expect(pipelineResult.success).toBe(true)
    expect(pipelineResult.events).toBeTruthy()

    // 解析 SSE 事件
    const eventsText = pipelineResult.events as string
    const eventLines = eventsText.split('\n').filter(l => l.startsWith('data:'))
    console.log(`[t6.5.8] Pipeline SSE 事件: ${eventLines.length} 个`)
    expect(eventLines.length).toBeGreaterThan(0)
  })

  // ─── Test 3：安全边界验证 ────────────
  test('3. dry-run 不覆盖正文', async () => {
    // 验证 dry-run 后文件内容未变（通过后端 API 直接读取）
    const content = await getFile(projectId, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.5.8] ✓ 正文未被覆盖')
  })

  // ─── Test 4：清理验证 ────────────
  test('4. 清理：DELETE 项目后不再出现', async () => {
    const tempPid = await createProject('__e2e_t6_5_8_temp')
    expect(tempPid).toBeTruthy()

    await deleteProject(tempPid)
    console.log(`[t6.5.8] 临时项目已删除: ${tempPid}`)

    const listResp = await fetch(`${BACKEND_API}/projects`)
    const listData = await listResp.json()
    const found = listData.data?.projects?.find((p: any) => p.project_id === tempPid)
    expect(found).toBeFalsy()
    console.log('[t6.5.8] ✓ 项目已清理')
  })
})
