/**
 * E2E: 回归测试 — 之前修复的 Bug
 *
 * Bug 1: 登录后显示"获取候选稿列表失败"
 * Bug 2: 主页进去不能正确生成内容（beforeEnter 验证项目）
 * Bug 3: 过期项目数据不清除导致白屏
 *
 * 这些测试验证修复后的行为是正确的。
 */
import { test, expect, type Page } from '@playwright/test'
import { openMainEntry } from './helpers/entryHelpers'
import { dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'

const projectId = 'e2e-human-regression'

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
      await ok({
        projects: [{
          project_id: projectId,
          id: projectId,
          name: '回归测试项目',
          genre: '奇幻',
          target_word_count: 50000,
          total_words: 800,
        }],
        total: 1,
      })
    } else if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: '回归测试项目',
        genre: '奇幻',
        target_word_count: 50000,
        total_words: 800,
      })
    } else if (path === '/projects/non-existent' && method === 'GET') {
      // 模拟不存在的项目
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: false, message: 'Project not found' }),
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

    // ── Tree ──
    else if (path === '/tree' && method === 'GET') {
      await ok({
        tree: [
          { name: '书名与创意.md', path: `${projectId}/书名与创意.md`, type: 'file' },
          { name: 'chapters', path: `${projectId}/chapters`, type: 'directory', children: [
            { name: 'vol-01', path: `${projectId}/chapters/vol-01`, type: 'directory', children: [
              { name: 'ch-001', path: `${projectId}/chapters/vol-01/ch-001`, type: 'directory', children: [
                { name: 'sec-001.md', path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`, type: 'file' },
              ] },
            ] },
          ] },
        ],
      })
    }

    // ── File ──
    else if (path === '/file' && method === 'GET') {
      const filePath = url.searchParams.get('path') || ''
      await ok({
        content: filePath.includes('sec-001') ? '# 第一章\n\n魔法学院的新生入学仪式即将开始。' : '# 书名\n\n魔法纪元',
        frontmatter: null,
        path: filePath,
        mtime: Date.now(),
        hash: `hash-${filePath}`,
      })
    } else if (path === '/file/save' && method === 'POST') {
      await ok({ mtime: Date.now(), hash: 'saved-hash' })
    }

    // ── Candidates ──
    else if (/^\/candidates\//.test(path) && method === 'GET') {
      await ok([])
    }

    // ── Prompts / Pipeline / Workflows ──
    else if (path.startsWith('/prompts/') && method === 'GET') {
      await ok('')
    } else if (path.startsWith('/pipeline/') && method === 'GET') {
      await ok([])
    } else if (path.startsWith('/workflows/') && method === 'GET') {
      await ok([])
    } else if (/^\/memory\/status\//.test(path) && method === 'GET') {
      await ok({
        project_id: projectId,
        story_state_exists: false,
        recent_context_exists: false,
        style_guide_exists: true,
      })
    }

    // ── Generate ──
    else if (path === '/generate' && method === 'POST') {
      await ok({ task_id: 'mock-task' })
    }

    // ── Catch-all ──
    else {
      await ok({})
    }
  })
}

test.describe('Bug 回归测试', () => {
  test('BUG-1: 登录后不应显示"获取候选稿列表失败"错误', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 直接用 openMainEntry 打开主页（模拟有 persisted project 的情况）
    // 先设置 localStorage 模拟 persisted project
    await page.addInitScript(({ projectId }) => {
      localStorage.setItem('project', JSON.stringify({
        currentProject: {
          project_id: projectId,
          id: projectId,
          name: '回归测试项目',
          genre: '奇幻',
        },
        openProjectId: projectId,
      }))
    }, { projectId })

    await openMainEntry(page)
    await dismissViteOverlay(page)

    // 验证页面正常加载
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })

    // 验证没有错误通知弹出
    const errorNotice = page.locator('.ant-notification-notice').filter({ hasText: /获取候选稿列表失败/i })
    await expect(errorNotice).toHaveCount(0)

    // 验证无严重 console 错误
    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('BUG-1: 直接访问项目页不应显示候选稿错误', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 直接导航到项目页（不使用 openMainEntry）
    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    // 验证页面正常加载
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 10000 })

    // 验证没有错误通知
    const errorNotice = page.locator('.ant-notification-notice').filter({ hasText: /获取候选稿列表失败/i })
    await expect(errorNotice).toHaveCount(0)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('BUG-2: 主页 loaded project 后有编辑器和文件树', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.addInitScript(({ projectId }) => {
      localStorage.setItem('project', JSON.stringify({
        currentProject: {
          project_id: projectId,
          id: projectId,
          name: '回归测试项目',
          genre: '奇幻',
        },
        openProjectId: projectId,
      }))
    }, { projectId })

    await openMainEntry(page)
    await dismissViteOverlay(page)

    // 验证核心区域可用
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId('file-tree')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('editor-panel')).toBeVisible()

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('BUG-3: 不存在的 stale 项目不会导致白屏', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 模拟一个已删除的项目 ID 被持久化
    await page.addInitScript(() => {
      localStorage.setItem('project', JSON.stringify({
        currentProject: {
          project_id: 'non-existent',
          id: 'non-existent',
          name: '已删除的项目',
          genre: '未知',
        },
        openProjectId: 'non-existent',
      }))
    })

    await openMainEntry(page)
    await dismissViteOverlay(page)

    // 页面应该仍然正常渲染（root route 的 beforeEnter 会清除过期数据）
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 15000 })

    // 文件树应该显示（可能是空状态）
    const fileTree = page.getByTestId('file-tree')
    await expect(fileTree).toBeVisible({ timeout: 5000 })

    // 不应该白屏
    const bodyText = await page.locator('body').textContent()
    expect(bodyText.length).toBeGreaterThan(0)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
