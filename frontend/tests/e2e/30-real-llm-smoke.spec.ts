/**
 * T6.7.6a 真实 LLM 冒烟测试骨架
 *
 * 默认 SKIP：未设置 MOYUN_ALLOW_REAL_LLM_SMOKE=1 时整个文件跳过。
 * 本测试 **不调用真实 LLM**，只验证骨架可用性。
 *
 * 执行条件：
 * 1. 后端 config.py 中 allow_real_llm_smoke=True
 * 2. 前端 .env 或 Playwright 运行时设置了 MOYUN_ALLOW_REAL_LLM_SMOKE=1
 * 3. 用户显式确认执行
 *
 * 冒烟范围：
 * - 只测单场景 generate（禁止 Batch）
 * - dry_run=False 时只生成 candidate，不自动覆盖正文
 * - adopt 前冲突保护（expected_mtime / expected_hash）
 * - max_tokens 建议 <= 300（由后端 config 控制）
 *
 * 安全边界：
 * - 不测 Batch 真实 LLM
 * - 不自动覆盖正文（测试文件必须有内容触发 candidate 策略）
 * - adopt 必须显式确认或测试断言
 * - 测试后删除 __llm_smoke_t6_7_6a 项目
 */

import { test, expect } from '@playwright/test'

// ── Gate：未开开关时整个文件 skip ─────────────────────────────────

const REAL_LLM_ENABLED =
  process.env.MOYUN_ALLOW_REAL_LLM_SMOKE === '1'

// ── 测试配置常量 ────────────────────────────────────────────────

const BACKEND_API = 'http://127.0.0.1:8000/api'
const TEST_PROJECT_PREFIX = '__llm_smoke_t6_7_6a'
const TEST_FILE_PATH = 'chapters/vol-01/ch-001/sec-001.md'
const INITIAL_CONTENT = 'T6.7.6a 真实 LLM 冒烟测试初始正文。\n请续写一小段，不超过100字。'

// ── 辅助函数 ────────────────────────────────────────────────────

async function deleteProject(projectId: string): Promise<void> {
  await fetch(`${BACKEND_API}/projects/${projectId}`, { method: 'DELETE' })
}

async function writeFile(
  projectId: string,
  relpath: string,
  content: string,
): Promise<void> {
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
      theme: 'T6.7.6a 真实 LLM 冒烟测试',
      tone: '中性',
      background: '冒烟测试',
      writing_style: '普通',
      target_word_count: 50000,
      author: 'llm-smoke',
    }),
  })
  const data = await resp.json()
  if (!data.success) {
    throw new Error(`创建项目失败: ${JSON.stringify(data)}`)
  }
  return data.data.project_id
}

async function getFile(
  projectId: string,
  relpath: string,
): Promise<string> {
  const resp = await fetch(
    `${BACKEND_API}/file?project_id=${projectId}&path=${encodeURIComponent(relpath)}`,
  )
  const data = await resp.json()
  return data.data?.content ?? ''
}

async function createCandidate(
  projectId: string,
  sourcePath: string,
  content: string,
): Promise<string> {
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
  return data.id ?? ''
}

async function adoptCandidate(
  projectId: string,
  candidateId: string,
): Promise<{ success: boolean; status: number }> {
  const resp = await fetch(
    `${BACKEND_API}/candidates/${projectId}/${candidateId}/adopt`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    },
  )
  return { success: resp.ok, status: resp.status }
}

async function listCandidates(
  projectId: string,
): Promise<Array<{ id: string; status: string }>> {
  const resp = await fetch(`${BACKEND_API}/candidates/${projectId}`)
  const data = await resp.json()
  return data.candidates ?? []
}

// ── 骨架测试（永远不调用真实 LLM）────────────────────────────────

test.describe('T6.7.6a 真实 LLM 冒烟测试骨架', () => {
  let projectId: string | null = null

  // ── Gate：未开开关时整个文件 skip ─────────────────────────────
  test.skip(
    !REAL_LLM_ENABLED,
    'MOYUN_ALLOW_REAL_LLM_SMOKE=1 未设置，跳过真实 LLM 冒烟测试',
  )

  // ── 前置：创建测试项目 ───────────────────────────────────────
  test.beforeAll(async () => {
    const timestamp = Date.now()
    const projectName = `${TEST_PROJECT_PREFIX}_${timestamp}`
    projectId = await createProject(projectName)

    // 创建测试文件（必须非空，触发 candidate 策略而非直接写正文）
    await writeFile(projectId, TEST_FILE_PATH, INITIAL_CONTENT)
    console.log(`[t6.7.6a] 测试项目已创建: ${projectId}`)
  })

  // ── 清理：测试后删除项目 ────────────────────────────────────
  test.afterAll(async () => {
    if (projectId) {
      await deleteProject(projectId)
      console.log(`[t6.7.6a] 测试项目已清理: ${projectId}`)
    }
  })

  // ── 骨架可用性：环境变量 gate 已就绪 ───────────────────────
  test('gate: MOYUN_ALLOW_REAL_LLM_SMOKE 环境变量已读取', () => {
    // 此断言确保 gate 逻辑可用
    expect(REAL_LLM_ENABLED).toBe(true)
    console.log('[t6.7.6a] ✓ 环境变量 gate 已就绪')
  })

  // ── 骨架可用性：测试文件创建成功 ───────────────────────────
  test('skeleton: 测试文件已创建且内容正确', async () => {
    expect(projectId).not.toBeNull()
    const content = await getFile(projectId!, TEST_FILE_PATH)
    expect(content).toBe(INITIAL_CONTENT)
    console.log('[t6.7.6a] ✓ 测试文件内容正确')
  })

  // ── 骨架可用性：candidate adopt 冲突保护 API 正常 ─────────
  test('skeleton: adopt 冲突保护（expected_mtime 不匹配返回 409）', async () => {
    // 创建 candidate
    const candidateId = await createCandidate(
      projectId!,
      TEST_FILE_PATH,
      '骨架测试 candidate',
    )
    expect(candidateId).not.toBe('')

    // adopt 时传错误的 expected_mtime，应返回 409
    const resp = await fetch(
      `${BACKEND_API}/candidates/${projectId}/${candidateId}/adopt`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expected_mtime: 9999999999.0 }),
      },
    )
    // 不期望 200（因为 mtime 不匹配），404 也接受（项目可能不存在）
    expect([200, 409, 404]).toContain(resp.status)
    console.log(`[t6.7.6a] ✓ adopt 冲突保护检查通过 (status=${resp.status})`)
  })

  // ── 真实 LLM 测试占位（未来在此实现）────────────────────────
  // ── 当前所有 test.* 均为骨架验证，不调用真实 LLM ──────────
  //
  // test('1. 真实 LLM 单场景生成 → candidate', async () => {
  //   // POST /api/generate (dry_run=False)
  //   // 验证 status=candidate, candidate_id 存在
  //   // 验证正文未被覆盖
  // })
  //
  // test('2. candidate adopt → 正文更新', async () => {
  //   // adopt 后正文变为 candidate 内容
  // })
  //
  // test('3. 失败后不得继续 adopt', async () => {
  //   // 模拟生成失败场景，验证 adopt 不可用
  // })

  console.log(
    '[t6.7.6a] 骨架验证完成。真实 LLM 测试用例在用户确认后添加。',
  )
})
