/**
 * E2E: 模拟人类操作 — 文件操作流程
 *
 * 覆盖:
 * 1. 打开已有项目
 * 2. 点击文件树中的文件
 * 3. 在 CodeMirror 编辑器中编辑内容
 * 4. 保存文件
 * 5. 切换 tab
 * 6. 新建文件
 */
import { test, expect, type Page } from '@playwright/test'
import { dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'

const projectId = 'e2e-human-fileops'

async function installMocks(page: Page) {
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
          project_id: projectId, id: projectId,
          name: '文件操作测试项目', genre: '都市',
          target_word_count: 50000, total_words: 1200,
        }],
        total: 1,
      })
    } else if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({
        project_id: projectId, id: projectId,
        name: '文件操作测试项目', genre: '都市',
        target_word_count: 50000, total_words: 1200,
      })
    } else if (path === '/llm/config' && method === 'GET') {
      await ok({ provider: 'openai-compatible', model: 'mock-model', connected: true })
    } else if (path === '/llm/status' && method === 'GET') {
      await ok({ connected: true })
    } else if (path === '/sse') {
      await route.fulfill({
        status: 200, contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: 'event: connected\ndata: {"timestamp":0}\n\n',
      })
    } else if (path === '/config/custom-params' && method === 'GET') {
      await ok({})
    } else if (path === '/tree' && method === 'GET') {
      // Use names that won't be transformed by displayName (sec-001 → 第1场景)
      await ok({
        tree: [
          { name: '书名与创意.md', path: `${projectId}/书名与创意.md`, type: 'file' },
          { name: 'intro.md', path: `${projectId}/intro.md`, type: 'file' },
          { name: 'chapter-01.md', path: `${projectId}/chapter-01.md`, type: 'file' },
          { name: 'style-guide.md', path: `${projectId}/style-guide.md`, type: 'file' },
        ],
      })
    } else if (path === '/file' && method === 'GET') {
      const filePath = url.searchParams.get('path') || ''
      let content = '# 默认内容'
      if (filePath.includes('intro')) {
        content = '# 序章\n\n林澈推开房门，走廊里空无一人。\n\n他闻到了一股淡淡的消毒水味道，走廊尽头的灯忽明忽暗。'
      } else if (filePath.includes('chapter-01')) {
        content = '# 第一章\n\n沈知夏站在电梯口等他。她的眼神冰冷如霜。'
      } else if (filePath.includes('书名与创意')) {
        content = '# 都市边缘\n\n一个失去记忆的年轻人发现自己拥有异能的故事。'
      }
      await ok({ content, frontmatter: null, path: filePath, mtime: Date.now(), hash: `hash-${filePath}` })
    } else if (path === '/file/create' && method === 'POST') {
      const body = request.postDataJSON() as { path?: string }
      await ok({ path: body?.path || 'new-file.md' })
    } else if (path === '/file/save' && method === 'POST') {
      await ok({ mtime: Date.now(), hash: 'saved-hash' })
    } else if (path === '/file/rename' && method === 'POST') {
      await ok({ success: true })
    } else if (path === '/file/delete' && method === 'POST') {
      await ok({ success: true })
    } else if (path === '/directory/create' && method === 'POST') {
      await ok({ success: true })
    } else if (/^\/candidates\//.test(path) && method === 'GET') {
      await ok([])
    } else {
      await ok({})
    }
  })
}

test.describe('文件操作流程 - 模拟人类操作', () => {
  // ── 清理 Pinia 持久化状态，防止 spec 间 localStorage 泄漏 ──
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

  test('打开项目后，点击文件加载到编辑器', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 10000 })

    // Click intro.md in the file tree (name not transformed by displayName)
    await page.locator('.node-name', { hasText: 'intro.md' }).first().click()

    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.cm-content')).toContainText('林澈', { timeout: 5000 })
    await expect(page.locator('.tab.active')).toContainText('intro.md')

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('在编辑器中编辑内容并保存', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    await page.locator('.node-name', { hasText: 'intro.md' }).first().click()
    await expect(page.getByTestId('codemirror-container')).toBeVisible({ timeout: 5000 })

    const cmContent = page.locator('.cm-content')
    await cmContent.click()
    await page.keyboard.press('Control+a')
    await page.keyboard.type('修改后的内容：新的场景描述。')
    await expect(cmContent).toContainText('修改后的内容')

    await page.keyboard.press('Control+s')
    await page.waitForTimeout(1000)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('切换文件后编辑器内容更新', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    await page.locator('.node-name', { hasText: 'intro.md' }).first().click()
    await expect(page.locator('.cm-content')).toContainText('林澈', { timeout: 5000 })

    await page.locator('.node-name', { hasText: 'chapter-01.md' }).first().click()
    await expect(page.locator('.cm-content')).toContainText('沈知夏', { timeout: 5000 })

    // Verify both tabs exist (use filter to avoid strict mode with 3+ tabs)
    await expect(page.locator('.tab').filter({ hasText: 'intro.md' })).toBeVisible()
    await expect(page.locator('.tab').filter({ hasText: 'chapter-01.md' })).toBeVisible()
    await expect(page.locator('.tab.active')).toContainText('chapter-01.md')
  })

  test('新建文件', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 10000 })

    await page.evaluate(() => { window.prompt = () => '新场景.md' })

    const fileTree = page.getByTestId('file-tree')
    const addButton = fileTree.locator('button').filter({ has: page.locator('svg') }).first()
    await addButton.click()
    await page.waitForTimeout(500)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
