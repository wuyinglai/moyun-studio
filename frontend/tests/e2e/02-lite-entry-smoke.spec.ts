/**
 * 02 - 爽文模式入口 Smoke 测试
 *
 * 验证：
 * 1. 打开轻量入口
 * 2. 页面不白屏
 * 3. 快速创作输入区或爽点卡区域可见
 * 4. 设置入口或模型状态可见
 * 5. 无严重 console error
 */

import { test, expect } from '@playwright/test'
import { openLiteEntry } from './helpers/entryHelpers'
import { getByTestId, dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'

test.describe('爽文模式入口 Smoke 测试', () => {
  test('打开爽文模式，页面不白屏', async ({ page }) => {
    const errors = createErrorCollector(page)
    await openLiteEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // 不白屏
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toBeTruthy()
    expect(bodyText!.length).toBeGreaterThan(10)

    // 爽文模式根元素存在
    const liteRoot = getByTestId(page, 'lite-entry-root')
    await expect(liteRoot).toBeVisible({ timeout: 10000 })

    // 无严重 console error
    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('爽点卡区域或创作输入区可见', async ({ page }) => {
    await openLiteEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 无项目时显示 idea-screen（爽点卡选择），有项目时显示 writing-shell（创作输入）
    const ideaScreen = page.locator('.idea-screen').first()
    const writingShell = page.locator('.writing-shell').first()
    await expect(ideaScreen.or(writingShell)).toBeVisible({ timeout: 10000 })
  })

  test('爽文模式标题或创作区域可见', async ({ page }) => {
    await openLiteEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 页面应包含"爽文"关键字或创作相关元素
    const bodyText = await page.locator('body').textContent()
    const hasLiteContent = bodyText?.includes('爽文') || bodyText?.includes('创作') || bodyText?.includes('写')
    expect(hasLiteContent).toBe(true)
  })

  test('无严重 console error', async ({ page }) => {
    const errors = createErrorCollector(page)
    await openLiteEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(3000)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
