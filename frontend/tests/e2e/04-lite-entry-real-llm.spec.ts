/**
 * 04 - 爽文模式真实 LLM 测试（占位）
 *
 * 需要 MOYUN_E2E_REAL_LLM=true 才会执行。
 * 后续补充完整测试用例。
 */

import { test, expect } from '@playwright/test'
import { openLiteEntry } from './helpers/entryHelpers'
import { shouldSkipLLMTests } from './helpers/llmEnv'
import { getByTestId, dismissViteOverlay } from './helpers/e2eUtils'

test.describe('爽文模式真实 LLM 测试', () => {
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')

  test('爽文模式灵感改稿区域可见（占位）', async ({ page }) => {
    await openLiteEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    const promptInput = getByTestId(page, 'lite-prompt-input')
    await expect(promptInput).toBeVisible({ timeout: 10000 })

    // TODO: 后续补充 — 输入改稿指令 → 点击生成 → 等待 LLM 响应 → 验证输出
  })
})
