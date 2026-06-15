/**
 * T6.5.4 项目创建 / 项目打开 / 项目列表真实 E2E 测试
 *
 * 覆盖内容：
 *  1) 主页加载 + "打开项目" 弹窗显示真实项目列表
 *  2) 通过 UI 创建项目（Modal → 填写 → 提交）→ 真实 POST /api/projects
 *  3) 创建成功后自动跳转到 /project/{id} → Professional 工作台显示
 *  4) 工作台中文件树渲染
 *  5) 从项目页重新打开"打开项目"弹窗 → 验证测试项目在列表中
 *  6) 清理：DELETE /api/projects/{id}
 *
 * 安全边界：
 *  - 项目名称使用 __e2e_t6_5_4_* 前缀
 *  - 测试结束后 DELETE /api/projects/{id} 清理
 *  - 不调用 llm / generate 等接口
 */
import { test, expect, type Page, type APIRequestContext } from '@playwright/test'
// ── Gate：需要真实后端 ──────────────────────────────────────────
const REAL_BACKEND_AVAILABLE = process.env.MOYUN_E2E_REAL_BACKEND === '1'

import { dismissViteOverlay } from './helpers/e2eUtils'

// ======================== 常量 ========================
const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_5_4_project_entry'
const TEST_GENRE = '都市'

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

async function deleteProjectViaApi(request: APIRequestContext, projectId: string): Promise<void> {
  await apiCall(request, 'DELETE', `/projects/${projectId}`)
}

async function installLLMMock(page: Page): Promise<void> {
  // Mock 所有 LLM / 生成相关接口，返回 connected=true 确保项目创建可以继续
  // 仅保留 File/Project/Tree/SSE 走真实后端
  await page.route(
    (url) => {
      const p = url.pathname || ''
      if (p.startsWith('/api/llm') || p.startsWith('/api/generate') || p.startsWith('/api/sse')) {
        return true
      }
      return false
    },
    async (route) => {
      const rawUrl = route.request().url()
      const reqUrl = typeof rawUrl === 'string' ? rawUrl : (rawUrl?.toString() ?? '')
      if (reqUrl.includes('/llm/status') || reqUrl.includes('/llm/config')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { connected: true, provider: 'mock', model: 'mock' } }),
        })
      } else if (reqUrl.includes('/sse')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
          body: 'event: connected\ndata: {"timestamp":0}\n\n',
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { connected: false }, message: 'mock' }),
        })
      }
    },
  )
}

/** 强制设置 llmStore.isConnected = true（Pinia store 直接写值，用于绕过 LLM 未配置时的创建限制） */
async function forceLLMConnected(page: Page): Promise<void> {
  await page.evaluate(() => {
    try {
      const pinia = (window as any).__pinia__
      if (pinia?.state?.value?.llm) {
        pinia.state.value.llm.isConnected = true
        if (pinia.state.value.llm.connected !== undefined) {
          pinia.state.value.llm.connected = true
        }
      }
    } catch {
      // ignore
    }
  })
}

// ======================== 测试套件 ========================
test.describe('T6.5.4 项目创建 / 打开 / 列表真实 E2E', () => {
  test.skip(
    !REAL_BACKEND_AVAILABLE,
    'MOYUN_E2E_REAL_BACKEND=1 未设置，跳过需要真实后端的测试',
  )

  let projectId: string
  let cleaned = false

  // ─── 前置：创建测试项目（供"打开"流程使用）─────────────────────
  test.beforeAll(async ({ request }) => {
    // 1) 验证后端可达
    const health = await apiCall(request, 'GET', '/projects')
    expect(health.ok, `后端 /api/projects 应返回 2xx (实际 ${health.status})`).toBeTruthy()

    // 2) 通过真实 API 预先创建一个项目（用于测试"打开"流程）
    const r = await apiCall(request, 'POST', '/projects', {
      name: TEST_PROJECT_NAME,
      genre: TEST_GENRE,
      theme: '测试',
      tone: '中性',
      background: 'T6.5.4 E2E',
      writing_style: '普通',
      target_word_count: 50000,
      author: 'e2e',
      scene_target_chars: 800,
      scenes_per_chapter: 5,
      chapters_per_volume: 12,
    })
    expect(r.ok || r.status === 201, `创建测试项目应成功 (status=${r.status})`).toBeTruthy()
    const pid = r.body?.data?.project_id
    expect(pid, '应返回 project_id').toBeTruthy()
    projectId = pid
    console.log(`[t6.5.4] 预创建项目 ID: ${projectId}`)

    // 3) 确认项目可被 GET /api/projects 列出
    const list = await apiCall(request, 'GET', '/projects')
    expect(list.ok).toBeTruthy()
    const projects: any[] = list.body?.data?.projects || []
    const found = projects.find((p) => p.project_id === projectId || p.id === projectId)
    expect(found, '项目应出现在 GET /api/projects 列表中').toBeTruthy()
  })

  test.afterAll(async ({ request }) => {
    if (projectId && !cleaned) {
      await deleteProjectViaApi(request, projectId)
      cleaned = true
      console.log(`[t6.5.4] 已清理项目: ${projectId}`)
    }
  })

  // ─── Test 1：打开"打开项目"弹窗，显示真实项目列表 ────────────
  test('1. 主页 → "打开项目" 弹窗显示真实项目列表', async ({ page }) => {
    await installLLMMock(page)

    // 打开主页
    await page.goto('/')
    await dismissViteOverlay(page)
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })

    // 点击 AppHeader 中的"打开项目"按钮
    await page.getByTitle('打开项目').click()

    // 等待 ant-modal 打开
    await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 })

    // 等待项目列表容器出现（open-project-modal 是模态框内包裹内容的 div）
    await expect(page.locator('.open-project-modal')).toBeVisible({ timeout: 5000 })

    // 等待 project-card 或 ant-list-item 出现（列表项）
    const listItem = page.locator('.ant-list-item').first()
    await expect(listItem).toBeVisible({ timeout: 15000 })

    // 确认测试项目在列表中
    await expect(
      page.locator('.project-card').filter({ hasText: TEST_PROJECT_NAME }),
    ).toBeVisible({ timeout: 5000 })
  })

  // ─── Test 2：点击项目卡片 → 进入 Professional 工作台 → 文件树加载 ────
  test('2. 在打开项目弹窗中双击项目 → 跳转到 /project/{id} → file-tree', async ({ page }) => {
    await installLLMMock(page)

    // 打开主页
    await page.goto('/')
    await dismissViteOverlay(page)
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })

    // 打开"打开项目"弹窗
    await page.getByTitle('打开项目').click()
    await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 })
    await expect(
      page.locator('.project-card').filter({ hasText: TEST_PROJECT_NAME }),
    ).toBeVisible({ timeout: 15000 })

    // 双击项目卡片触发 openProject（modal 会关闭，router.push() 被调用）
    const targetCard = page.locator('.project-card').filter({ hasText: TEST_PROJECT_NAME })
    await targetCard.dblclick()

    // Vue Router pushState + beforeEnter 导航完成后，AppLayout（含 file-tree）才会渲染
    // file-tree 出现 = 路由成功变为 /project/{id} 的充分证明（无需额外检查 URL）
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })
  })

  // ─── Test 3：从主入口通过 UI 创建新项目（Modal → 填写 → 提交）──────────
  test('3. 主页 → 新建项目 Modal → 填写 → 提交 → 跳转 /project/{id} → file-tree', async ({ page }) => {
    await installLLMMock(page)

    // 打开主页
    await page.goto('/')
    await dismissViteOverlay(page)
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })

    // 强制设置 llmStore.isConnected = true（绕过 LLM 未配置时的创建限制）
    await forceLLMConnected(page)

    // 点击"新建项目"按钮
    await page.getByTitle('新建项目').click()

    // 等待创建项目 Modal 出现
    await expect(page.getByTestId('create-project-name-input')).toBeVisible({ timeout: 5000 })

    // 填写项目名称（加时间戳避免重复）
    const uniqueName = `${TEST_PROJECT_NAME}-${Date.now()}`
    await page.getByTestId('create-project-name-input').fill(uniqueName)

    // 选择题材：都市
    await page.locator('.ant-radio-button-wrapper', { hasText: TEST_GENRE }).first().click()

    // 点击提交
    await page.getByTestId('create-project-submit').click()

    // 等待跳转到 /project/{id}（新创建的项目会自动跳转）
    await page.waitForURL(/\/project\/[a-z0-9]+$/, { timeout: 20000 })

    // 等待 file-tree 加载
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })

    // 从 URL 中提取 projectId 并清理这个新创建的项目
    const url = page.url()
    const match = url.match(/\/project\/([^/]+)/)
    expect(match, 'URL 应包含 /project/{id}').toBeTruthy()
    const createdId = match![1]
    console.log(`[t6.5.4] 通过 UI 创建的项目 ID: ${createdId}`)

    // 清理这个新创建的项目
    await deleteProjectViaApi(page.request, createdId)
    console.log(`[t6.5.4] 已清理 UI 创建的项目: ${createdId}`)
  })

  // ─── Test 4：进入工作台后，再次打开"打开项目"弹窗 → 验证预创建项目在列表 ───
  test('4. /project/{id} 工作台 → 打开"打开项目"弹窗 → 预创建项目在列表中', async ({ page }) => {
    await installLLMMock(page)

    // 直接导航到预创建项目的页面
    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })

    // 在工作台中点击 AppHeader 的"打开项目"按钮
    await page.getByTitle('打开项目').click()

    // 等待模态框打开
    await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.open-project-modal')).toBeVisible({ timeout: 5000 })

    // 等待列表项出现
    await expect(page.locator('.ant-list-item').first()).toBeVisible({ timeout: 15000 })

    // 验证预创建项目在列表中
    await expect(
      page.locator('.project-card').filter({ hasText: TEST_PROJECT_NAME }),
    ).toBeVisible({ timeout: 5000 })
  })

  // ─── Test 5：清理：DELETE /api/projects/{id} 后项目不再出现 ───
  test('5. 清理：DELETE 后 GET /api/projects 不再包含该项目', async ({ request }) => {
    await deleteProjectViaApi(request, projectId)
    cleaned = true

    const list = await apiCall(request, 'GET', '/projects')
    expect(list.ok).toBeTruthy()
    const projects: any[] = list.body?.data?.projects || []
    const found = projects.find((p) => p.project_id === projectId || p.id === projectId)
    expect(found, `清理后项目 ${projectId} 不应出现在 GET /api/projects 列表中`).toBeFalsy()
  })
})
