import { test, expect, type Page } from '@playwright/test'
import { dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'

const projectId = 'right-panel-project'

async function installRightPanelMocks(page: Page) {
  await page.route('http://127.0.0.1:5173/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace('/api', '')
    const method = request.method()

    const ok = async (data: unknown) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }

    if (path === '/projects' && method === 'GET') {
      await ok({
        projects: [{
          project_id: projectId,
          id: projectId,
          name: 'Right Panel Project',
          genre: 'urban',
          target_word_count: 50000,
          total_words: 800,
        }],
        total: 1,
      })
    } else if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: 'Right Panel Project',
        genre: 'urban',
        target_word_count: 50000,
        total_words: 800,
      })
    } else if (path === '/tree' && method === 'GET') {
      await ok({
        tree: [
          { name: 'chapters', path: `${projectId}/chapters`, type: 'directory', children: [
            { name: 'vol-01', path: `${projectId}/chapters/vol-01`, type: 'directory', children: [
              { name: 'ch-001', path: `${projectId}/chapters/vol-01/ch-001`, type: 'directory', children: [
                { name: 'sec-001.md', path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`, type: 'file' },
              ] },
            ] },
          ] },
          { name: 'story-state.md', path: `${projectId}/story-state.md`, type: 'file' },
          { name: 'style-guide.md', path: `${projectId}/style-guide.md`, type: 'file' },
          { name: 'recent-context.md', path: `${projectId}/recent-context.md`, type: 'file' },
        ],
      })
    } else if (path === '/file' && method === 'GET') {
      const filePath = url.searchParams.get('path') || ''
      await ok({
        content: filePath.includes('sec-001')
          ? '# Scene 1\n\nMock scene content for right panel smoke.'
          : `# ${filePath || 'mock'}\n\nMock supporting document.`,
        frontmatter: null,
        path: filePath,
        mtime: Date.now(),
        hash: `hash-${filePath || 'mock'}`,
      })
    } else if (path === '/file/save' && method === 'POST') {
      await ok({ mtime: Date.now(), hash: 'saved-hash' })
    } else if (path === '/llm/config' && method === 'GET') {
      await ok({ provider: 'openai-compatible', model: 'mock-model', connected: true })
    } else if (path === '/llm/status' && method === 'GET') {
      await ok({ connected: true })
    } else if (path === '/sse') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: 'event: connected\ndata: {"timestamp":0}\n\n',
      })
    } else if (path === '/config/custom-params' && method === 'GET') {
      await ok({})
    } else if (/^\/candidates\//.test(path) && method === 'GET') {
      await ok([
        {
          id: 'candidate-1',
          source_path: 'chapters/vol-01/ch-001/sec-001.md',
          action: 'polish',
          status: 'pending',
          preview: 'Mock candidate preview.',
          created_at: new Date().toISOString(),
        },
      ])
    } else if (path.startsWith('/pipeline/') && method === 'GET') {
      await ok({})
    } else if (path.startsWith('/workflows/') && method === 'GET') {
      await ok({})
    } else if (path.startsWith('/prompts/') && method === 'GET') {
      await ok('')
    } else if (/^\/memory\/status\//.test(path) && method === 'GET') {
      await ok({
        project_id: projectId,
        story_state_exists: true,
        recent_context_exists: true,
        recent_entries_count: 3,
        story_state_length: 1024,
        recent_context_length: 2048,
        last_updated: Date.now() / 1000,
        story_engine_exists: true,
        story_engine_length: 512,
        story_engine_mtime: Date.now() / 1000,
        style_guide_exists: true,
        style_guide_length: 768,
        style_guide_mtime: Date.now() / 1000,
        recent_context_scene_limit: 15,
      })
    } else {
      await ok({})
    }
  })
}

test.describe('right panel tabs', () => {
  // ── 清理 Pinia 持久化状态，防止 spec 间 localStorage 泄漏 ──
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

  test('opens every professional right panel tab without crashing', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installRightPanelMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    const tabs = page.locator('.right-panel .panel-tab')
    // 至少 10 个 Tab（新增 Flow 流程 Tab 后可能更多）
    const tabCount = await tabs.count()
    expect(tabCount).toBeGreaterThanOrEqual(10)

    // 验证关键 Tab 存在（包含流程）
    const tabTexts = await tabs.allTextContents()
    expect(tabTexts.some(t => t.includes('流程'))).toBe(true)

    // 遍历所有 Tab
    for (let index = 0; index < tabCount; index += 1) {
      await tabs.nth(index).click()
      await expect(tabs.nth(index)).toHaveClass(/active/)
      await expect(page.locator('.right-panel > .panel-content')).toBeVisible()
      await expect(page.locator('.right-panel .error-boundary')).toHaveCount(0)
    }

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
