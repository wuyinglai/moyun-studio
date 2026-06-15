import { test, expect, type Page } from '@playwright/test'
import { openMainEntry } from './helpers/entryHelpers'

const projectId = 'e2e-title-project'
const generatedIdea = '# E2E Book Idea\n\nGenerated title content from create flow.'

async function installCreateProjectMocks(page: Page, generationRequests: unknown[]) {
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
      await ok({ projects: [], total: 0 })
    } else if (path === '/projects' && method === 'POST') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: 'E2E Create Flow',
        genre: '修仙',
        tone: '',
        background: '',
        theme: '',
        writing_style: '',
        target_word_count: 50000,
        total_words: 0,
      })
    } else if (path === `/projects/${projectId}` && method === 'GET') {
      await ok({
        project_id: projectId,
        id: projectId,
        name: 'E2E Create Flow',
        genre: '修仙',
        target_word_count: 50000,
        total_words: 0,
      })
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
    } else if (path === '/file/create' && method === 'POST') {
      await ok({ path: '书名与创意.md' })
    } else if (path === '/tree' && method === 'GET') {
      await ok({
        tree: [
          { name: '书名与创意.md', path: `${projectId}/书名与创意.md`, type: 'file' },
          { name: 'style-guide.md', path: `${projectId}/style-guide.md`, type: 'file' },
        ],
      })
    } else if (path === '/file' && method === 'GET') {
      await ok({
        content: '',
        frontmatter: null,
        path: '书名与创意.md',
        mtime: Date.now(),
        hash: 'empty',
      })
    } else if (path === '/generate' && method === 'POST') {
      generationRequests.push(request.postDataJSON())
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body:
          'event: prompt\ndata: {"prompt":"mock prompt","task_id":"gen-title"}\n\n' +
          `event: generation\ndata: ${JSON.stringify({ delta: generatedIdea, task_id: 'gen-title' })}\n\n` +
          'event: done\ndata: {"task_id":"gen-title","message":"done"}\n\n',
      })
    } else {
      await ok({})
    }
  })
}

test.describe('create project title generation flow', () => {
  // ── 清理 Pinia 持久化状态，防止 spec 间 localStorage 泄漏 ──
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

  test('streams the first generated idea into the editor, not the chat panel', async ({ page }) => {
    const generationRequests: unknown[] = []
    await installCreateProjectMocks(page, generationRequests)

    await openMainEntry(page)
    await page.getByTitle('新建项目').click()
    await page.getByTestId('create-project-name-input').fill('E2E Create Flow')
    await page.locator('.ant-radio-button-wrapper', { hasText: '修仙' }).first().click()
    await page.getByTestId('create-project-submit').click()

    await expect(page).toHaveURL(new RegExp(`/project/${projectId}$`))
    await expect(page.locator('.tab.active')).toContainText('书名与创意.md')
    await expect(page.locator('[data-testid="codemirror-container"]')).toContainText('E2E Book Idea')
    await expect(page.locator('.chat-panel')).not.toContainText('E2E Book Idea')

    expect(generationRequests).toHaveLength(1)
    expect(generationRequests[0]).toMatchObject({
      project_id: projectId,
      file_path: '书名与创意.md',
      prompt_type: 'generate/title',
      mode: 'append',
      stream: true,
    })
  })

  test('regenerates the title file with the title prompt even when old metadata is stale', async ({ page }) => {
    const generationRequests: unknown[] = []
    await page.addInitScript(({ projectId }) => {
      localStorage.setItem('fileMeta', JSON.stringify({
        fileMetaMap: {
          [projectId]: {
            '书名与创意.md': {
              promptType: 'generate/continuation',
              extraVars: { user_prompt: 'stale continuation prompt' },
              generatedAt: new Date().toISOString(),
            },
          },
        },
      }))
    }, { projectId })
    await installCreateProjectMocks(page, generationRequests)

    await page.goto(`/project/${projectId}`)
    await page.getByText('书名与创意.md').first().click()
    await expect(page.locator('.tab.active')).toContainText('书名与创意.md')
    await page.getByRole('button', { name: '🔄 重新生成' }).click()
    await page.getByRole('button', { name: '确 定' }).click()

    await expect(page.locator('[data-testid="codemirror-container"]')).toContainText('E2E Book Idea')
    const request = generationRequests.at(-1)
    expect(request).toMatchObject({
      project_id: projectId,
      file_path: '书名与创意.md',
      prompt_type: 'generate/title',
      mode: 'append',
      stream: true,
      extra_vars: expect.objectContaining({
        genre: '修仙',
      }),
    })
  })
})
