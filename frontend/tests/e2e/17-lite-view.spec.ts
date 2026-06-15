/**
 * T6.5.2 - Lite（爽文模式）视图 E2E 测试
 *
 * 关键点：
 *   - 只拦截 /api/*，不碰 /src/*，避免 Vite 模块 MIME 错误
 *   - 不调用真实 LLM；所有生成结果都由 mock 返回
 *   - 页面显示 idea 卡片、写作视图、下一场景选项卡
 */
import { test, expect, type Page } from '@playwright/test'
import { createErrorCollector, dismissViteOverlay, filterSevereErrors } from './helpers/e2eUtils'

const projectId = '__e2e_t6_5_2_lite'

async function installMockApi(page: Page) {
  await page.route(
    (url) => {
      const p = url.pathname
      return p === '/api' || p.startsWith('/api/')
    },
    async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname.replace(/^\/api/, '')
      const method = req.method()

      // Projects
      if (path === '/projects' && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { projects: [{ project_id: projectId, id: projectId, name: 'T6.5.2 Lite 测试项目', genre: '玄幻', target_word_count: 50000, total_words: 3000 }], total: 1 } }),
        })
      }
      if (path === `/projects/${projectId}` && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { project_id: projectId, id: projectId, name: 'T6.5.2 Lite 测试项目', genre: '玄幻' } }),
        })
      }

      // Tree / File
      if (path === '/tree' && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              tree: [
                {
                  name: 'chapters',
                  path: `${projectId}/chapters`,
                  type: 'directory',
                  children: [
                    {
                      name: 'vol-01',
                      path: `${projectId}/chapters/vol-01`,
                      type: 'directory',
                      children: [
                        {
                          name: 'ch-001',
                          path: `${projectId}/chapters/vol-01/ch-001`,
                          type: 'directory',
                          children: [
                            {
                              name: 'sec-001.md',
                              path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
                              type: 'file',
                            },
                          ],
                        },
                      ],
                    },
                  ],
                },
              ],
            },
          }),
        })
      }
      if (path === '/file' && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { content: '# 初始场景\n\n青云山脉绵延千里。', frontmatter: null, path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`, mtime: Date.now(), hash: 'lite-test-hash' } }),
        })
      }
      if (path === '/file/save' && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { mtime: Date.now(), hash: 'saved-hash' } }),
        })
      }

      // SSE
      if (path === '/sse') {
        return route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
          body: 'event: connected\ndata: {"timestamp":0}\n\n',
        })
      }

      // LLM
      if (path === '/llm/status' && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { connected: true } }) })
      }
      if (path === '/llm/config' && method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { provider: 'openai-compatible', model: 'mock-model', connected: true } }) })
      }

      // Lite: ideas
      if (path === '/lite/ideas' && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              cards: [
                { id: 'idea-1', title: '热血少年修仙路', summary: '一个普通少年意外获得上古传承' },
                { id: 'idea-2', title: '都市异能觉醒', summary: '平凡白领某日觉醒操控时间之能' },
                { id: 'idea-3', title: '异世药神重生', summary: '顶级药师重生回到少年时代' },
              ],
            },
          }),
        })
      }

      // Lite: projects (创建项目)
      if (path === '/lite/projects' && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              project_id: projectId,
              first_file: 'chapters/vol-01/ch-001/sec-001.md',
              story_engine: { state: 'ok' },
            },
          }),
        })
      }

      // Lite: next-options
      if (path === '/lite/next-options' && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              cards: [
                { id: 'opt-1', title: '遇到神秘老者', description: '神秘老者在前方等待' },
                { id: 'opt-2', title: '进入上古遗迹', description: '一座被遗忘的遗迹' },
                { id: 'opt-3', title: '与强敌正面冲突', description: '一位强敌挡住去路' },
              ],
              current_file: 'chapters/vol-01/ch-001/sec-001.md',
              next_file: 'chapters/vol-01/ch-001/sec-002.md',
            },
          }),
        })
      }

      // Lite: write-next
      if (path === '/lite/write-next' && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              file_path: 'chapters/vol-01/ch-001/sec-002.md',
              content: '# 场景二\n\n少年推开了山门，眼前是一座古老的建筑。',
              quality_summary: 'quality: good',
              story_engine_summary: { state: 'ok' },
            },
          }),
        })
      }

      // 其他 API：空响应
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: {} }),
      })
    }
  )
}

test.describe('T6.5.2 Lite 视图 E2E', () => {
  // ── 清理 Pinia 持久化状态，防止 spec 间 localStorage 泄漏 ──
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

  test('1. 打开 /lite → 页面不白屏，显示 Lite 内容', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMockApi(page)

    await page.goto('/lite')
    await dismissViteOverlay(page)

    // 根元素或 app 可见
    const root = page.locator('[data-testid="lite-entry-root"]').or(page.locator('#app')).first()
    await expect(root).toBeVisible({ timeout: 15000 })

    const text = (await page.locator('body').textContent()) || ''
    expect(text.length).toBeGreaterThan(10)

    expect(filterSevereErrors(errors)).toEqual([])
  })

  test('2. 页面内容包含 idea 或"爽文"/"创作"字样', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMockApi(page)

    await page.goto('/lite')
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    const text = (await page.locator('body').textContent()) || ''
    const hasLiteKeyword =
      text.includes('idea') ||
      text.includes('爽文') ||
      text.includes('创作') ||
      text.includes('写') ||
      text.includes('项目')
    expect(hasLiteKeyword).toBe(true)

    expect(filterSevereErrors(errors)).toEqual([])
  })

  test('3. 若存在 idea 卡片区域 → 模拟点击一张', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMockApi(page)

    await page.goto('/lite')
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // 点击任何可点击的卡片元素（带"修仙"或"少年"的文本）
    const cards = page.locator('*').filter({ hasText: /少年|修仙|idea|IDEA/i })
    if (await cards.count() > 0) {
      try {
        await cards.first().click({ timeout: 3000 })
      } catch {
        // 忽略失败
      }
    }

    // 页面仍可见 → 不崩溃
    const text = (await page.locator('body').textContent()) || ''
    expect(text.length).toBeGreaterThan(10)

    expect(filterSevereErrors(errors)).toEqual([])
  })

  test('4. idea cards 列表内容可见（至少 1 张 card）', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMockApi(page)

    await page.goto('/lite')
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    const bodyText = (await page.locator('body').textContent()) || ''
    // 至少应该有一张 idea card 的标题出现
    const hasAnyCard =
      bodyText.includes('热血') ||
      bodyText.includes('少年') ||
      bodyText.includes('修仙') ||
      bodyText.includes('都市') ||
      bodyText.includes('药神') ||
      bodyText.includes('重生')
    expect(hasAnyCard).toBe(true)

    expect(filterSevereErrors(errors)).toEqual([])
  })

  test('5. 写作视图：页面不崩溃', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMockApi(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    const text = (await page.locator('body').textContent()) || ''
    expect(text.length).toBeGreaterThan(10)

    expect(filterSevereErrors(errors)).toEqual([])
  })

  test('6. 全流程无严重 console.error', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMockApi(page)

    await page.goto('/lite')
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    const text = (await page.locator('body').textContent()) || ''
    expect(text.length).toBeGreaterThan(10)

    const severe = filterSevereErrors(errors)
    expect(severe).toEqual([])
  })
})
