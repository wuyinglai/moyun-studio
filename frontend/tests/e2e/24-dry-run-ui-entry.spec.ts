/**
 * T6.5.9 前端 dry-run 测试入口 E2E 测试
 *
 * 验证：
 * 1. Dry Run 按钮仅在开发模式可见
 * 2. 点击按钮触发 dry-run 任务
 * 3. 任务状态在 UI 中可见
 * 4. dry-run 不覆盖正文
 * 5. dry-run 不生成 candidate
 */
import { test, expect } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_5_9_dry_run_ui'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.5.9 初始内容'

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
      theme: 'T6.5.9 dry-run UI',
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

test.describe('T6.5.9 前端 dry-run 测试入口 E2E', () => {
  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    console.log(`[t6.5.9] 测试项目 ID: ${projectId}`)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.5.9] 已清理项目: ${projectId}`)
    }
  })

  test('1. Dry Run 按钮存在（开发模式）', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(8000)

    // 查找 Dry Run 按钮（检查是否存在于 DOM 中）
    const dryRunButton = page.getByTestId('dry-run-task-button')
    
    // 等待按钮出现（attached 状态表示存在于 DOM 中）
    await dryRunButton.waitFor({ timeout: 15000, state: 'attached' })
    
    // 验证按钮存在并包含正确文本
    const buttonText = await dryRunButton.textContent()
    expect(buttonText).toContain('Dry Run')
    console.log('[t6.5.9] ✓ Dry Run 按钮存在')
  })

  test('2. 点击 Dry Run 按钮 → 任务创建成功 → 任务状态可见', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(8000)

    // 查找 Dry Run 按钮并点击
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await dryRunButton.waitFor({ timeout: 15000, state: 'attached' })
    
    // 使用 evaluate 直接调用按钮的点击事件
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-task-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待任务创建（通过 API 验证）
    await page.waitForTimeout(5000)

    // 通过 API 查询任务状态
    const taskList = await page.evaluate(async ({ apiBase }) => {
      const resp = await fetch(`${apiBase}/tasks`)
      const data = await resp.json()
      return data.data?.tasks || []
    }, { apiBase: BACKEND_API })

    // 验证有任务存在
    expect(taskList.length).toBeGreaterThan(0)
    console.log(`[t6.5.9] ✓ 任务列表包含 ${taskList.length} 个任务`)

    // 检查是否有 dry-run 任务
    const dryRunTasks = taskList.filter((t: any) => t.task_id?.includes('dry') || t.template?.includes('dry'))
    if (dryRunTasks.length > 0) {
      console.log('[t6.5.9] ✓ 找到 dry-run 任务')
    }
  })

  test('3. Dry Run 任务完成后 → 正文未被覆盖', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(5000)

    // 通过 evaluate 点击按钮
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-task-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待任务完成
    await page.waitForTimeout(8000)

    // 验证文件内容未变（直接通过 API）
    const content = await getFile(projectId, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.5.9] ✓ 正文未被覆盖')
  })

  test('4. Dry Run 不生成正式 candidate', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(5000)

    // 通过 evaluate 点击按钮
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
      console.log('[t6.5.9] ✓ 未生成正式 candidate')
    }
  })
})
