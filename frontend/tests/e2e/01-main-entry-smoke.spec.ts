/**
 * 01 - 主入口（专业模式）Smoke 测试
 *
 * 验证：
 * 1. 打开主入口
 * 2. 页面不白屏
 * 3. 主工作台核心区域可见
 * 4. 设置入口可见
 * 5. 无严重 console error
 */

import { test, expect } from '@playwright/test'
import { openMainEntry } from './helpers/entryHelpers'
import { getByTestId, dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'
import { installMockApi } from './helpers/mockApi'

test.describe('主入口 Smoke 测试', () => {
  test.beforeEach(async ({ page }) => {
    await installMockApi(page)
  })

  test('打开主入口，页面不白屏', async ({ page }) => {
    const errors = createErrorCollector(page)
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // 不白屏
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toBeTruthy()
    expect(bodyText!.length).toBeGreaterThan(10)

    // 主入口根元素存在
    const mainRoot = getByTestId(page, 'main-entry-root')
    await expect(mainRoot).toBeVisible({ timeout: 10000 })

    // 无严重 console error
    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })

  test('主工作台核心区域可见', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 文件树
    const fileTree = getByTestId(page, 'file-tree')
    await expect(fileTree).toBeVisible({ timeout: 10000 })

    // 编辑器面板
    const editorPanel = getByTestId(page, 'editor-panel')
    await expect(editorPanel).toBeVisible({ timeout: 10000 })
  })

  test('设置入口可见', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    const settingsBtn = getByTestId(page, 'settings-button')
    await expect(settingsBtn).toBeVisible({ timeout: 10000 })
  })

  test('无严重 console error', async ({ page }) => {
    const errors = createErrorCollector(page)
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(3000)

    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors).toEqual([])
  })
})
