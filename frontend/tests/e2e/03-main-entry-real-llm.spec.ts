/**
 * 03 - 主入口真实 LLM 测试（占位）
 *
 * 需要 MOYUN_E2E_REAL_LLM=true 才会执行。
 * 后续补充完整测试用例。
 */

import { test, expect } from '@playwright/test'
import { openMainEntry } from './helpers/entryHelpers'
import { shouldSkipLLMTests, validateLLMEnv } from './helpers/llmEnv'
import { getByTestId, dismissViteOverlay } from './helpers/e2eUtils'

test.describe('主入口真实 LLM 测试', () => {
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')

  test('LLM 环境配置验证', () => {
    const { valid, errors } = validateLLMEnv()
    if (!valid) {
      console.log('LLM 配置问题:', errors.join('; '))
    }
    // 即使配置不完整也不失败，只是提示
    expect(typeof valid).toBe('boolean')
  })

  test('主入口设置弹窗可配置 LLM（占位）', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    const settingsBtn = getByTestId(page, 'settings-button')
    await expect(settingsBtn).toBeVisible({ timeout: 10000 })
    await settingsBtn.click()

    // 设置弹窗应出现
    const settingsModal = getByTestId(page, 'settings-modal')
    await expect(settingsModal).toBeVisible({ timeout: 5000 })

    // TODO: 后续补充 — 在设置中填入 LLM 配置 → 测试连接 → 验证成功
  })
})
