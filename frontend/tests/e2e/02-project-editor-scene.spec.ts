/**
 * 02 - 项目编辑器场景测试（占位）
 *
 * 后续任务补充完整测试用例。
 * 当前仅验证项目创建弹窗可打开。
 */

import { test, expect } from '@playwright/test'
import { getByTestId, dismissViteOverlay } from './helpers/e2eUtils'
import { shouldSkipLLMTests } from './helpers/llmEnv'

test.describe('项目编辑器场景', () => {
  test('新建项目弹窗可打开', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    const newProjectBtn = getByTestId(page, 'new-project-button')
    await expect(newProjectBtn).toBeVisible({ timeout: 10000 })
    await newProjectBtn.click()

    // 弹窗应出现
    const modal = page.locator('.ant-modal').first()
    await expect(modal).toBeVisible({ timeout: 5000 })
  })

  test('设置弹窗可打开', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    const settingsBtn = getByTestId(page, 'settings-button')
    await expect(settingsBtn).toBeVisible({ timeout: 10000 })
    await settingsBtn.click()

    // 设置弹窗应出现
    const settingsModal = getByTestId(page, 'settings-modal')
    await expect(settingsModal).toBeVisible({ timeout: 5000 })
  })

  // 真实 LLM 测试：需要 MOYUN_E2E_REAL_LLM=true
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')
  test('配置 LLM 并测试连接（真实 LLM）', async ({ page }) => {
    // TODO: 后续补充完整 LLM 配置和连接测试
    test.skip()
  })
})
