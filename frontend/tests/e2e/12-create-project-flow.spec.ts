/**
 * E2E: 模拟人类操作 — 创建项目完整流程
 *
 * 覆盖:
 * 1. 从主入口点击"新建项目"
 * 2. 填写表单（名称、类型、风格）
 * 3. 提交创建
 * 4. 验证跳转到项目页、文件树出现
 */
import { test, expect, type Page } from '@playwright/test'
import { openMainEntry } from './helpers/entryHelpers'
import { dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'

const projectId = 'e2e-human-create'

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

    // ── Projects ──
    if (path === '/projects' && method === 'GET') {
      await ok({ projects: [], total: 0 })
    } else if (path === '/projects' && method === 'POST') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: '测试项目-人类操作',
        genre: '修仙',
        tone: '热血',
        background: '',
        theme: '',
        writing_style: '古风',
        target_word_count: 50000,
        total_words: 0,
      })
    } else if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: '测试项目-人类操作',
        genre: '修仙',
        target_word_count: 50000,
        total_words: 0,
      })
    }

    // ── LLM ──
    else if (path === '/llm/config' && method === 'GET') {
      await ok({ provider: 'openai-compatible', model: 'mock-model', connected: true })
    } else if (path === '/llm/status' && method === 'GET') {
      await ok({ connected: true })
    }

    // ── SSE ──
    else if (path === '/sse') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: 'event: connected\ndata: {"timestamp":0}\n\n',
      })
    }

    // ── Config ──
    else if (path === '/config/custom-params' && method === 'GET') {
      await ok({})
    }

    // ── Tree / Files ──
    else if (path === '/tree' && method === 'GET') {
      await ok({
        tree: [
          { name: '书名与创意.md', path: `${projectId}/书名与创意.md`, type: 'file' },
          { name: 'chapters', path: `${projectId}/chapters`, type: 'directory', children: [
            { name: 'vol-01', path: `${projectId}/chapters/vol-01`, type: 'directory', children: [] },
          ] },
        ],
      })
    } else if (path === '/file' && method === 'GET') {
      await ok({
        content: '# 测试项目\n\n这是一个测试项目的内容。',
        frontmatter: null,
        path: '书名与创意.md',
        mtime: Date.now(),
        hash: 'mock-hash',
      })
    } else if (path === '/file/create' && method === 'POST') {
      await ok({ path: '书名与创意.md' })
    } else if (path === '/file/save' && method === 'POST') {
      await ok({ mtime: Date.now(), hash: 'saved-hash' })
    }

    // ── Generate (for pendingGeneration auto-trigger) ──
    else if (path === '/generate' && method === 'POST') {
      await ok({ task_id: 'mock-task', message: 'mock generation' })
    }

    // ── Catch-all ──
    else {
      await ok({})
    }
  })
}

test.describe('创建项目流程 - 模拟人类操作', () => {
  test('从主入口点击新建，填写表单，创建成功并跳转', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 1. 打开主入口
    await openMainEntry(page)
    await dismissViteOverlay(page)

    // 验证主入口已加载
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 10000 })

    // 2. 点击"新建项目"按钮（header 中的金色按钮）
    await page.getByTitle('新建项目').click()

    // 验证创建项目弹窗打开
    await expect(page.getByTestId('create-project-name-input')).toBeVisible({ timeout: 5000 })

    // 3. 填写项目名称
    await page.getByTestId('create-project-name-input').fill('测试项目-人类操作')

    // 4. 选择类型 — 点击"修仙" radio button
    await page.locator('.ant-radio-button-wrapper', { hasText: '修仙' }).first().click()

    // 5. 选择写作风格 — 点击"细腻"
    await page.locator('.ant-radio-button-wrapper', { hasText: '细腻' }).first().click()

    // 6. 点击提交按钮
    await page.getByTestId('create-project-submit').click()

    // 7. 验证 URL 跳转到项目页
    await expect(page).toHaveURL(new RegExp(`/project/${projectId}$`), { timeout: 15000 })

    // 8. 验证文件树出现
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 10000 })

    // 9. 验证编辑器区域可见
    await expect(page.getByTestId('editor-panel')).toBeVisible()

    // 10. 验证无严重 console 错误
    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('创建项目弹窗可以取消关闭', async ({ page }) => {
    await installMocks(page)

    await openMainEntry(page)
    await dismissViteOverlay(page)

    // 点击新建
    await page.getByTitle('新建项目').click()
    await expect(page.getByTestId('create-project-name-input')).toBeVisible()

    // 点击弹窗关闭按钮 (X)
    await page.locator('.ant-modal-close').click()
    await page.waitForTimeout(800)

    // 验证弹窗已关闭, 主入口仍然可见
    await expect(page.getByTestId('main-entry-root')).toBeVisible()
    // 输入框不应可见
    await expect(page.getByTestId('create-project-name-input')).not.toBeVisible()
  })

  test('创建后文件树显示项目文件', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await openMainEntry(page)
    await dismissViteOverlay(page)

    // 执行创建流程
    await page.getByTitle('新建项目').click()
    await page.getByTestId('create-project-name-input').fill('测试项目-人类操作')
    await page.locator('.ant-radio-button-wrapper', { hasText: '修仙' }).first().click()
    await page.getByTestId('create-project-submit').click()

    await expect(page).toHaveURL(new RegExp(`/project/${projectId}$`), { timeout: 15000 })

    // 文件树应该显示 "书名与创意.md"
    const fileTree = page.getByTestId('file-tree')
    await expect(fileTree).toBeVisible({ timeout: 10000 })
    await expect(fileTree).toContainText('书名与创意')

    // chapters 目录应该可见
    await expect(fileTree).toContainText('chapters')

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
