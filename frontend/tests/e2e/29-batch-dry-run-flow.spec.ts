/**
 * T6.6.4 Batch Dry Run 测试
 *
 * 验证：
 * - Batch dry-run 按钮存在
 * - API 请求带 dry_run:true
 * - 响应包含 dry_run 标记
 * - 正文未覆盖
 * - 未生成 candidate
 */
import { test, expect } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_6_4_batch_dry_run'
const TEST_FILE_PATH_1 = 'chapters/vol-01/ch-001/sec-001.md'
const TEST_FILE_PATH_2 = 'chapters/vol-01/ch-001/sec-002.md'
const INITIAL_CONTENT_1 = 'T6.6.4 Batch 初始正文 1'
const INITIAL_CONTENT_2 = 'T6.6.4 Batch 初始正文 2'

async function createProject(name: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      genre: '测试',
      theme: 'T6.6.4 Batch Dry Run',
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

async function writeFile(projectId: string, relpath: string, content: string): Promise<void> {
  await fetch(`${BACKEND_API}/file?project_id=${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: relpath, content }),
  })
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

async function deleteProject(projectId: string): Promise<void> {
  await fetch(`${BACKEND_API}/projects/${projectId}`, { method: 'DELETE' })
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

test.describe('T6.6.4 Batch Dry Run', () => {
  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    await writeFile(projectId, TEST_FILE_PATH_1, INITIAL_CONTENT_1)
    await writeFile(projectId, TEST_FILE_PATH_2, INITIAL_CONTENT_2)
    console.log(`[t6.6.4] 测试项目: ${projectId}`)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log('[t6.6.4] 项目清理完成')
    }
  })

  test('1. 打开项目页 → Batch Dry Run 按钮存在', async ({ page }) => {
    await installLLMMock(page)
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH_1}`)
    await dismissViteOverlay(page)

    // 验证按钮在 DOM 中存在（isDevMode 为 true 时才渲染）
    const batchBtn = page.getByTestId('dry-run-batch-button')
    await batchBtn.waitFor({ state: 'attached', timeout: 20000 })

    // 检查按钮是否可见或 hidden - 只要在 DOM 中就说明被正确渲染
    const isAttached = await batchBtn.isVisible()
    console.log(`[t6.6.4] ✓ Batch Dry Run 按钮在 DOM 中, visible=${isAttached}`)
  })

  test('2. API 触发 Batch Dry Run → 返回 dry_run 标记', async () => {
    const resp = await fetch(`${BACKEND_API}/generate/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        volume_number: 1,
        chapter_number: 1,
        section_numbers: [1, 2],
        prompt_type: 'generate/chapter',
        dry_run: true,
      }),
    })

    const data = await resp.json()
    expect(data.success).toBe(true)

    const result = data.data
    expect(result.total).toBe(2)
    expect(result.succeeded).toBe(2)

    for (const task of result.tasks) {
      expect(task.dry_run).toBe(true)
      expect(task.status).toBe('dry_run')
    }
    console.log('[t6.6.4] ✓ Batch dry-run 返回 dry_run 标记')
  })

  test('3. Batch dry-run 不覆盖正文', async () => {
    const content1 = await getFile(projectId, TEST_FILE_PATH_1)
    expect(content1).toBe(INITIAL_CONTENT_1)

    const content2 = await getFile(projectId, TEST_FILE_PATH_2)
    expect(content2).toBe(INITIAL_CONTENT_2)
    console.log('[t6.6.4] ✓ 正文未被覆盖')
  })

  test('4. Batch dry-run 不生成候选稿', async () => {
    const candidates = await getCandidates(projectId)
    expect(candidates.length).toBe(0)
    console.log('[t6.6.4] ✓ 未生成候选稿')
  })
})
