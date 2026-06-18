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

type MockOptions = {
  failNextRevision?: boolean
  adoptConflict?: boolean
}

type MockState = {
  candidates: Array<Record<string, unknown>>
  revisionPayloads: Array<Record<string, unknown>>
  adoptCalls: number
  deleteCalls: number
  fileSaveCalls: number
  sseEvents: Array<Record<string, unknown>>
}

async function installMocks(page: Page, options: MockOptions = {}): Promise<MockState> {
  let failRevisionResponses = options.failNextRevision ? 3 : 0
  let revisionCounter = 0
  const candidates: Array<Record<string, unknown>> = [
    {
      id: 'cand-001',
      source_path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
      candidate_path: `${projectId}/candidates/cand-001.md`,
      action: 'polish',
      status: 'pending',
      preview: '青云山脉绵延千里，仙鹤在云雾中穿行。少年站在山门前，仰望那高耸入云的石阶。',
      created_at: new Date().toISOString(),
      generation_context: {
        required_beats_input: [{ id: 'beat-1', text: '正文必须提到第七层协议' }],
        forbidden_beats_input: [{ id: 'forbid-1', text: '不能揭晓第七层协议完整真相' }],
      },
      beat_validation: {
        enabled: true,
        status: 'warning',
        summary: '发现 1 个可能缺失的信息点',
        required_beats: [{ id: 'beat-1', text: '正文必须提到第七层协议', status: 'missing' }],
        forbidden_beats: [],
      },
      continuity_anchors: {
        enabled: true,
        used_count: 2,
        anchor_ids: ['anchor-1', 'anchor-2'],
        types: { character_state: 1, object_location: 1 },
      },
      quality: {
        instruction_following: 'warning',
        continuity: 'pass',
        style_preservation: 'pass',
        change_scope: 'medium',
        forbidden_check: 'pass',
        notes: ['beat validation warning'],
      },
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
    {
      id: 'cand-004',
      source_path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
      candidate_path: `${projectId}/candidates/cand-004.md`,
      action: 'continue',
      status: 'pending',
      preview: '续写内容...',
      created_at: new Date(Date.now() - 180000).toISOString(),
      beat_validation: {
        enabled: true,
        status: 'unknown',
        summary: '信息点检查未能完成',
        required_beats: [{ id: 'beat-1', text: '正文必须提到第七层协议', status: 'unknown' }],
        forbidden_beats: [],
      },
    },
    {
      id: 'cand-005',
      source_path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
      candidate_path: `${projectId}/candidates/cand-005.md`,
      action: 'repair',
      status: 'pending',
      preview: '修复后内容...',
      created_at: new Date(Date.now() - 60000).toISOString(),
      parent_candidate_id: 'cand-001',
      revision_group_id: 'revgrp_test01',
      revision_index: 1,
      quality: {
        instruction_following: 'pass',
        continuity: 'pass',
        style_preservation: 'unknown',
        change_scope: 'small',
        forbidden_check: 'pass',
        notes: [],
      },
    },
  ]
  const state: MockState = {
    candidates,
    revisionPayloads: [],
    adoptCalls: 0,
    deleteCalls: 0,
    fileSaveCalls: 0,
    sseEvents: [
      {
        event: 'file.updated',
        data: {
          type: 'file.updated',
          project_id: projectId,
          payload: {
            path: `${projectId}/chapters/vol-01/ch-001/sec-001.md`,
            size: 120,
            mtime: 123456,
          },
        },
      },
      {
        event: 'candidate-created',
        data: {
          type: 'candidate-created',
          project_id: projectId,
          payload: {
            candidate_id: 'cand-sse-safe',
            source_path: 'chapters/vol-01/ch-001/sec-001.md',
            action: 'rewrite',
          },
        },
      },
    ],
  }
  const findCandidate = (candidateId: string) => candidates.find((item) => item.id === candidateId)

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
      const sseBody = [
        'event: connected\ndata: {"timestamp":0}\n\n',
        ...state.sseEvents.map((item) => `event: ${item.event}\ndata: ${JSON.stringify(item.data)}\n\n`),
      ].join('')
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: sseBody,
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
      state.fileSaveCalls += 1
      await ok({ mtime: Date.now(), hash: 'saved-hash' })
    }

    // ── Candidates ──
    else if (/^\/candidates\/.+\/.+\/revise$/.test(path) && method === 'POST') {
      const payload = request.postDataJSON() as {
        feedback_text?: string
        quick_actions?: string[]
        repair_scope?: string
      } | null
      expect(payload?.feedback_text || payload?.quick_actions?.length).toBeTruthy()
      state.revisionPayloads.push((payload || {}) as Record<string, unknown>)
      if (failRevisionResponses > 0) {
        failRevisionResponses -= 1
        await route.fulfill({
          status: 502,
          contentType: 'application/json',
          body: JSON.stringify({ success: false, error: { code: 'LLM_ERROR', message: 'mock llm failed' } }),
        })
        return
      }
      const parentId = path.split('/').at(-2) || 'cand-001'
      const parent = findCandidate(parentId)
      const parentContext = (parent?.generation_context || {}) as Record<string, unknown>
      const revisionGroupId = String(parent?.revision_group_id || parentContext.revision_group_id || 'revgrp-e2e')
      revisionCounter += 1
      const childId = `cand-rev-${String(revisionCounter).padStart(3, '0')}`
      const child = {
        id: childId,
        source_path: parent?.source_path || 'chapters/vol-01/ch-001/sec-001.md',
        candidate_path: `${projectId}/.candidates/${childId}.feedback_revision.md`,
        action: 'feedback_revision',
        status: 'pending',
        parent_candidate_id: parentId,
        revision_group_id: revisionGroupId,
        revision_index: revisionCounter,
        generation_context: {
          revision_type: 'feedback_revision',
          parent_candidate_id: parentId,
          feedback_text: payload?.feedback_text || '',
          quick_actions: payload?.quick_actions || [],
          repair_scope: payload?.repair_scope || 'full_candidate',
          required_beats_input: parentContext.required_beats_input || [],
          forbidden_beats_input: parentContext.forbidden_beats_input || [],
          revision_group_id: revisionGroupId,
          revision_index: revisionCounter,
        },
        beat_validation: parent?.beat_validation || {},
        created_at: new Date().toISOString(),
        word_count: 42,
      }
      candidates.unshift(child)
      await ok(child)
    } else if (/^\/candidates\/[^/]+\/[^/]+$/.test(path) && method === 'GET') {
      const candidateId = path.split('/').pop() || 'cand-001'
      const candidate = findCandidate(candidateId)
      await ok({
        candidate: {
          ...candidate,
          id: candidateId,
          source_path: String(candidate?.source_path || 'chapters/vol-01/ch-001/sec-001.md'),
          candidate_path: String(candidate?.candidate_path || `${projectId}/candidates/${candidateId}.md`),
          action: String(candidate?.action || 'polish'),
          status: String(candidate?.status || 'pending'),
          created_at: String(candidate?.created_at || new Date().toISOString()),
          word_count: Number(candidate?.word_count || 42),
        },
        content: '候选稿预览正文',
      })
    } else if (/^\/candidates\//.test(path) && method === 'GET') {
      await ok({ candidates })
    } else if (/^\/candidates\//.test(path) && path.includes('/adopt') && method === 'POST') {
      state.adoptCalls += 1
      if (options.adoptConflict) {
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            error: {
              code: 'FILE_CONFLICT',
              message: 'source file changed before candidate adoption',
            },
          }),
        })
        return
      }
      await ok({ success: true })
    } else if (/^\/candidates\//.test(path) && method === 'DELETE') {
      state.deleteCalls += 1
      const candidateId = path.split('/').at(-1) || ''
      const candidate = findCandidate(candidateId)
      if (candidate) candidate.status = 'discarded'
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
  return state
}

test.describe('候选稿工作流 - 模拟人类操作', () => {
  // ── 清理 Pinia 持久化状态，防止 spec 间 localStorage 泄漏 ──
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

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

  test('T6.9.2: 候选稿面板顶部有安全说明（不会自动覆盖正文）', async ({ page }) => {
    await installMocks(page)
    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    // 切换到候选稿面板
    const candidateTab = page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' })
    await candidateTab.click()

    // 验证安全说明文案
    const notice = page.locator('.candidate-notice')
    await expect(notice).toBeVisible({ timeout: 5000 })
    await expect(notice).toContainText('不会自动覆盖正文')
    await expect(notice).toContainText('可以先预览')
    console.log('[t6.9.2] ✓ candidate-notice 文案存在且包含安全说明')
  })

  test('T8.5-mini: pending 候选稿可以按反馈再生成 child candidate', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)

    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()
    await expect(page.getByTestId('candidate-revise-button').first()).toBeVisible({ timeout: 5000 })

    await page.getByTestId('candidate-revise-button').first().click()
    await expect(page.getByTestId('candidate-revision-feedback')).toBeVisible({ timeout: 5000 })
    await page.getByTestId('candidate-revision-feedback').fill('加强冲突，不要新增人物')
    await page.getByTestId('candidate-revision-submit').click()

    await expect(page.locator('[data-testid="candidate-revision-summary"]').first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator('[data-testid="candidate-revision-summary"]').first()).toContainText('第 1 版')

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

    // T6.9.2: 预览弹窗应显示"不会修改正文"说明
    const previewModal = page.locator('.preview-modal')
    if (await previewModal.isVisible({ timeout: 5000 }).catch(() => false)) {
      const previewNotice = page.locator('.preview-notice')
      await expect(previewNotice).toBeVisible({ timeout: 3000 })
      await expect(previewNotice).toContainText('不会修改正文')
      console.log('[t6.9.2] ✓ preview-notice 文案存在且包含安全说明')
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

  test('T8.6: 空反馈且无快捷动作时不能提交 revision', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-revise-button').first().click()
    await expect(page.getByTestId('candidate-revision-feedback')).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('candidate-revision-submit')).toBeDisabled()
  })

  test('T8.6: adopted 候选稿不显示按反馈再生成按钮', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const adoptedCard = page.locator('.candidate-card').filter({ hasText: '已采用' })
    await expect(adoptedCard).toBeVisible({ timeout: 5000 })
    await expect(adoptedCard.getByTestId('candidate-revise-button')).toHaveCount(0)
  })

  test('T8.6: feedback revision 展示来源、轮次和反馈摘要', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-revise-button').first().click()
    await page.getByTestId('candidate-revision-feedback').fill('保留开头，只改结尾，加强画面感')
    await page.getByTestId('candidate-revision-submit').click()

    const revisionCard = page.locator('.candidate-card').filter({ hasText: '反馈修订稿' }).first()
    await expect(revisionCard.getByTestId('candidate-revision-summary')).toContainText('第 1 版', { timeout: 5000 })
    await expect(revisionCard.getByTestId('candidate-revision-summary')).toContainText('保留开头')
  })

  test('T8.6: revision LLM 失败后 modal 保持打开并可重试', async ({ page }) => {
    const errors = createErrorCollector(page)
    await installMocks(page, { failNextRevision: true })

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-revise-button').first().click()
    await page.getByTestId('candidate-revision-feedback').fill('第一次会失败')
    await page.getByTestId('candidate-revision-submit').click()

    await expect(page.getByTestId('candidate-revision-feedback')).toBeVisible({ timeout: 5000 })
    await page.getByTestId('candidate-revision-feedback').fill('重试后生成')
    await page.getByTestId('candidate-revision-submit').click()

    await expect(page.locator('.candidate-card').filter({ hasText: '反馈修订稿' })).toBeVisible({ timeout: 5000 })

    const severeErrors = filterSevereErrors(errors).filter((message) => !message.includes('status of 502'))
    expect(severeErrors).toEqual([])
  })

  test('T8.6: parent 有 required beats 时 modal 显示继承检查数量', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-revise-button').first().click()
    await expect(page.getByTestId('candidate-revision-beat-inheritance')).toContainText('必须信息点', { timeout: 5000 })
    await expect(page.getByTestId('candidate-revision-beat-inheritance')).toContainText('禁止项')
  })

  test('T8.7: 质量检查区展示 beat warning 状态和缺失详情', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const qualitySection = page.locator('[data-testid="candidate-quality-section"]').first()
    await expect(qualitySection).toBeVisible({ timeout: 5000 })
    await expect(qualitySection).toContainText('信息点有警告')
    await expect(qualitySection).toContainText('正文必须提到第七层协议')
    console.log('[t8.7] ✓ quality section shows warning + missing beat detail')
  })

  test('T9.3: 候选稿质量区展示已使用连续性锚点数量', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const anchorInfo = page.getByTestId('candidate-continuity-anchor-count').first()
    await expect(anchorInfo).toBeVisible({ timeout: 5000 })
    await expect(anchorInfo).toContainText('连续性锚点')
    await expect(anchorInfo).toContainText('2')
  })

  test('T8.7: 质量检查区展示 unknown 状态并说明不影响采用', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const unknownQuality = page.locator('.quality-item.quality-unknown')
    await expect(unknownQuality).toBeVisible({ timeout: 5000 })
    await expect(unknownQuality).toContainText('不影响采用')
    console.log('[t8.7] ✓ quality section shows unknown state with advisory text')
  })

  test('T8.7: 反馈再生成 modal 说明不会覆盖正文', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-revise-button').first().click()
    const modal = page.locator('.revision-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })
    await expect(modal.locator('.revision-notice')).toContainText('不会覆盖正文')
    console.log('[t8.7] ✓ revision modal copy mentions no overwrite')
  })

  test('T8.7: 无 beat_validation 的候选稿不展示质量检查区', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-002 has no beat_validation, no continuity, no warning_message
    const cand002Card = page.locator('.candidate-card').filter({ hasText: '重写' }).first()
    await expect(cand002Card).toBeVisible({ timeout: 5000 })
    await expect(cand002Card.locator('[data-testid="candidate-quality-section"]')).toHaveCount(0)
    console.log('[t8.7] ✓ quality section hidden for candidate without validation data')
  })
  test('T9.2b: candidate SSE events do not expose full content', async ({ page }) => {
    const state = await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 10000 })

    expect(state.sseEvents.length).toBeGreaterThanOrEqual(2)
    for (const event of state.sseEvents) {
      expect(JSON.stringify(event)).not.toContain('"content"')
      expect((event.data as { project_id?: string }).project_id).toBe(projectId)
    }
  })

  test('T9.2b: cancelling warning adopt does not call adopt API', async ({ page }) => {
    const state = await installMocks(page)
    page.on('dialog', (dialog) => dialog.dismiss())

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').nth(4).click()

    await page.locator('[data-testid="candidate-adopt-button"]').first().click()
    expect(state.adoptCalls).toBe(0)
    expect(state.fileSaveCalls).toBe(0)
  })

  test('T9.2b: FILE_CONFLICT on adopt keeps candidate pending and does not save source', async ({ page }) => {
    const state = await installMocks(page, { adoptConflict: true })
    page.on('dialog', (dialog) => dialog.accept())

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').nth(4).click()

    await page.locator('[data-testid="candidate-adopt-button"]').first().click()
    await expect.poll(() => state.adoptCalls).toBe(1)
    expect(state.fileSaveCalls).toBe(0)
    expect(state.candidates.find((candidate) => candidate.id === 'cand-001')?.status).toBe('pending')
  })

  test('T9.2b: deleting candidate does not write official scene file', async ({ page }) => {
    const state = await installMocks(page)
    page.on('dialog', (dialog) => dialog.accept())

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').nth(4).click()

    await page.locator('[data-testid="candidate-reject-button"]').first().click()
    await expect.poll(() => state.deleteCalls).toBe(1)
    expect(state.fileSaveCalls).toBe(0)
  })

  test('T9.2b: feedback revision request preserves safety metadata flags', async ({ page }) => {
    const state = await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').nth(4).click()

    await page.getByTestId('candidate-revise-button').first().click()
    await page.getByTestId('candidate-revision-feedback').fill('keep the ending suspense and preserve satisfied beats')
    await page.getByTestId('candidate-revision-submit').click()

    await expect.poll(() => state.revisionPayloads.length).toBe(1)
    expect(state.revisionPayloads[0]).toMatchObject({
      feedback_text: 'keep the ending suspense and preserve satisfied beats',
      repair_scope: 'full_candidate',
      inherit_required_beats: true,
      inherit_forbidden_beats: true,
      run_beat_validation: true,
    })
  })

  test('T9.2b: quick feedback action alone can create a safe revision candidate', async ({ page }) => {
    const state = await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').nth(4).click()

    await page.getByTestId('candidate-revise-button').first().click()
    await page.locator('.revision-quick-actions button').first().click()
    await expect(page.getByTestId('candidate-revision-submit')).toBeEnabled()
    await page.getByTestId('candidate-revision-submit').click()

    await expect.poll(() => state.revisionPayloads.length).toBe(1)
    expect(state.revisionPayloads[0].feedback_text).toBe('')
    expect(state.revisionPayloads[0].quick_actions).toEqual(expect.arrayContaining([expect.any(String)]))
    expect(state.fileSaveCalls).toBe(0)
  })

  // ── T10.1b: Quality Explanation UI ──────────────────────────────

  test('T10.1b: quality explanation toggle visible for candidate with quality metadata', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const toggle = page.getByTestId('candidate-quality-explanation-toggle').first()
    await expect(toggle).toBeVisible({ timeout: 5000 })
    await expect(toggle).toContainText('质量提示')
    console.log('[t10.1b] ✓ quality explanation toggle visible with collapsed text')
  })

  test('T10.1b: quality explanation expands to show 5 dimensions on click', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const toggle = page.getByTestId('candidate-quality-explanation-toggle').first()
    await toggle.click()

    const body = page.getByTestId('candidate-quality-explanation-body').first()
    await expect(body).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('quality-dimension-instruction_following')).toBeVisible()
    await expect(page.getByTestId('quality-dimension-continuity')).toBeVisible()
    await expect(page.getByTestId('quality-dimension-style_preservation')).toBeVisible()
    await expect(page.getByTestId('quality-dimension-change_scope')).toBeVisible()
    await expect(page.getByTestId('quality-dimension-forbidden_check')).toBeVisible()
    console.log('[t10.1b] ✓ 5 quality dimensions visible after expand')
  })

  test('T10.1b: quality explanation uses correct status labels (pass/warning/unknown)', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-quality-explanation-toggle').first().click()

    // cand-001 has instruction_following=warning
    const instructionDim = page.getByTestId('quality-dimension-instruction_following')
    await expect(instructionDim).toContainText('需注意')

    // cand-001 has continuity=pass
    const continuityDim = page.getByTestId('quality-dimension-continuity')
    await expect(continuityDim).toContainText('通过')

    // cand-001 has change_scope=medium → "变化适中"
    const changeDim = page.getByTestId('quality-dimension-change_scope')
    await expect(changeDim).toContainText('变化适中')
    console.log('[t10.1b] ✓ status labels use user-friendly copy (pass/warning)')
  })

  test('T10.1b: repair explanation shown when candidate has instruction_following warning', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-quality-explanation-toggle').first().click()

    const repairExpl = page.getByTestId('candidate-repair-explanation')
    await expect(repairExpl).toBeVisible({ timeout: 5000 })
    await expect(repairExpl).toContainText('修复候选稿')
    await expect(repairExpl).toContainText('不会自动采纳')
    console.log('[t10.1b] ✓ repair explanation visible with safety note')
  })

  test('T10.1b: safety text always visible in expanded quality explanation', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-quality-explanation-toggle').first().click()

    const safetyText = page.getByTestId('candidate-safety-text')
    await expect(safetyText).toBeVisible({ timeout: 5000 })
    await expect(safetyText).toContainText('所有质量提示仅供参考')
    await expect(safetyText).toContainText('不会自动修改正文')
    console.log('[t10.1b] ✓ candidate-only safety text present')
  })

  test('T10.1b: old candidate without quality metadata shows placeholder, not fake dimensions', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-002 has no quality metadata — should show placeholder
    const cand002Card = page.locator('.candidate-card').filter({ hasText: '重写' }).first()
    await expect(cand002Card).toBeVisible({ timeout: 5000 })
    const toggle = cand002Card.locator('[data-testid="candidate-quality-explanation-toggle"]')
    await expect(toggle).toContainText('暂无质量解释')

    // Expand and verify no fake dimensions are shown
    await toggle.click()
    await expect(cand002Card.locator('[data-testid="candidate-quality-explanation-empty"]')).toBeVisible()
    await expect(cand002Card.locator('[data-testid="quality-dimension-instruction_following"]')).toHaveCount(0)
    console.log('[t10.1b] ✓ old candidate shows placeholder, no fake dimensions')
  })

  test('T10.1b: quality explanation collapses on second click', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const toggle = page.getByTestId('candidate-quality-explanation-toggle').first()
    // Expand
    await toggle.click()
    await expect(page.getByTestId('candidate-quality-explanation-body').first()).toBeVisible()
    // Collapse
    await toggle.click()
    await expect(page.getByTestId('candidate-quality-explanation-body').first()).toHaveCount(0)
    console.log('[t10.1b] ✓ quality explanation collapses on second click')
  })

  // ── T10.2b: Candidate Compare MVP ──────────────────────────────

  test('T10.2b: compare button is visible on candidate cards', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    const compareBtn = page.getByTestId('candidate-compare-button').first()
    await expect(compareBtn).toBeVisible({ timeout: 5000 })
    await expect(compareBtn).toHaveAttribute('title', '比较差异')
    console.log('[t10.2b] ✓ compare button visible with correct title')
  })

  test('T10.2b: clicking compare opens modal with correct labels (mode A)', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // Click compare on cand-002 (no parent → mode A)
    const cand002Card = page.locator('.candidate-card').filter({ hasText: '重写' }).first()
    await cand002Card.getByTestId('candidate-compare-button').click()

    const modal = page.getByTestId('compare-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })
    await expect(modal).toContainText('候选稿比较')
    await expect(modal).toContainText('当前正文')
    await expect(modal).toContainText('重写候选稿')
    console.log('[t10.2b] ✓ mode A: modal shows 当前正文 vs 重写候选稿')
  })

  test('T10.2b: compare modal shows safety notice and no adopt button', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-compare-button').first().click()

    const modal = page.getByTestId('compare-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })
    await expect(modal).toContainText('比较视图仅用于查看差异')
    await expect(modal).toContainText('不会修改正文')
    // Verify no adopt button in modal
    await expect(modal.locator('button').filter({ hasText: '采用' })).toHaveCount(0)
    console.log('[t10.2b] ✓ safety notice present, no adopt button in compare modal')
  })

  test('T10.2b: repair child compare shows parent vs child labels (mode B)', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // Click compare on cand-005 (repair child of cand-001 → mode B)
    const cand005Card = page.locator('.candidate-card').filter({ hasText: '修复版' }).first()
    await cand005Card.getByTestId('candidate-compare-button').click()

    const modal = page.getByTestId('compare-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })
    await expect(modal).toContainText('父候选稿')
    await expect(modal).toContainText('修复版候选稿')
    console.log('[t10.2b] ✓ mode B: repair child shows 父候选稿 vs 修复版候选稿')
  })

  test('T10.2b: compare modal shows diff area and summary', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-compare-button').first().click()

    const modal = page.getByTestId('compare-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })
    await expect(modal.getByTestId('compare-diff-area')).toBeVisible({ timeout: 5000 })
    await expect(modal.getByTestId('compare-summary')).toBeVisible()
    console.log('[t10.2b] ✓ diff area and summary visible')
  })

  test('T10.2b: compare modal close button works', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    await page.getByTestId('candidate-compare-button').first().click()
    await expect(page.getByTestId('compare-modal')).toBeVisible({ timeout: 5000 })

    await page.getByTestId('compare-modal').locator('button').filter({ hasText: '关闭' }).click()
    await expect(page.getByTestId('compare-modal')).toHaveCount(0)
    console.log('[t10.2b] ✓ compare modal closes on button click')
  })

  test('T10.2b: adopted candidate can still open compare', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-003 is adopted
    const cand003Card = page.locator('.candidate-card').filter({ hasText: '已采用' }).first()
    await cand003Card.getByTestId('candidate-compare-button').click()

    const modal = page.getByTestId('compare-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })
    await expect(modal).toContainText('候选稿比较')
    console.log('[t10.2b] ✓ adopted candidate can open compare without changing status')
  })

  // ─── T10.3b: Candidate Decision Flow UI 验收测试 ──────────────────────────────────

  test('T10.3b: pending candidate shows primary/secondary/trailing action groups', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-001 is pending
    const cand001Card = page.locator('.candidate-card').filter({ hasText: '待处理' }).first()

    // Primary group: preview, compare, adopt
    await expect(cand001Card.locator('button[title="预览"]')).toBeVisible()
    await expect(cand001Card.getByTestId('candidate-compare-button')).toBeVisible()
    await expect(cand001Card.getByTestId('candidate-adopt-button')).toBeVisible()

    // Secondary group: revise, repair
    await expect(cand001Card.getByTestId('candidate-revise-button')).toBeVisible()
    await expect(cand001Card.getByTestId('candidate-repair-button')).toBeVisible()

    // Trailing group: delete
    await expect(cand001Card.getByTestId('candidate-reject-button')).toBeVisible()

    console.log('[t10.3b] ✓ pending candidate shows primary/secondary/trailing action groups')
  })

  test('T10.3b: adopted candidate shows preview/compare/delete but not adopt/revise/repair', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-003 is adopted
    const cand003Card = page.locator('.candidate-card').filter({ hasText: '已采用' }).first()

    // Primary group: preview, compare (adopt is hidden for adopted)
    await expect(cand003Card.locator('button[title="预览"]')).toBeVisible()
    await expect(cand003Card.getByTestId('candidate-compare-button')).toBeVisible()
    await expect(cand003Card.getByTestId('candidate-adopt-button')).toHaveCount(0)

    // Secondary group is hidden
    await expect(cand003Card.getByTestId('candidate-revise-button')).toHaveCount(0)
    await expect(cand003Card.getByTestId('candidate-repair-button')).toHaveCount(0)

    // Trailing group: delete is still visible
    await expect(cand003Card.getByTestId('candidate-reject-button')).toBeVisible()

    console.log('[t10.3b] ✓ adopted candidate shows preview/compare/delete but not adopt/revise/repair')
  })

  test('T10.3b: pending candidate with warning shows adopt hint', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-001 is pending with warning (instruction_following=warning)
    const cand001Card = page.locator('.candidate-card').filter({ hasText: '待处理' }).first()

    // Adopt hint should be visible for pending candidate with warning
    await expect(cand001Card.getByTestId('candidate-adopt-hint')).toBeVisible()
    await expect(cand001Card.getByTestId('candidate-adopt-hint')).toContainText('采纳前建议先查看质量提示和比较差异')

    console.log('[t10.3b] ✓ pending candidate with warning shows adopt hint')
  })

  test('T10.3b: pending candidate without warning does not show adopt hint', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-002 is pending without warning or quality data
    const cand002Card = page.locator('.candidate-card').filter({ hasText: '重写' }).nth(0)

    // Adopt hint should not be visible
    await expect(cand002Card.getByTestId('candidate-adopt-hint')).toHaveCount(0)

    console.log('[t10.3b] ✓ pending candidate without warning does not show adopt hint')
  })

  test('T10.3b: adopt hint does not block adopt action', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // cand-001 is pending with warning
    const cand001Card = page.locator('.candidate-card').filter({ hasText: '待处理' }).first()

    // Adopt button should still be visible and enabled
    const adoptButton = cand001Card.getByTestId('candidate-adopt-button')
    await expect(adoptButton).toBeVisible()
    await expect(adoptButton).toBeEnabled()

    // Adopt hint is present but does not disable adopt
    await expect(cand001Card.getByTestId('candidate-adopt-hint')).toBeVisible()

    console.log('[t10.3b] ✓ adopt hint does not block adopt action')
  })

  test('T10.3b: compare modal still has no adopt button', async ({ page }) => {
    await installMocks(page)

    await page.goto(`/project/${projectId}`)
    await dismissViteOverlay(page)
    await page.locator('.right-panel .panel-tab').filter({ hasText: '候选稿' }).click()

    // Open compare modal for any candidate
    await page.locator('.candidate-card').first().getByTestId('candidate-compare-button').click()

    const modal = page.getByTestId('compare-modal')
    await expect(modal).toBeVisible({ timeout: 5000 })

    // Compare modal should not have adopt button
    await expect(modal.getByTestId('candidate-adopt-button')).toHaveCount(0)
    await expect(modal.getByRole('button', { name: /采用|采纳/ })).toHaveCount(0)

    console.log('[t10.3b] ✓ compare modal still has no adopt button')
  })
})
