/**
 * T6.6.0 Professional 主流程安全 E2E 最小串联测试
 *
 * 验证完整安全链路：
 * 项目创建 → 页面打开 → 文件编辑 → dry-run 任务 → 安全边界验证
 *
 * 安全边界：
 * - 不调用真实 LLM
 * - 不覆盖正文
 * - 不生成正式 candidate
 * - 测试完成后清理
 */
import { test, expect } from '@playwright/test'
// ── Gate：需要真实后端 ──────────────────────────────────────────
const REAL_BACKEND_AVAILABLE = process.env.MOYUN_E2E_REAL_BACKEND === '1'

import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_6_professional_safe_flow'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.6.0 初始正文'

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
      theme: 'T6.6.0 Professional Safe Flow',
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

test.describe('T6.6.0 Professional 主流程安全 E2E', () => {
  test.skip(
    !REAL_BACKEND_AVAILABLE,
    'MOYUN_E2E_REAL_BACKEND=1 未设置，跳过需要真实后端的测试',
  )

  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    console.log(`[t6.6.0] 测试项目 ID: ${projectId}`)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.6.0] 已清理项目: ${projectId}`)
    }
  })

  test('1. 项目页面可打开 → 文件树可见', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 验证文件树可见
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })
    console.log('[t6.6.0] ✓ 文件树可见')
  })

  test('2. 编辑器可见 → 文件内容可读取', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 验证编辑器可见
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })

    // 验证内容显示
    await expect(page.locator('.cm-content')).toContainText(INITIAL_CONTENT, { timeout: 10000 })
    console.log('[t6.6.0] ✓ 编辑器可见，内容正确')
  })

  test('3. ExecutionPanel 可见 → dry-run 按钮存在', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(8000)

    // 验证 dry-run 按钮存在（开发模式）
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await dryRunButton.waitFor({ timeout: 15000, state: 'attached' })
    
    const buttonText = await dryRunButton.textContent()
    expect(buttonText).toContain('Dry Run')
    console.log('[t6.6.0] ✓ dry-run 按钮存在')
  })

  test('4. 点击 dry-run 按钮 → 任务创建成功', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(5000)

    // 点击 dry-run 按钮
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-task-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待任务创建
    await page.waitForTimeout(5000)

    // 通过 API 查询任务
    const taskList = await page.evaluate(async ({ apiBase }) => {
      const resp = await fetch(`${apiBase}/tasks`)
      const data = await resp.json()
      return data.data?.tasks || []
    }, { apiBase: BACKEND_API })

    expect(taskList.length).toBeGreaterThan(0)
    console.log(`[t6.6.0] ✓ 任务列表包含 ${taskList.length} 个任务`)
  })

  test('5. 安全边界验证：正文未被覆盖', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 点击 dry-run 按钮
    await page.waitForTimeout(5000)
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-task-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待任务完成
    await page.waitForTimeout(8000)

    // 验证文件内容未变
    const content = await getFile(projectId, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.6.0] ✓ 正文未被覆盖')
  })

  test('6. 安全边界验证：未生成正式 candidate', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 点击 dry-run 按钮
    await page.waitForTimeout(5000)
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-task-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待任务完成
    await page.waitForTimeout(5000)

    // 验证没有生成 candidate
    const candidatesResp = await page.evaluate(async ({ pid, apiBase }) => {
      const resp = await fetch(`${apiBase}/candidates?project_id=${pid}`)
      return resp.json()
    }, { pid: projectId, apiBase: BACKEND_API })

    if (candidatesResp.success && candidatesResp.data?.candidates) {
      const newCandidates = candidatesResp.data.candidates.filter((c: any) =>
        c.source_path === TEST_FILE_PATH
      )
      expect(newCandidates.length).toBe(0)
      console.log('[t6.6.0] ✓ 未生成正式 candidate')
    }
  })
})
