/**
 * 05 - 候选稿批量真实 LLM 测试（占位）
 *
 * 需要 MOYUN_E2E_REAL_LLM=true 才会执行。
 * 后续补充完整测试用例。
 */

import { test, expect } from '@playwright/test'
import { shouldSkipLLMTests } from './helpers/llmEnv'

test.describe('候选稿批量真实 LLM 测试', () => {
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')

  test('候选稿面板基本结构（占位）', async ({ page }) => {
    // TODO: 后续补充 — 打开项目 → 生成内容 → 检查候选稿面板
    test.skip()
  })
})
