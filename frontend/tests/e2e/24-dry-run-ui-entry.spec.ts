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

async function getCandidates(projectId: string): Promise<any[]> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}`)
  const data = await resp.json()
  return data.candidates || []
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

  test('1. 切换到"执行" tab → Dry Run 按钮可见', async ({ page }) => {
    await installLLMMock(page)
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 切换到"执行" tab（dev-tools 在该 tab 下）
    const execTab = page.getByText('执行', { exact: true }).nth(0)
    await expect(execTab).toBeVisible({ timeout: 20000 })
    await execTab.click()
    console.log('[t6.5.9] ✓ 已切换到"执行" tab')

    // 验证 dev-dry-run-tools 区块可见
    const devTools = page.getByTestId('dev-dry-run-tools')
    await expect(devTools).toBeVisible({ timeout: 20000 })
    console.log('[t6.5.9] ✓ dev-dry-run-tools 区块可见')

    // 验证开发工具说明文案（T6.9.2 新增）
    const devToolsSubtitle = devTools.locator('.dev-tools-subtitle')
    await expect(devToolsSubtitle).toBeVisible({ timeout: 5000 })
    await expect(devToolsSubtitle).toContainText('不会调用真实 LLM')
    await expect(devToolsSubtitle).toContainText('不会写入正文')
    console.log('[t6.9.2] ✓ dev-tools-subtitle 文案存在且包含安全说明')

    // 验证 Task Dry Run 按钮可见
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await expect(dryRunButton).toBeVisible({ timeout: 20000 })
    const buttonText = await dryRunButton.textContent()
    expect(buttonText).toContain('Task Dry Run')
    console.log('[t6.5.9] ✓ Task Dry Run 按钮可见')
  })

  test('2. 点击 Dry Run 按钮 → 任务创建成功 → 任务状态可见', async ({ page }) => {
    await installLLMMock(page)
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 切换到"执行" tab
    const execTab = page.getByText('执行', { exact: true }).nth(0)
    await expect(execTab).toBeVisible({ timeout: 20000 })
    await execTab.click()

    // 真实用户 click（不是 JS force click）
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await expect(dryRunButton).toBeVisible({ timeout: 20000 })
    await dryRunButton.click()
    console.log('[t6.5.9] ✓ 已执行真实用户 click')

    // 等待任务创建（通过 API 验证）
    await page.waitForTimeout(5000)

    // 通过 API 查询任务状态
    const resp = await fetch(`${BACKEND_API}/tasks`)
    const data = await resp.json()
    const taskList = data.data?.tasks || []

    expect(taskList.length).toBeGreaterThan(0)
    console.log(`[t6.5.9] ✓ 任务列表包含 ${taskList.length} 个任务`)

    // ─── T6.7.4 统一状态面板断言 ───
    const statusPanel = page.getByTestId('dry-run-status-panel')
    await expect(statusPanel).toBeVisible({ timeout: 10000 })
    console.log('[t6.7.4] ✓ dry-run-status-panel 可见')

    const statusType = page.getByTestId('dry-run-status-type')
    await expect(statusType).toHaveText('task')
    console.log('[t6.7.4] ✓ dry-run-status-type === task')

    const statusState = page.getByTestId('dry-run-status-state')
    await expect(statusState).toBeVisible()
    // 最终状态可能是 completed 或 running（轮询未完成）
    console.log('[t6.7.4] ✓ dry-run-status-state 可见')

    const statusDryRun = page.getByTestId('dry-run-status-dry-run')
    await expect(statusDryRun).toContainText('true')
    console.log('[t6.7.4] ✓ dry-run-status-dry-run 包含 true')

    const statusSummary = page.getByTestId('dry-run-status-summary')
    await expect(statusSummary).toBeVisible()
    console.log('[t6.7.4] ✓ dry-run-status-summary 可见')
  })

  test('3. Dry Run 任务完成后 → 正文未被覆盖', async ({ page }) => {
    await installLLMMock(page)
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 切换到"执行" tab
    const execTab = page.getByText('执行', { exact: true }).nth(0)
    await expect(execTab).toBeVisible({ timeout: 20000 })
    await execTab.click()

    // 真实用户 click
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await expect(dryRunButton).toBeVisible({ timeout: 20000 })
    await dryRunButton.click()

    // 等待任务完成
    await page.waitForTimeout(8000)

    // 验证文件内容未变
    const content = await getFile(projectId, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.5.9] ✓ 正文未被覆盖')
  })

  test('4. Dry Run 不生成正式 candidate', async ({ page }) => {
    await installLLMMock(page)
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    // 切换到"执行" tab
    const execTab = page.getByText('执行', { exact: true }).nth(0)
    await expect(execTab).toBeVisible({ timeout: 20000 })
    await execTab.click()

    // 真实用户 click
    const dryRunButton = page.getByTestId('dry-run-task-button')
    await expect(dryRunButton).toBeVisible({ timeout: 20000 })
    await dryRunButton.click()

    // 等待任务完成
    await page.waitForTimeout(5000)

    // 验证没有生成 candidate
    const candidates = await getCandidates(projectId)
    const sourceCandidates = candidates.filter((c: any) => c.source_path === TEST_FILE_PATH)
    expect(sourceCandidates.length).toBe(0)
    console.log('[t6.5.9] ✓ 未生成正式 candidate')
  })
})
