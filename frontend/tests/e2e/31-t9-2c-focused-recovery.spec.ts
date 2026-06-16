import { expect, test, type Page } from '@playwright/test'
import { dismissViteOverlay } from './helpers/e2eUtils'

const projectId = 't9-2c-project'
const scenePath = 'chapters/vol-01/ch-001/sec-001.md'
const nextScenePath = 'chapters/vol-01/ch-001/sec-002.md'

type Candidate = Record<string, unknown>

type T92cMockOptions = {
  pipelineError?: boolean
  fileSaveConflict?: boolean
  liteStreamError?: boolean
}

type T92cMockState = {
  candidates: Candidate[]
  pipelineCalls: Record<string, unknown>[]
  fileSavePayloads: Record<string, unknown>[]
  liteStreamCalls: Record<string, unknown>[]
  sourceContent: string
}

function apiOk(data: unknown) {
  return JSON.stringify({ success: true, data })
}

function sse(events: Array<{ event: string; data: unknown }>) {
  return events.map((item) => `event: ${item.event}\ndata: ${JSON.stringify(item.data)}\n\n`).join('')
}

function projectPayload() {
  return {
    id: projectId,
    project_id: projectId,
    name: 'T9.2c mock project',
    genre: 'test',
    target_word_count: 50000,
    total_words: 1600,
  }
}

function candidatePayload(id: string, action = 'rewrite'): Candidate {
  return {
    id,
    source_path: scenePath,
    candidate_path: `.candidates/${id}.md`,
    action,
    status: 'pending',
    source_type: 'ai',
    source_filename: 'sec-001.md',
    preview: `Candidate ${id} preview body`,
    created_at: new Date().toISOString(),
    word_count: 128,
  }
}

async function installT92cMockApi(page: Page, options: T92cMockOptions = {}): Promise<T92cMockState> {
  const state: T92cMockState = {
    candidates: [],
    pipelineCalls: [],
    fileSavePayloads: [],
    liteStreamCalls: [],
    sourceContent: '# Scene 1\n\nOriginal official scene content. The source file must remain unchanged until adopt.',
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

    const fulfillJson = async (data: unknown, status = 200) => {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: status >= 400 ? JSON.stringify(data) : apiOk(data),
      })
    }

    if (path === '/projects' && method === 'GET') {
      await fulfillJson({ projects: [projectPayload()], total: 1 })
      return
    }

    if (path === `/projects/${projectId}` && method === 'GET') {
      await fulfillJson(projectPayload())
      return
    }

    if (path === '/llm/config' && method === 'GET') {
      await fulfillJson({ provider: 'mock', model: 'mock-model', connected: true })
      return
    }

    if (path === '/llm/status' && method === 'GET') {
      await fulfillJson({ connected: true })
      return
    }

    if (path === '/config/custom-params' && method === 'GET') {
      await fulfillJson({})
      return
    }

    if (path === '/tree' && method === 'GET') {
      await fulfillJson({
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
                      { name: 'sec-001.md', path: scenePath, type: 'file' },
                      { name: 'sec-002.md', path: nextScenePath, type: 'file' },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      })
      return
    }

    if (path === '/file' && method === 'GET') {
      const requestedPath = url.searchParams.get('path') || scenePath
      const content = requestedPath.endsWith('sec-002.md')
        ? '# Scene 2\n\n'
        : requestedPath.endsWith('story-engine.md')
          ? '# Story engine\n\nCurrent conflict and memory.'
          : state.sourceContent
      await fulfillJson({
        path: requestedPath,
        content,
        frontmatter: null,
        mtime: 1001,
        hash: 'hash-before-save',
      })
      return
    }

    if ((path === '/file' || path === '/file/save') && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>
      state.fileSavePayloads.push(payload)
      if (options.fileSaveConflict) {
        await fulfillJson({
          success: false,
          error: {
            code: 'FILE_CONFLICT',
            message: 'File has changed on disk.',
          },
        }, 409)
        return
      }
      state.sourceContent = String(payload.content || '')
      await fulfillJson({ path: payload.path, content: payload.content, mtime: 1002, hash: 'hash-after-save' })
      return
    }

    if (path === '/pipeline/run' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>
      state.pipelineCalls.push(payload)

      if (options.pipelineError) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
          body: sse([{ event: 'error', data: { message: 'LLM_ERROR: mock pipeline failure' } }]),
        })
        return
      }

      const candidate = candidatePayload(`cand-t92c-${state.candidates.length + 1}`, String(payload.pipeline || 'rewrite'))
      state.candidates.unshift(candidate)
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: sse([
          { event: 'candidate-created', data: { project_id: projectId, payload: { candidate_id: candidate.id, source_path: scenePath } } },
          { event: 'done', data: { task_id: 'pipeline-t92c', message: 'done' } },
        ]),
      })
      return
    }

    if (path.startsWith('/pipeline/') && method === 'GET') {
      await fulfillJson({ name: path.split('/').pop(), steps: [] })
      return
    }

    if (path === '/lite/next-options' && method === 'POST') {
      await fulfillJson({
        current_file: scenePath,
        next_file: nextScenePath,
        cards: [
          {
            id: 'card-1',
            title: 'Mock beat',
            beat: 'Push the scene forward safely.',
            scene: 'A short mock scene direction.',
            protagonist_desire: 'Keep agency.',
            obstacle: 'Avoid continuity break.',
            payoff: 'A safe candidate is generated.',
            hook: 'End with a hook.',
            advancement: 'Move to the next scene.',
          },
        ],
      })
      return
    }

    if (path === '/lite/write-next-stream' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>
      state.liteStreamCalls.push(payload)
      if (options.liteStreamError) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
          body: sse([{ event: 'error', data: { message: 'LLM_ERROR: mock lite failure' } }]),
        })
        return
      }
      const candidatePath = 'chapters/vol-01/ch-001/.candidates/sec-001-rewrite.md'
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: sse([
          { event: 'meta', data: { file_path: candidatePath, label: 'candidate', source_file: scenePath, is_candidate: true, candidate_id: 'lite-cand-1' } },
          { event: 'delta', data: { delta: 'Lite candidate draft content.' } },
          {
            event: 'done',
            data: {
              file_path: candidatePath,
              content: '# Lite candidate\n\nLite candidate draft content.',
              quality_summary: 'Candidate generated.',
              story_engine_summary: {},
              source_file: scenePath,
              candidate_id: 'lite-cand-1',
            },
          },
        ]),
      })
      return
    }

    if (/^\/candidates\/[^/]+\/[^/]+$/.test(path) && method === 'GET') {
      const candidateId = path.split('/').pop() || ''
      const candidate = state.candidates.find((item) => item.id === candidateId) || candidatePayload(candidateId)
      await fulfillJson({ candidate, content: 'Candidate preview content.' })
      return
    }

    if (/^\/candidates\/[^/]+\/[^/]+\/adopt$/.test(path) && method === 'POST') {
      const candidateId = path.split('/').at(-2) || ''
      const candidate = state.candidates.find((item) => item.id === candidateId)
      if (candidate) candidate.status = 'adopted'
      state.sourceContent = '# Adopted\n\nCandidate preview content.'
      await fulfillJson({ success: true, file_path: scenePath })
      return
    }

    if (/^\/candidates\/[^/]+\/[^/]+$/.test(path) && method === 'DELETE') {
      const candidateId = path.split('/').pop() || ''
      const candidate = state.candidates.find((item) => item.id === candidateId)
      if (candidate) candidate.status = 'discarded'
      await fulfillJson({ success: true })
      return
    }

    if (/^\/candidates\//.test(path) && method === 'GET') {
      await fulfillJson({ candidates: state.candidates })
      return
    }

    if (path === '/sse') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: sse([{ event: 'connected', data: { timestamp: Date.now() } }]),
      })
      return
    }

    if (path.startsWith('/prompts/') || path.startsWith('/workflows/') || path.startsWith('/memory/status/')) {
      await fulfillJson({})
      return
    }

    await fulfillJson({})
  })

  return state
}

async function openProfessionalScene(page: Page) {
  await page.goto(`/project/${projectId}/file/${scenePath}`)
  await dismissViteOverlay(page)
  await expect(page.getByTestId('main-entry-root')).toBeVisible({ timeout: 10000 })
  await expect(page.getByTestId('editor-toolbar')).toBeVisible({ timeout: 10000 })
}

async function openCandidateTab(page: Page) {
  await page.locator('.right-panel .panel-tab').nth(4).click()
  await expect(page.getByTestId('candidate-panel')).toBeVisible({ timeout: 10000 })
}

test.describe('T9.2c focused E2E recovery batch 2', () => {
  test('Professional rewrite creates candidate and does not save official scene', async ({ page }) => {
    const state = await installT92cMockApi(page)
    await openProfessionalScene(page)

    await page.getByTestId('rewrite-button').click()
    await expect.poll(() => state.pipelineCalls.length).toBe(1)
    await expect.poll(() => state.candidates.length).toBe(1)

    expect(state.pipelineCalls[0]).toMatchObject({
      pipeline: 'rewrite',
      target_file: scenePath,
      output_mode: 'candidate',
    })
    expect(state.fileSavePayloads).toHaveLength(0)
    expect(state.sourceContent).toContain('Original official scene content')
    await expect(page.getByTestId('candidate-panel')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('candidate-content').first()).toBeVisible({ timeout: 10000 })
  })

  test('Professional pipeline error restores generation controls and leaves no bad candidate', async ({ page }) => {
    const state = await installT92cMockApi(page, { pipelineError: true })
    await openProfessionalScene(page)

    await page.getByTestId('rewrite-button').click()
    await expect.poll(() => state.pipelineCalls.length).toBe(1)
    await expect(page.getByTestId('rewrite-button')).toBeEnabled({ timeout: 10000 })

    expect(state.candidates).toHaveLength(0)
    expect(state.fileSavePayloads).toHaveLength(0)
    expect(state.sourceContent).toContain('Original official scene content')
  })

  test('Lite feedback generation streams into a candidate draft without overwriting source', async ({ page }) => {
    const state = await installT92cMockApi(page)
    await page.goto(`/project/${projectId}/lite`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('lite-entry-root')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('lite-prompt-input')).toBeVisible({ timeout: 10000 })
    await page.getByTestId('lite-prompt-input').fill('Make the current scene sharper, but keep continuity.')
    await page.getByTestId('lite-generate-button').click()

    await expect.poll(() => state.liteStreamCalls.length).toBe(1)
    await expect(page.locator('.candidate-bar')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('lite-accept-button')).toBeVisible({ timeout: 10000 })
    expect(state.liteStreamCalls[0]).toMatchObject({ action: 'rewrite', target_file: nextScenePath })
    expect(state.fileSavePayloads).toHaveLength(0)
    expect(state.sourceContent).toContain('Original official scene content')
  })

  test('Lite LLM error recovers the generate button and does not create a candidate draft', async ({ page }) => {
    const state = await installT92cMockApi(page, { liteStreamError: true })
    await page.goto(`/project/${projectId}/lite`)
    await dismissViteOverlay(page)

    await expect(page.getByTestId('lite-prompt-input')).toBeVisible({ timeout: 10000 })
    await page.getByTestId('lite-prompt-input').fill('This mocked request should fail once.')
    await page.getByTestId('lite-generate-button').click()

    await expect.poll(() => state.liteStreamCalls.length).toBe(1)
    await expect(page.getByTestId('lite-generate-button')).toBeEnabled({ timeout: 10000 })
    await expect(page.locator('.candidate-bar')).toHaveCount(0)
    expect(state.fileSavePayloads).toHaveLength(0)
  })

  test('File save conflict shows conflict modal and does not silently overwrite content', async ({ page }) => {
    const state = await installT92cMockApi(page, { fileSaveConflict: true })
    await openProfessionalScene(page)

    await page.locator('.cm-content').click()
    await page.keyboard.press('Control+A')
    await page.keyboard.type('User edit that should not overwrite the server version.')
    await page.keyboard.press('Control+S')

    await expect.poll(() => state.fileSavePayloads.length >= 1).toBe(true)
    await expect(page.locator('.ant-modal-confirm').first()).toBeVisible({ timeout: 10000 })
    expect(state.fileSavePayloads[0]).toMatchObject({
      expected_mtime: 1001,
      expected_hash: 'hash-before-save',
    })
    expect(state.sourceContent).toContain('Original official scene content')
  })

  test('Candidate preview can close before delete, and delete never saves official scene', async ({ page }) => {
    const state = await installT92cMockApi(page)
    state.candidates.unshift(candidatePayload('cand-existing-preview-delete'))
    page.on('dialog', (dialog) => dialog.accept())

    await openProfessionalScene(page)
    await openCandidateTab(page)
    await page.locator('.candidate-card .card-actions-primary button').first().click()
    await expect(page.locator('.preview-modal')).toBeVisible({ timeout: 10000 })
    await page.locator('.preview-modal .btn-cancel').click()
    await expect(page.locator('.preview-modal')).toHaveCount(0)

    await page.getByTestId('candidate-reject-button').first().click()
    await expect.poll(() => state.candidates[0].status).toBe('discarded')
    expect(state.fileSavePayloads).toHaveLength(0)
    expect(state.sourceContent).toContain('Original official scene content')
  })
})
