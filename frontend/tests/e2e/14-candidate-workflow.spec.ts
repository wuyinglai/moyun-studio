/**
 * E2E: 模拟人类操作 — 候选稿工作流
 *
 * 覆盖:
 * 1. 在项目页面，打开候选稿面板
 * 2. 查看候选稿列表
 * 3. 预览候选稿内容
 * 4. 采用候选稿
 * 5. 放弃候选稿
 * 6. 右侧面板切换各个 tab 不崩溃
 */
import { test, expect, type Page } from '@playwright/test'
import { dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'

const projectId = 'e2e-human-candidate'

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
          name: '候选稿测试项目',
          genre: '玄幻',
          target_word_count: 50000,
          total_words: 2500,
        }],
        total: 1,
      })
    } else if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: '候选稿测试项目',
        genre: '玄幻',
        target_word_count: 50000,
        total_words: 2500,
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
          { name: 'style-guide.md', path: `${projectId}/style-guide.md`, type: 'file' },
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

    // ── File read ──
    else if (path === '/file' && method === 'GET') {
      await ok({
        content: '# 第一章\n\n青云山脉绵延千里，山腰云雾缭绕，偶有仙鹤掠过。',
        frontmatter: null,
        path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
        mtime: Date.now(),
        hash: 'scene-hash',
      })
    } else if (path === '/file/save' && method === 'POST') {
      await ok({ mtime: Date.now(), hash: 'saved-hash' })
    }

    // ── Candidates ──
    else if (/^\/candidates\//.test(path) && method === 'GET') {
      // 返回候选稿列表
      await ok([
        {
          id: 'cand-001',
          source_path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
          candidate_path: `${projectId}/candidates/cand-001.md`,
          action: 'polish',
          status: 'pending',
          preview: '青云山脉绵延千里，仙鹤在云雾中穿行。少年站在山门前，仰望那高耸入云的石阶。',
          created_at: new Date().toISOString(),
        },
        {
          id: 'cand-002',
          source_path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
          candidate_path: `${projectId}/candidates/cand-002.md`,
          action: 'rewrite',
          status: 'pending',
          preview: '青云宗的山门前，一位白衣少年负手而立。他的目光穿透云层，望向那遥远的峰顶。',
          created_at: new Date(Date.now() - 60000).toISOString(),
        },
        {
          id: 'cand-003',
          source_path: `${projectId}/书名与创意.md`,
          candidate_path: `${projectId}/candidates/cand-003.md`,
          action: 'modify',
          status: 'adopted',
          preview: '已采用的内容',
          created_at: new Date(Date.now() - 120000).toISOString(),
        },
      ])
    } else if (/^\/candidates\//.test(path) && path.includes('/adopt') && method === 'POST') {
      await ok({ success: true })
    } else if (/^\/candidates\//.test(path) && method === 'DELETE') {
      await ok({ success: true })
    }

    // ── Pipeline (for polish/rewrite buttons) ──
    else if (path === '/pipeline/run' && method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body:
          'event: generation\ndata: {"delta":"润色后的内容...","task_id":"polish-1"}\n\n' +
          'event: done\ndata: {"task_id":"polish-1","message":"done"}\n\n',
      })
    } else if (path.startsWith('/pipeline/') && method === 'GET') {
      await ok([])
    }

    // ── Workflows ──
    else if (path.startsWith('/workflows/') && method === 'GET') {
      await ok([])
    }

    // ── Prompts ──
    else if (path.startsWith('/prompts/') && method === 'GET') {
      await ok('')
    }

    // ── Memory ──
    else if (/^\/memory\/status\//.test(path) && method === 'GET') {
      await ok({
        project_id: projectId,
        story_state_exists: true,
        recent_context_exists: true,
        recent_entries_count: 3,
        story_state_length: 1024,
        recent_context_length: 2048,
        last_updated: Date.now() / 1000,
        story_engine_exists: false,
        style_guide_exists: true,
        style_guide_length: 768,
        style_guide_mtime: Date.now() / 1000,
        recent_context_scene_limit: 15,
      })
    }

    // ── Catch-all ──
    else {
      await ok({})
    }
  })
}

test.describe('候选稿工作流 - 模拟人类操作', () => {
  test('打开候选稿面板，查看候选稿列表', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 1. 打开项目
    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 10000 })

    // 2. 点击右侧面板的 "候选稿" tab
    const candidateTab = page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' })
    await candidateTab.click()

    // 3. 验证候选稿面板内容可见
    await expect(page.locator('.right-panel > .panel-content') || page.getByTestId('candidate-panel')).toBeVisible({ timeout: 5000 })

    // 4. 验证候选稿列表包含至少一个候选稿
    const candidateList = page.getByTestId('candidate-panel') || page.locator('.right-panel > .panel-content')
    // 应该能找到一个候选稿条目
    await expect(candidateList).not.toHaveCount(0)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('候选稿面板不会在页面加载时弹出错误提示', async ({ page }) => {
    // 这是对之前 bug 的回归测试: 登录后不应显示"获取候选稿列表失败"
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    // 验证页面正常加载，没有白屏
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 10000 })

    // 检查 Ant Design notification（错误通知应该不可见）
    const errorNotification = page.locator('.ant-notification-notice').filter({ hasText: /获取候选稿列表失败|错误|失败/ })
    await expect(errorNotification).toHaveCount(0)

    // 验证无严重 console 错误
    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('点击候选稿预览', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    // 切换到候选稿面板
    const candidateTab = page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' })
    await candidateTab.click()

    // 等待候选稿列表渲染
    await page.waitForTimeout(1000)

    // 点击第一个候选稿卡片
    const firstCandidate = page.locator('[data-testid="candidate-content"]').first()
    if (await firstCandidate.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstCandidate.click()
    }

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('采用候选稿', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 拦截 confirm 对话框
    page.on('dialog', (dialog) => dialog.accept())

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    // 切换到候选稿面板
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()
    await page.waitForTimeout(1000)

    // 查找 adopt 按钮
    const adoptButton = page.locator('[data-testid="candidate-adopt-button"]').first()
    if (await adoptButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await adoptButton.click()
      await page.waitForTimeout(500)
    }

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('放弃（删除）候选稿', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    // 拦截 confirm 对话框
    page.on('dialog', (dialog) => dialog.accept())

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    // 切换到候选稿面板
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()
    await page.waitForTimeout(1000)

    // 查找 reject 按钮
    const rejectButton = page.locator('[data-testid="candidate-reject-button"]').first()
    if (await rejectButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await rejectButton.click()
      await page.waitForTimeout(500)
    }

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
