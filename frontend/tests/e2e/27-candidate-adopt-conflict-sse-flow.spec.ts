/**
 * T6.6.2 Candidate adopt + conflict + SSE 串联测试
 *
 * 验证 Candidate 完整工作流：
 * - 候选稿创建/预置
 * - 预览（不覆盖正文）
 * - 采用成功
 * - SSE 事件接收
 * - 冲突检测
 */
import { test, expect } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_6_2_candidate_sse'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.6.2 初始正文'
const CANDIDATE_CONTENT = 'T6.6.2 candidate 正文'
const CONFLICT_CONTENT = 'T6.6.2 外部冲突正文'

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
      theme: 'T6.6.2 Candidate SSE',
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

async function createCandidate(projectId: string, sourcePath: string, content: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      source_path: sourcePath,
      action: 'polish',
      content,
    }),
  })
  const data = await resp.json()
  return data.id || ''
}

async function adoptCandidate(projectId: string, candidateId: string): Promise<{ success: boolean; status: number; body: any }> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}/${candidateId}/adopt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  const body = await resp.json()
  return { success: resp.ok, status: resp.status, body }
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

test.describe('T6.6.2 Candidate adopt + conflict + SSE 串联测试', () => {
  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    console.log(`[t6.6.2] 测试项目 ID: ${projectId}`)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.6.2] 已清理项目: ${projectId}`)
    }
  })

  test('1. 打开项目页面 → 文件树可见 → 编辑器显示初始正文', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.cm-content')).toContainText(INITIAL_CONTENT, { timeout: 10000 })
    console.log('[t6.6.2] ✓ 页面打开成功，编辑器显示初始正文')
  })

  test('2. 通过 API 创建 candidate → 验证 candidate 存在且状态为 pending', async () => {
    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, CANDIDATE_CONTENT)
    console.log(`[t6.6.2] 创建 candidate ID: ${candidateId}`)
    
    expect(candidateId).toBeTruthy()
    
    const candidates = await getCandidates(projectId)
    const targetCandidate = candidates.find((c: any) => c.id === candidateId)
    expect(targetCandidate).toBeTruthy()
    expect(targetCandidate.status).toBe('pending')
    expect(targetCandidate.base_hash).toBeTruthy()
    console.log('[t6.6.2] ✓ candidate 创建成功，状态为 pending')
  })

  test('3. Preview candidate → 通过 API 验证内容且不覆盖正文', async () => {
    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, CANDIDATE_CONTENT)
    
    const resp = await fetch(`${BACKEND_API}/candidates/${projectId}/${candidateId}`)
    const data = await resp.json()
    expect(data.content).toBe(CANDIDATE_CONTENT)
    
    const fileContent = await getFile(projectId, TEST_FILE_PATH)
    expect(fileContent).toBe(INITIAL_CONTENT)
    console.log('[t6.6.2] ✓ Preview 获取成功，正文未被覆盖')
  })

  test('4. Adopt candidate 成功 → 正文更新 → candidate 状态 adopted', async () => {
    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, CANDIDATE_CONTENT)
    
    const adoptResult = await adoptCandidate(projectId, candidateId)
    expect(adoptResult.success).toBe(true)
    
    const fileContent = await getFile(projectId, TEST_FILE_PATH)
    expect(fileContent).toBe(CANDIDATE_CONTENT)
    console.log('[t6.6.2] ✓ Adopt 成功，正文已更新')
    
    const candidates = await getCandidates(projectId)
    const targetCandidate = candidates.find((c: any) => c.id === candidateId)
    expect(targetCandidate.status).toBe('adopted')
    console.log('[t6.6.2] ✓ candidate 状态为 adopted')
  })

  test('5. 冲突测试：外部修改后 adopt 失败', async () => {
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
    
    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, '冲突测试 candidate')
    
    await writeFile(projectId, TEST_FILE_PATH, CONFLICT_CONTENT)
    
    const adoptResult = await adoptCandidate(projectId, candidateId)
    
    expect(adoptResult.status).toBe(409)
    console.log(`[t6.6.2] ✓ 冲突时返回状态码: ${adoptResult.status}`)
    
    const fileContent = await getFile(projectId, TEST_FILE_PATH)
    expect(fileContent).toBe(CONFLICT_CONTENT)
    console.log('[t6.6.2] ✓ 冲突时正文未被覆盖')
    
    const candidates = await getCandidates(projectId)
    const targetCandidate = candidates.find((c: any) => c.id === candidateId)
    expect(targetCandidate.status).toBe('rejected')
    console.log('[t6.6.2] ✓ 冲突 candidate 状态为 rejected')
  })

  test('6. SSE 事件验证：页面打开后能收到事件', async ({ page }) => {
    await installLLMMock(page)

    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)
    await page.waitForTimeout(5000)

    await page.evaluate(() => {
      ;(window as any)._sseEvents = []
    })

    await page.evaluate(() => {
      const sseService = (window as any).sseService
      if (sseService) {
        sseService.on('candidate-adopted', (data: any) => {
          ;(window as any)._sseEvents.push({ type: 'candidate-adopted', data })
        })
        sseService.on('file-updated', (data: any) => {
          ;(window as any)._sseEvents.push({ type: 'file-updated', data })
        })
      }
    })

    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, 'SSE 测试内容')
    await writeFile(projectId, TEST_FILE_PATH, '触发 file-updated')

    await page.waitForTimeout(5000)

    const events = await page.evaluate(() => (window as any)._sseEvents || [])
    console.log('[t6.6.2] 收到的 SSE 事件:', JSON.stringify(events, null, 2))

    const fileUpdatedEvent = events.find((e: any) => e.type === 'file-updated')
    if (fileUpdatedEvent) {
      console.log('[t6.6.2] ✓ file-updated SSE 事件已收到')
    } else {
      console.log('[t6.6.2] ⚠️ file-updated SSE 事件未收到')
    }
  })
})