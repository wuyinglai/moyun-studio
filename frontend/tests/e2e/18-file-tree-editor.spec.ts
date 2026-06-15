/**
 * T6.5.3 文件树 + 编辑器 + File API 真实联调 E2E 测试
 *
 * 覆盖内容：
 *  1) 真实后端创建项目 & 写入测试文件
 *  2) Professional 项目页 / 文件页加载 + 文件树渲染
 *  3) MarkdownEditor 渲染 + 初始内容展示
 *  4) 编辑器修改内容 + Ctrl+S 保存 → 通过真实后端 GET /api/file 校验
 *  5) 页面刷新后内容仍一致
 *  6) FILE_CONFLICT：外部修改后用旧 expected_hash 保存应被拒绝（409 / FILE_CONFLICT）
 *
 * 安全边界：
 *  - 项目名称使用 __e2e_t6_5_3_* 前缀
 *  - 测试结束后 DELETE /api/projects/{id} 清理
 *  - 不调用 llm / generate 等接口
 */
import { test, expect, type Page, type APIRequestContext } from '@playwright/test'
// ── Gate：需要真实后端 ──────────────────────────────────────────
const REAL_BACKEND_AVAILABLE = process.env.MOYUN_E2E_REAL_BACKEND === '1'

import { dismissViteOverlay } from './helpers/e2eUtils'

// ======================== 常量 ========================
const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_FILE = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.5.3 初始内容'
const EDITED_CONTENT = 'T6.5.3 修改后的内容'
const EXTERNAL_CONTENT = 'T6.5.3 外部修改内容'
const TEST_PROJECT_NAME = '__e2e_t6_5_3_file_editor'

// ======================== 工具函数 ========================
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

async function createProject(request: APIRequestContext): Promise<string> {
  const r = await apiCall(request, 'POST', '/projects', {
    name: TEST_PROJECT_NAME,
    genre: '都市',
    theme: '测试',
    tone: '中性',
    background: 'T6.5.3 E2E',
    writing_style: '普通',
    target_word_count: 50000,
    author: 'e2e',
    scene_target_chars: 800,
    scenes_per_chapter: 5,
    chapters_per_volume: 12,
  })
  expect(r.ok || r.status === 201, `创建项目应成功 (status=${r.status})`).toBeTruthy()
  const pid = r.body?.data?.project_id
  expect(pid, `返回 project_id`).toBeTruthy()
  return pid
}

async function writeFileViaApi(
  request: APIRequestContext,
  projectId: string,
  relpath: string,
  content: string,
  opts?: { expected_mtime?: number; expected_hash?: string },
): Promise<{ status: number; ok: boolean; body: any }> {
  const body: any = { path: relpath, content }
  if (opts?.expected_mtime != null) body.expected_mtime = opts.expected_mtime
  if (opts?.expected_hash != null) body.expected_hash = opts.expected_hash
  return apiCall(request, 'POST', `/file?project_id=${projectId}`, body)
}

async function readFileViaApi(
  request: APIRequestContext,
  projectId: string,
  relpath: string,
): Promise<{ content: string; mtime?: number; hash?: string }> {
  const r = await apiCall(
    request,
    'GET',
    `/file?project_id=${projectId}&path=${encodeURIComponent(relpath)}`,
  )
  expect(r.ok, `GET /api/file(${relpath}) 应成功 (status=${r.status})`).toBeTruthy()
  const d = r.body?.data
  return { content: String(d?.content ?? ''), mtime: d?.mtime, hash: d?.hash }
}

async function deleteProjectViaApi(request: APIRequestContext, projectId: string): Promise<void> {
  await apiCall(request, 'DELETE', `/projects/${projectId}`)
}

async function waitForEditorContent(page: Page, expected: string, timeoutMs = 30000): Promise<void> {
  // 等待 data-testid="codemirror-container" 可见，然后检查 cm-content 中的文本
  await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: timeoutMs })
  // CodeMirror 渲染文本节点位于 .cm-content / .cm-line 内；使用 getByText 做轮询等待
  await expect(page.locator('.cm-content')).toContainText(expected, { timeout: timeoutMs })
}

// ======================== 测试套件 ========================
test.describe('T6.5.3 文件树 + 编辑器 + File API 真实联调', () => {
  test.skip(
    !REAL_BACKEND_AVAILABLE,
    'MOYUN_E2E_REAL_BACKEND=1 未设置，跳过需要真实后端的测试',
  )

  let projectId: string
  let cleaned = false

  test.beforeAll(async ({ request }) => {
    // 1) 验证后端可达
    const health = await apiCall(request, 'GET', '/projects')
    expect(health.ok, `后端 /api/projects 应返回 2xx (实际 ${health.status})`).toBeTruthy()

    // 2) 创建测试项目
    projectId = await createProject(request)
    console.log(`[t6.5.3] 测试项目 ID: ${projectId}`)

    // 3) 通过真实 File API 写入初始文件
    const write = await writeFileViaApi(request, projectId, TEST_FILE, INITIAL_CONTENT)
    expect(write.ok || write.status === 200 || write.status === 201, '初始文件写入应成功').toBeTruthy()

    // 4) 立刻回读确认落地
    const check = await readFileViaApi(request, projectId, TEST_FILE)
    expect(check.content, '初始写入后回读应包含 INITIAL_CONTENT').toContain(INITIAL_CONTENT)
  })

  test.afterAll(async ({ request }) => {
    if (projectId && !cleaned) {
      await deleteProjectViaApi(request, projectId)
      cleaned = true
      console.log(`[t6.5.3] 已清理项目: ${projectId}`)
    }
  })

  test('1. 文件页加载成功：file-tree + codemirror-container 均可见', async ({ page }) => {
    await page.goto(`/project/${projectId}/file/${TEST_FILE}`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 30000 })
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 30000 })
  })

  test('2. 编辑器显示初始内容', async ({ page }) => {
    await page.goto(`/project/${projectId}/file/${TEST_FILE}`)
    await dismissViteOverlay(page)
    await waitForEditorContent(page, INITIAL_CONTENT)
  })

  test('3. 修改正文 + Ctrl+S 保存 → 后端 GET /api/file 验证内容一致', async ({ page, request }) => {
    await page.goto(`/project/${projectId}/file/${TEST_FILE}`)
    await dismissViteOverlay(page)
    await waitForEditorContent(page, INITIAL_CONTENT)

    // 聚焦 → 全选 → 输入新内容
    const cm = page.locator('.cm-content').first()
    await cm.click()
    await page.keyboard.press('Control+a')
    await page.keyboard.type(EDITED_CONTENT)
    await expect(cm).toContainText(EDITED_CONTENT, { timeout: 15000 })

    // Ctrl+S 保存
    await page.keyboard.press('Control+s')
    await page.waitForTimeout(2500)

    // 通过真实后端 GET /api/file 重新读取，确认内容一致
    const after = await readFileViaApi(request, projectId, TEST_FILE)
    expect(after.content, '保存后后端读回的内容应包含 EDITED_CONTENT').toContain(EDITED_CONTENT)
  })

  test('4. 页面刷新后编辑器仍一致', async ({ page, request }) => {
    // 先确认后端已有 EDITED_CONTENT
    const saved = await readFileViaApi(request, projectId, TEST_FILE)
    expect(saved.content).toContain(EDITED_CONTENT)

    // 重新打开页面并校验
    await page.goto(`/project/${projectId}/file/${TEST_FILE}`)
    await dismissViteOverlay(page)
    await waitForEditorContent(page, EDITED_CONTENT)
  })

  test('5. FILE_CONFLICT：外部写入后，用旧 expected_hash 保存应被拒绝，内容不被覆盖', async ({
    request,
  }) => {
    // 读当前文件，拿到 hash / mtime
    const current = await readFileViaApi(request, projectId, TEST_FILE)
    expect(current.hash, '当前文件应有 hash').toBeTruthy()

    // 外部写入 EXTERNAL_CONTENT
    const extWrite = await writeFileViaApi(request, projectId, TEST_FILE, EXTERNAL_CONTENT)
    expect(extWrite.ok || extWrite.status === 200 || extWrite.status === 201, '外部写入应成功').toBeTruthy()

    // 立刻再读回确认外部内容已生效
    const afterExt = await readFileViaApi(request, projectId, TEST_FILE)
    expect(afterExt.content, '外部写入后应读到 EXTERNAL_CONTENT').toContain(EXTERNAL_CONTENT)

    // 用旧的 expected_hash 再次写入（模拟冲突）
    const conflict = await writeFileViaApi(request, projectId, TEST_FILE, '试图用旧 hash 覆盖', {
      expected_hash: current.hash,
    })
    const isConflict =
      conflict.status === 409 || conflict.body?.error?.code === 'FILE_CONFLICT'
    expect(isConflict, `使用旧 expected_hash 保存应返回 409 / FILE_CONFLICT (实际 status=${conflict.status})`).toBe(true)

    // 内容应保持外部修改，未被覆盖
    const finalContent = await readFileViaApi(request, projectId, TEST_FILE)
    expect(finalContent.content, '冲突被拒绝后，文件内容仍应为 EXTERNAL_CONTENT').toContain(EXTERNAL_CONTENT)
    expect(finalContent.content, '冲突被拒绝后，文件不应被污染').not.toContain('试图用旧 hash 覆盖')
  })

  test('6. 清理：DELETE /api/projects/{id} 后访问该项目 tree 应失败', async ({ request }) => {
    await deleteProjectViaApi(request, projectId)
    cleaned = true

    const tree = await apiCall(request, 'GET', `/tree?project_id=${projectId}`)
    const gone = !tree.ok || tree.status === 404 || tree.status === 400 || tree.status === 500
    expect(gone, '项目删除后 GET /api/tree 应失败').toBe(true)
  })
})
