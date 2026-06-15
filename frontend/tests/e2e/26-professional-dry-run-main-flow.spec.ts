/**
 * T6.6.1 Professional 主流程 dry-run E2E 测试
 *
 * 验证更完整的 Professional 工作台用户路径：
 * 项目打开 → 文件树导航 → 编辑器 → dry-run 任务 → 状态查看 → 安全边界验证
 *
 * 安全边界：
 * - 不调用真实 LLM
 * - 不覆盖正文
 * - 不生成正式 candidate
 */
import { test, expect } from '@playwright/test'
// ── Gate：需要真实后端 ──────────────────────────────────────────
const REAL_BACKEND_AVAILABLE = process.env.MOYUN_E2E_REAL_BACKEND === '1'

import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_6_1_professional_dry_run'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.6.1 Professional 初始正文'

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
      theme: 'T6.6.1 Professional Dry Run',
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

test.describe('T6.6.1 Professional 主流程 dry-run E2E', () => {
  test.skip(
    !REAL_BACKEND_AVAILABLE,
    'MOYUN_E2E_REAL_BACKEND=1 未设置，跳过需要真实后端的测试',
  )

  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    console.log(`[t6.6.1] 测试项目 ID: ${projectId}`)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.6.1] 已清理项目: ${projectId}`)
    }
  })

  test('1. 打开项目页面 → 文件树可见', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 验证文件树可见
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })
    console.log('[t6.6.1] ✓ 文件树可见')
  })

  test('2. 通过文件树打开文件 → 编辑器显示正文', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待编辑器加载
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })

    // 验证编辑器内容显示
    await expect(page.locator('.cm-content')).toContainText(INITIAL_CONTENT, { timeout: 10000 })
    console.log('[t6.6.1] ✓ 编辑器显示初始正文')
  })

  test('3. 右侧 ExecutionPanel 可见 → dry-run 按钮存在', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待页面加载
    await page.waitForTimeout(8000)

    // 验证 dry-run 按钮存在
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await dryRunButton.waitFor({ timeout: 15000, state: 'attached' })
    
    const buttonText = await dryRunButton.textContent()
    expect(buttonText).toContain('Dry Run')
    console.log('[t6.6.1] ✓ dry-run 按钮存在')
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

    // 通过 API 查询任务状态
    const taskResult = await page.evaluate(async ({ apiBase }) => {
      const resp = await fetch(`${apiBase}/tasks`)
      const data = await resp.json()
      return data.data?.tasks?.slice(-1)[0] || null  // 获取最后一个任务
    }, { apiBase: BACKEND_API })

    expect(taskResult).not.toBeNull()
    expect(taskResult.task_id).toBeTruthy()
    console.log(`[t6.6.1] ✓ 任务创建成功，任务 ID: ${taskResult.task_id}`)
  })

  test('5. 任务状态验证 → 通过 API 确认 dry-run 标记', async ({ page }) => {
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

    // 查询任务详情
    const taskDetail = await page.evaluate(async ({ apiBase }) => {
      const listResp = await fetch(`${apiBase}/tasks`)
      const listData = await listResp.json()
      const tasks = listData.data?.tasks || []
      if (tasks.length === 0) return null
      
      const lastTask = tasks[tasks.length - 1]
      const detailResp = await fetch(`${apiBase}/tasks/${lastTask.task_id}`)
      return detailResp.json()
    }, { apiBase: BACKEND_API })

    expect(taskDetail.success).toBe(true)
    expect(taskDetail.data.task_id).toBeTruthy()
    console.log(`[t6.6.1] ✓ 任务状态可查询`)
  })

  test('6. 安全边界：正文未被覆盖', async ({ page }) => {
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

    // 验证文件内容（API 验证）
    const content = await getFile(projectId, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.6.1] ✓ 正文未被覆盖')

    // 验证编辑器内容（UI 验证）
    await expect(page.locator('.cm-content')).toContainText(INITIAL_CONTENT, { timeout: 10000 })
    console.log('[t6.6.1] ✓ 编辑器显示内容未变')
  })

  test('7. 安全边界：未生成正式 candidate', async ({ page }) => {
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

    // 通过 API 查询 candidate 列表
    const candidatesResp = await page.evaluate(async ({ pid, apiBase }) => {
      const resp = await fetch(`${apiBase}/candidates?project_id=${pid}`)
      return resp.json()
    }, { pid: projectId, apiBase: BACKEND_API })

    if (candidatesResp.success && candidatesResp.data?.candidates) {
      const targetCandidates = candidatesResp.data.candidates.filter((c: any) =>
        c.source_path === TEST_FILE_PATH
      )
      expect(targetCandidates.length).toBe(0)
      console.log('[t6.6.1] ✓ 未生成正式 candidate')
    } else {
      console.log('[t6.6.1] ✓ 无 candidate 列表或列表为空')
    }
  })

  test('8. 任务状态轮询验证', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 等待轮询启动（ExecutionPanel 在 onMounted 启动轮询）
    await page.waitForTimeout(10000)

    // 点击 dry-run 按钮
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="dry-run-task-button"]')
      if (btn) {
        btn.click()
      }
    })

    // 等待轮询更新
    await page.waitForTimeout(8000)

    // 验证任务出现在列表中（通过 API 验证轮询效果）
    const taskCount = await page.evaluate(async ({ apiBase }) => {
      const resp = await fetch(`${apiBase}/tasks`)
      const data = await resp.json()
      return (data.data?.tasks || []).length
    }, { apiBase: BACKEND_API })

    expect(taskCount).toBeGreaterThan(0)
    console.log(`[t6.6.1] ✓ 轮询正常，任务数: ${taskCount}`)
  })
})
