import { expect, test, type Page } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const projectId = 't9-3-continuity-project'
const scenePath = 'chapters/vol-01/ch-001/sec-001.md'

type Anchor = Record<string, unknown>

async function installContinuityMocks(page: Page, initialAnchors: Anchor[] = []) {
  const state = {
    anchors: [...initialAnchors],
    putPayloads: [] as Record<string, unknown>[],
  }

  await page.addInitScript(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  await page.route('http://127.0.0.1:5173/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace('/api', '')
    const method = request.method()
    const ok = async (data: unknown) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data }),
    })

    if (path === '/projects' && method === 'GET') {
      await ok({ projects: [{ id: projectId, project_id: projectId, name: 'Continuity E2E' }], total: 1 })
      return
    }
    if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({ id: projectId, project_id: projectId, name: 'Continuity E2E' })
      return
    }
    if (path === `/projects/${projectId}/continuity-anchors` && method === 'GET') {
      await ok({ version: 1, anchors: state.anchors })
      return
    }
    if (path === `/projects/${projectId}/continuity-anchors` && method === 'PUT') {
      const payload = request.postDataJSON() as Record<string, unknown>
      state.putPayloads.push(payload)
      state.anchors = Array.isArray(payload.anchors) ? [...payload.anchors as Anchor[]] : []
      await ok({ version: 1, anchors: state.anchors })
      return
    }
    if (path === '/tree' && method === 'GET') {
      await ok({
        tree: [{
          name: 'chapters',
          path: `${projectId}/chapters`,
          type: 'directory',
          children: [{ name: 'sec-001.md', path: scenePath, type: 'file' }],
        }],
      })
      return
    }
    if (path === '/file' && method === 'GET') {
      const requestedPath = url.searchParams.get('path') || scenePath
      const content = requestedPath.endsWith('story-engine.md')
        ? '# 故事引擎\n\n## 人物欲望\n- 保持目标\n\n## 冲突推进\n- 保持冲突\n\n## 前文记忆\n- 保持记忆\n\n## 阶段性目标\n- 保持目标\n'
        : '# 第一场景\n\n正文'
      await ok({ path: requestedPath, content, frontmatter: null, mtime: 1001, hash: 'hash-1' })
      return
    }
    if (path === '/llm/config' && method === 'GET') {
      await ok({ provider: 'mock', model: 'mock-model', connected: true })
      return
    }
    if (path === '/llm/status' && method === 'GET') {
      await ok({ connected: true })
      return
    }
    if (path === '/config/custom-params' && method === 'GET') {
      await ok({})
      return
    }
    if (path === '/sse') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: 'event: connected\ndata: {"timestamp":0}\n\n',
      })
      return
    }
    if (/^\/candidates\//.test(path) && method === 'GET') {
      await ok({ candidates: [] })
      return
    }
    await ok({})
  })

  return state
}

test.describe('T9.3 continuity anchors MVP', () => {
  test('old project without anchors opens quick panel safely', async ({ page }) => {
    await installContinuityMocks(page)
    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    const section = page.getByTestId('continuity-anchors-section')
    await expect(section).toBeVisible({ timeout: 5000 })
    await expect(section).toContainText('暂无 active 锚点')
  })

  test('user can add and archive an active continuity anchor', async ({ page }) => {
    const state = await installContinuityMocks(page)
    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    await page.getByTestId('continuity-anchors-section').click()
    await page.getByTestId('continuity-anchor-title').fill('沈知夏左臂受伤')
    await page.getByTestId('continuity-anchor-content').fill('沈知夏左臂仍有旧伤，不能高强度攀爬。')
    await page.getByTestId('continuity-anchor-type').selectOption('character_state')
    await page.getByTestId('continuity-anchor-priority').selectOption('high')
    await page.getByTestId('continuity-anchor-add').click()

    await expect(page.getByTestId('continuity-anchor-item')).toContainText('沈知夏左臂受伤')
    expect(state.putPayloads.at(-1)?.anchors).toEqual(expect.arrayContaining([
      expect.objectContaining({ status: 'active', type: 'character_state', priority: 'high' }),
    ]))

    await page.getByTestId('continuity-anchor-archive').click()
    await expect(page.getByTestId('continuity-anchor-item')).toHaveCount(0)
    expect(state.putPayloads.at(-1)?.anchors).toEqual(expect.arrayContaining([
      expect.objectContaining({ status: 'archived' }),
    ]))
  })
})
