/**
 * Mock API helper for E2E tests
 *
 * Intercepts all /api/* requests via Playwright page.route() so the frontend
 * can load without a real backend.  Returns sensible defaults for every
 * endpoint the app hits on startup and during smoke tests.
 *
 * Usage (in test file or fixture):
 *   import { installMockApi } from './mockApi'
 *   test.beforeEach(async ({ page }) => { await installMockApi(page) })
 */

import type { Page } from '@playwright/test'

// ── Mock data ──────────────────────────────────────────────

const MOCK_PROJECTS: unknown[] = []

const MOCK_LLM_CONFIG = {
  provider: 'openai-compatible',
  base_url: 'http://127.0.0.1:1234/v1',
  model: 'mock-model',
  api_key_set: false,
  connected: false,
}

const MOCK_FILE_TREE: unknown[] = []

const MOCK_FILE_CONTENT = {
  content: '',
  frontmatter: null,
  path: '',
  mtime: new Date().toISOString(),
  hash: 'd41d8cd98f00b204e9800998ecf8427e',
}

const MOCK_IDEAS = {
  ideas: [
    { id: 'idea-1', title: '都市异能', genre: '都市', description: '一个普通大学生突然觉醒异能' },
    { id: 'idea-2', title: '星际冒险', genre: '科幻', description: '人类最后的星际舰队踏上征途' },
    { id: 'idea-3', title: '修仙重生', genre: '仙侠', description: '陨落的大帝重生回到少年时代' },
  ],
}

const MOCK_CANDIDATES: unknown[] = []

// ── SSE mock ───────────────────────────────────────────────

const SSE_BODY =
  'event: connected\ndata: {"timestamp":0}\n\n' +
  'event: sse.heartbeat\ndata: {"ts":0}\n\n'

// ── Route handler ──────────────────────────────────────────

interface LogEntry {
  method: string
  url: string
  status: number
  unmatched?: boolean
}

/**
 * Install mock API routes on a Playwright page.
 *
 * Every /api/* request is intercepted and returns a mock response.
 * Unmatched requests return 404 with a JSON body so the frontend
 * can distinguish "no backend" from "endpoint not mocked".
 *
 * @returns an object with a `logs` array for diagnostics.
 */
export async function installMockApi(page: Page): Promise<{ logs: LogEntry[] }> {
  const logs: LogEntry[] = []

  // Catch-all for /api/* — use precise URL pattern to avoid matching
  // non-API paths like /src/shared/api/routes.ts
  await page.route('http://127.0.0.1:5173/api/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname.replace('/api', '')
    const method = route.request().method()

    const entry: LogEntry = { method, url: path, status: 200 }
    let handled = true

    // ── Projects ──
    if (path === '/projects' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: MOCK_PROJECTS }) })
    }
    else if (/^\/projects\/[^/]+$/.test(path) && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: false, message: 'Project not found (mock)' }) })
    }

    // ── LLM ──
    else if (path === '/llm/config' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: MOCK_LLM_CONFIG }) })
    }
    else if (path === '/llm/status' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { connected: false } }) })
    }
    else if (path === '/llm/test' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { connected: false, message: 'Mock: no real LLM' } }) })
    }

    // ── SSE ──
    else if (path === '/sse') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-cache', Connection: 'keep-alive' },
        body: SSE_BODY,
      })
    }

    // ── Files ──
    else if (path === '/file' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: MOCK_FILE_CONTENT }) })
    }
    else if (path === '/file/create' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { path: 'mock.md' } }) })
    }
    else if (path === '/file/save' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { mtime: new Date().toISOString() } }) })
    }
    else if (path === '/file/rename' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
    }
    else if (path === '/file/delete' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
    }
    else if (path === '/files/search' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) })
    }
    else if (path === '/directory/create' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
    }

    // ── Tree ──
    else if (path === '/tree' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: MOCK_FILE_TREE }) })
    }

    // ── Lite ──
    else if (path === '/lite/ideas' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: MOCK_IDEAS }) })
    }
    else if (path === '/lite/projects' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { project_id: 'mock-project', name: 'Mock Project' } }) })
    }
    else if (path === '/lite/next-options' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { options: [] } }) })
    }
    else if (path.startsWith('/lite/') && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: {} }) })
    }

    // ── Candidates ──
    else if (/^\/candidates\//.test(path) && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: MOCK_CANDIDATES }) })
    }
    else if (/^\/candidates\//.test(path) && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: {} }) })
    }

    // ── Generate ──
    else if (path === '/generate' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { task_id: 'mock-task' } }) })
    }
    else if (path === '/generate/batch' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { tasks: [] } }) })
    }

    // ── Pipeline ──
    else if (path === '/pipeline/run' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { task_id: 'mock-pipeline-task' } }) })
    }
    else if (path.startsWith('/pipeline/') && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: {} }) })
    }

    // ── Workflows ──
    else if (path === '/workflows/run' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { run_id: 'mock-run' } }) })
    }
    else if (path.startsWith('/workflows/') && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: {} }) })
    }

    // ── Chat ──
    else if (path === '/chat' && method === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { task_id: 'mock-chat-task' } }) })
    }

    // ── Config ──
    else if (path === '/config/custom-params' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: {} }) })
    }

    // ── Prompts ──
    else if (path.startsWith('/prompts/') && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: '' }) })
    }

    // ── Catch-all: return 200 with empty data to avoid axios retries ──
    // Returning 404 causes axios to retry 3x and log [API Error] to console.
    // Instead, return a "success: false" response that the frontend handles gracefully.
    else {
      handled = false
      entry.status = 200
      entry.unmatched = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: `Mock API: unhandled ${method} ${path}`,
        }),
      })
    }

    logs.push(entry)

    // Log unmatched requests to console for diagnostics
    if (!handled) {
      console.warn(`[mockApi] UNHANDLED ${method} ${path} → 404`)
    }
  })

  return { logs }
}
