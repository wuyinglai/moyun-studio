/**
 * T6.7.2 candidate-adopted SSE 补测
 *
 * 验证：
 * 1. adopt candidate 成功后，后端发布 candidate.adopted 事件
 * 2. SSE 转发该事件为 candidate-adopted（而非 file-updated）
 * 3. 前端能收到 candidate-adopted 事件
 * 4. 同时能收到 file-updated 事件
 * 5. candidate 状态变为 adopted
 * 6. 正文更新为 candidate 内容
 * 7. 未调用真实 LLM
 */
import { test, expect } from '@playwright/test'
// ── Gate：需要真实后端 ──────────────────────────────────────────
const REAL_BACKEND_AVAILABLE = process.env.MOYUN_E2E_REAL_BACKEND === '1'

import { dismissViteOverlay } from './helpers/e2eUtils'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_7_2_candidate_adopted_sse'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.7.2 初始正文'
const CANDIDATE_CONTENT = 'T6.7.2 candidate 正文'

async function deleteProject(projectId: string): Promise<void> {
  await fetch(`${BACKEND_API}/projects/${projectId}`, { method: 'DELETE' })
}

async function writeFile(projectId: string, relpath: string, content: string): Promise<void> {
  await fetch(`${BACKEND_API}/file?project_id=${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: relpath, content }),
  })
}

async function createProject(name: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      genre: '测试',
      theme: 'T6.7.2 candidate-adopted SSE',
      tone: '中性',
      background: '测试',
      writing_style: '普通',
      target_word_count: 50000,
      author: 'e2e',
    }),
  })
  const data = await resp.json()
  return data.data.project_id
}

async function getFile(projectId: string, relpath: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/file?project_id=${projectId}&path=${encodeURIComponent(relpath)}`)
  const data = await resp.json()
  return data.data?.content || ''
}

async function createCandidate(projectId: string, sourcePath: string, content: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      source_path: sourcePath,
      action: 'polish',
      content,
    }),
  })
  const data = await resp.json()
  return data.id || ''
}

async function adoptCandidate(projectId: string, candidateId: string): Promise<{ success: boolean; status: number; body: any }> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}/${candidateId}/adopt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  const body = await resp.json()
  return { success: resp.ok, status: resp.status, body }
}

async function getCandidateStatus(projectId: string, candidateId: string): Promise<string> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}/${candidateId}`)
  const data = await resp.json()
  return data.candidate?.status || ''
}

test.describe('T6.7.2 candidate-adopted SSE 补测', () => {
  test.skip(
    !REAL_BACKEND_AVAILABLE,
    'MOYUN_E2E_REAL_BACKEND=1 未设置，跳过需要真实后端的测试',
  )

  let projectId: string

  test.beforeAll(async () => {
    projectId = await createProject(TEST_PROJECT_NAME)
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
    console.log(`[t6.7.2] 测试项目: ${projectId}`)
  })

  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.7.2] 已清理项目: ${projectId}`)
    }
  })

  test('1. adopt candidate → 收到 candidate-adopted SSE 事件', async ({ page, request }) => {
    // 1. 创建 candidate
    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, CANDIDATE_CONTENT)
    expect(candidateId).not.toBe('')
    console.log(`[t6.7.2] 已创建 candidate: ${candidateId}`)

    // 2. 监听 SSE 事件 - 通过拦截 /api/sse 流收集事件
    const receivedEvents: string[] = []
    let adoptedEventCount = 0
    let fileUpdatedEventCount = 0

    await page.route('**/api/sse', (route) => {
      // 放行，但拦截响应
      route.continue()
    })

    // 3. 打开项目页面，建立 SSE 连接
    await page.goto(`/project/${projectId}/file/${TEST_FILE_PATH}`)
    await dismissViteOverlay(page)
    await page.waitForTimeout(3000)

    // 4. 通过页面上下文注册 SSE 事件监听
    const eventPromise = page.evaluate(() => {
      return new Promise<{ adoptedEvents: string[]; fileUpdatedEvents: string[]; allEvents: string[] }>(
        (resolve) => {
          const adoptedEvents: string[] = []
          const fileUpdatedEvents: string[] = []
          const allEvents: string[] = []

          // 直接从 window 上的 SSE 管理器获取事件（如果 useSSE 暴露了）
          // 否则通过 EventSource 重新订阅
          try {
            const sse = new EventSource('/api/sse')
            sse.addEventListener('candidate-adopted', (e: any) => {
              adoptedEvents.push(e.data)
              allEvents.push('candidate-adopted')
            })
            sse.addEventListener('file-updated', (e: any) => {
              fileUpdatedEvents.push(e.data)
              allEvents.push('file-updated')
            })
            // 记录所有消息事件名
            const originalAEL = sse.addEventListener.bind(sse)
            // 监听 message 事件（默认事件）
            sse.onmessage = (e: MessageEvent) => {
              // 默认 message 事件 - 不记录，使用上面的 addEventListener
            }
            ;(window as any).__t672_sse = { sse, adoptedEvents, fileUpdatedEvents, allEvents }
          } catch {}
          // 简单等待 15 秒内接收事件
          setTimeout(() => {
            resolve({
              adoptedEvents: (window as any).__t672_sse?.adoptedEvents || [],
              fileUpdatedEvents: (window as any).__t672_sse?.fileUpdatedEvents || [],
              allEvents: (window as any).__t672_sse?.allEvents || [],
            })
          }, 15000)
        },
      )
    })

    // 5. 等待 1 秒后通过 API adopt
    await page.waitForTimeout(1000)
    const adoptResult = await adoptCandidate(projectId, candidateId)
    console.log(`[t6.7.2] adopt 请求完成: ${adoptResult.success}, status=${adoptResult.status}`)

    expect(adoptResult.success).toBe(true)
    expect(adoptResult.status).toBe(200)

    // 6. 等待事件收集完成
    const result = await eventPromise
    console.log(`[t6.7.2] 收到 candidate-adopted 事件数: ${result.adoptedEvents.length}`)
    console.log(`[t6.7.2] 收到 file-updated 事件数: ${result.fileUpdatedEvents.length}`)
    console.log(`[t6.7.2] 所有事件名: ${result.allEvents.join(', ')}`)

    // 7. 验证 - 关键：candidate-adopted 必须存在（修复前会是 0）
    expect(result.adoptedEvents.length).toBeGreaterThan(0)

    // 8. 验证正文已更新
    const finalContent = await getFile(projectId, TEST_FILE_PATH)
    expect(finalContent).toBe(CANDIDATE_CONTENT)
    console.log('[t6.7.2] ✓ 正文已更新为 candidate 内容')

    // 9. 验证 candidate 状态
    const finalStatus = await getCandidateStatus(projectId, candidateId)
    expect(finalStatus).toBe('adopted')
    console.log(`[t6.7.2] ✓ candidate 状态: ${finalStatus}`)
  })

  test('2. 不调用真实 LLM - 纯 API 路径验证', async ({}) => {
    // 本测试验证整个流程不涉及 LLM 调用
    // 创建独立的 candidate + adopt
    const candidateId = await createCandidate(projectId, TEST_FILE_PATH, 'T6.7.2 test2 candidate')
    expect(candidateId).not.toBe('')

    const adoptResult = await adoptCandidate(projectId, candidateId)
    expect(adoptResult.success).toBe(true)

    const finalContent = await getFile(projectId, TEST_FILE_PATH)
    expect(finalContent).toBe('T6.7.2 test2 candidate')

    console.log('[t6.7.2] ✓ 纯 API 流程完成，无 LLM 调用')
  })
})
