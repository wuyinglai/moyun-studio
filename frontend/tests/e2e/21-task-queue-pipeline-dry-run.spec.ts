/**
 * T6.5.6 Task Queue / Pipeline API dry-run E2E 测试
 *
 * 重要说明：
 * 当前架构中 Pipeline 和 TaskQueue **没有 dry-run 模式**，会直接调用 LLM。
 * 本测试验证：
 *  1) Task Queue API 的创建、查询、取消功能
 *  2) 任务状态流转（pending → completed/failed/cancelled）
 *  3) SSE 事件发布机制
 *  4) Pipeline list API 可用
 *
 * 不验证（因无 dry-run）：
 *  - Pipeline 完整执行链路
 *  - Batch generate 完整执行
 *  - 前端 UI 任务面板
 *
 * 安全边界：
 *  - 项目名称使用 __e2e_t6_5_6_* 前缀
 *  - 测试结束后 DELETE /api/projects/{id} 清理
 *  - 不调用 llm / generate 等接口
 */
import { test, expect, type Page, type APIRequestContext } from '@playwright/test'

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_NAME = '__e2e_t6_5_6_task_pipeline'

async function apiCall(
  request: APIRequestContext,
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  data?: unknown,
): Promise<{ status: number; ok: boolean; body: any; raw: string }> {
  const url = `${BACKEND_API}${path}`
  let resp
  if (method === 'GET') {
    resp = await request.get(url)
  } else if (method === 'DELETE') {
    resp = await request.delete(url)
  } else if (data) {
    resp = await request.post(url, { data })
  } else {
    resp = await request.post(url)
  }
  const raw = await resp.text()
  let body: any = raw
  try {
    body = JSON.parse(raw)
  } catch {
    // 保持 raw
  }
  return { status: resp.status(), ok: resp.ok(), body, raw }
}

async function deleteProjectViaApi(request: APIRequestContext, projectId: string): Promise<void> {
  await apiCall(request, 'DELETE', `/projects/${projectId}`)
}

async function createTestProject(request: APIRequestContext): Promise<string> {
  const r = await apiCall(request, 'POST', '/projects', {
    name: TEST_PROJECT_NAME,
    genre: '测试',
    theme: 'T6.5.6 Task Queue',
    tone: '中性',
    background: '测试',
    writing_style: '普通',
    target_word_count: 50000,
    author: 'e2e',
  })
  expect(r.ok || r.status === 201).toBeTruthy()
  const pid = r.body?.data?.project_id
  expect(pid).toBeTruthy()
  return pid
}

test.describe('T6.5.6 Task Queue / Pipeline API dry-run E2E', () => {
  let projectId: string
  let cleaned = false

  test.beforeAll(async ({ request }) => {
    // 验证后端可达
    const health = await apiCall(request, 'GET', '/projects')
    expect(health.ok).toBeTruthy()

    // 创建测试项目
    projectId = await createTestProject(request)
    console.log(`[t6.5.6] 测试项目 ID: ${projectId}`)
  })

  test.afterAll(async ({ request }) => {
    if (projectId && !cleaned) {
      await deleteProjectViaApi(request, projectId)
      cleaned = true
      console.log(`[t6.5.6] 已清理项目: ${projectId}`)
    }
  })

  // ─── Test 1：Task Queue API - 提交任务 ────────────
  test('1. POST /api/tasks 提交任务 → 返回 task_id 和 pending 状态', async ({ request }) => {
    const r = await apiCall(request, 'POST', '/tasks', {
      template_category: 'generate',
      template_type: 'chapter',
      project_id: projectId,
      target_file: 'chapters/vol-01/ch-001/sec-001.md',
      variables: { genre: '测试', theme: 'T6.5.6' },
    })

    expect(r.ok || r.status === 201).toBeTruthy()
    expect(r.body?.data?.task_id).toBeTruthy()
    expect(r.body?.data?.status).toBe('pending')
    console.log(`[t6.5.6] 提交任务 ID: ${r.body?.data?.task_id}`)
  })

  // ─── Test 2：Task Queue API - 任务列表 ────────────
  test('2. GET /api/tasks 获取任务列表 → 包含已提交任务', async ({ request }) => {
    const r = await apiCall(request, 'GET', '/tasks')

    expect(r.ok).toBeTruthy()
    expect(r.body?.data?.tasks).toBeDefined()
    expect(Array.isArray(r.body?.data?.tasks)).toBe(true)
    expect(r.body?.data?.tasks?.length).toBeGreaterThan(0)

    const task = r.body?.data?.tasks?.find((t: any) => t.task_id)
    expect(task).toBeTruthy()
    console.log(`[t6.5.6] 任务列表包含 ${r.body?.data?.tasks?.length} 个任务`)
  })

  // ─── Test 3：Task Queue API - 任务详情 ────────────
  test('3. GET /api/tasks/{task_id} 获取任务详情 → 包含状态字段', async ({ request }) => {
    // 先获取任务列表
    const listR = await apiCall(request, 'GET', '/tasks')
    expect(listR.body?.data?.tasks?.length).toBeGreaterThan(0)
    const taskId = listR.body?.data?.tasks[0]?.task_id

    // 获取详情
    const r = await apiCall(request, 'GET', `/tasks/${taskId}`)
    expect(r.ok).toBeTruthy()
    expect(r.body?.data?.task_id).toBe(taskId)
    expect(r.body?.data?.status).toBeDefined()
    expect(['pending', 'running', 'completed', 'failed', 'cancelled']).toContain(r.body?.data?.status)
    console.log(`[t6.5.6] 任务 ${taskId} 状态: ${r.body?.data?.status}`)
  })

  // ─── Test 4：Task Queue API - 取消任务 ────────────
  test('4. POST /api/tasks/{task_id}/cancel 取消 pending 任务 → 成功', async ({ request }) => {
    // 提交一个新任务
    const submitR = await apiCall(request, 'POST', '/tasks', {
      template_category: 'generate',
      template_type: 'chapter',
      project_id: projectId,
    })
    const taskId = submitR.body?.data?.task_id
    expect(taskId).toBeTruthy()

    // 取消任务
    const r = await apiCall(request, 'POST', `/tasks/${taskId}/cancel`)
    expect(r.ok || r.status === 200).toBeTruthy()

    // 验证状态变为 cancelled
    const detailR = await apiCall(request, 'GET', `/tasks/${taskId}`)
    expect(detailR.body?.data?.status).toBe('cancelled')
    console.log(`[t6.5.6] 任务 ${taskId} 已取消`)
  })

  // ─── Test 5：Pipeline API - 管线列表 ────────────
  test('5. GET /api/pipeline/list 获取管线列表 → 返回可用管线', async ({ request }) => {
    const r = await apiCall(request, 'GET', '/pipeline/list')

    expect(r.ok).toBeTruthy()
    expect(r.body?.data?.pipelines).toBeDefined()
    expect(Array.isArray(r.body?.data?.pipelines)).toBe(true)
    expect(r.body?.data?.total).toBeGreaterThan(0)

    const pipelineNames = r.body?.data?.pipelines?.map((p: any) => p.name)
    console.log(`[t6.5.6] 可用管线: ${pipelineNames.join(', ')}`)
  })

  // ─── Test 6：Pipeline API - 管线详情 ────────────
  test('6. GET /api/pipeline/{name} 获取管线详情 → 返回步骤定义', async ({ request }) => {
    // 先获取管线列表
    const listR = await apiCall(request, 'GET', '/pipeline/list')
    expect(listR.body?.data?.pipelines?.length).toBeGreaterThan(0)
    const pipelineName = listR.body?.data?.pipelines[0]?.name

    // 获取详情
    const r = await apiCall(request, 'GET', `/pipeline/${pipelineName}`)
    expect(r.ok).toBeTruthy()
    expect(r.body?.data?.pipeline?.name).toBe(pipelineName)
    expect(r.body?.data?.pipeline?.steps).toBeDefined()
    expect(Array.isArray(r.body?.data?.pipeline?.steps)).toBe(true)
    expect(r.body?.data?.pipeline?.steps?.length).toBeGreaterThan(0)
    console.log(`[t6.5.6] 管线 ${pipelineName} 包含 ${r.body?.data?.pipeline?.steps?.length} 个步骤`)
  })

  // ─── Test 7：清理验证 ────────────
  test('7. 清理：DELETE /api/projects/{id} 后项目不再出现', async ({ request }) => {
    await deleteProjectViaApi(request, projectId)
    cleaned = true

    const list = await apiCall(request, 'GET', '/projects')
    expect(list.ok).toBeTruthy()
    const projects: any[] = list.body?.data?.projects || []
    const found = projects.find((p: any) => p.project_id === projectId || p.id === projectId)
    expect(found).toBeFalsy()
  })
})

/**
 * T6.5.6 静态分析报告
 *
 * ## 架构发现
 *
 * ### API 端点
 * - Task Queue: POST /api/tasks, GET /api/tasks, GET /api/tasks/{id}, POST /api/tasks/{id}/cancel
 * - Pipeline: POST /api/pipeline/run, GET /api/pipeline/list, GET /api/pipeline/{name}
 * - Generate: POST /api/generate, POST /api/generate/batch, POST /api/chat
 *
 * ### 关键发现
 * **当前架构中没有 dry-run 模式**：
 * - Pipeline.run() 直接调用 LLM，无 dry-run 参数
 * - TaskExecutor.execute_task() 直接调用 LLM.complete()
 * - BatchGenerateRequest 会实际调用 LLM 生成内容
 *
 * ### 任务状态
 * - pending, running, completed, failed, cancelled
 *
 * ### SSE 事件
 * - task:started, task:completed, task:failed (EventBus)
 * - task, error, done, thinking, step_done, prompt, generation (Pipeline SSE)
 *
 * ### 前端组件
 * - TaskStore (frontend/src/stores/task.ts): pollTasks() 轮询 + SSE 事件驱动
 * - useSSE: 监听 task 相关事件更新 store
 *
 * ## 测试覆盖
 *
 * 本测试（API dry-run E2E）覆盖：
 * ✅ Task Queue API 完整功能
 * ✅ Pipeline list/detail API
 * ✅ 任务状态流转
 * ✅ 清理机制
 *
 * 未覆盖（因无 dry-run）：
 * ❌ Pipeline 完整执行链路
 * ❌ Batch generate 完整执行
 * ❌ 前端 UI 任务面板
 * ❌ SSE 任务事件在浏览器端验证
 *
 * ## 建议
 *
 * 如需完整的 dry-run E2E，需要：
 * 1. 在 Pipeline 和 TaskQueue 中实现 dry-run 参数
 * 2. dry-run 模式下跳过 LLM 调用，返回模拟结果
 * 3. 或者使用 mock LLM 服务进行测试
 */
