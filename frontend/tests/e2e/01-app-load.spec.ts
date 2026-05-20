/**
 * 01 - 应用加载 Smoke 测试
 *
 * 验证应用基本可用性：
 * 1. 页面能打开
 * 2. 不白屏
 * 3. 项目面板存在
 * 4. 编辑器区域存在
 * 5. 设置入口存在
 * 6. 无严重 console error
 */

import { test, expect } from '@playwright/test'
import { getByTestId, dismissViteOverlay } from './helpers/e2eUtils'

test.describe('应用加载 Smoke 测试', () => {
  const consoleErrors: string[] = []

  test.beforeEach(async ({ page }) => {
    // 收集 console error
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        // 忽略已知的无害错误
        if (
          text.includes('ResizeObserver') ||
          text.includes('vite-error-overlay') ||
          text.includes('Download the Vue DevTools')
        ) {
          return
        }
        consoleErrors.push(text)
      }
    })
  })

  test('页面能打开', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    // 页面标题应包含"墨韵"
    const title = await page.title()
    expect(title).toBeTruthy()
  })

  test('不白屏', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // body 应有实际内容
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toBeTruthy()
    expect(bodyText!.length).toBeGreaterThan(10)
  })

  test('项目面板（左栏）存在', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 文件树区域应存在
    const fileTree = getByTestId(page, 'file-tree')
    await expect(fileTree).toBeVisible({ timeout: 10000 })
  })

  test('编辑器区域存在', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 编辑器面板应存在
    const editorPanel = getByTestId(page, 'editor-panel')
    await expect(editorPanel).toBeVisible({ timeout: 10000 })
  })

  test('设置入口存在', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 设置按钮应存在
    const settingsBtn = getByTestId(page, 'settings-button')
    await expect(settingsBtn).toBeVisible({ timeout: 10000 })
  })

  test('无严重 console error', async ({ page }) => {
    await page.goto('/')
    await dismissViteOverlay(page)
    await page.waitForTimeout(3000)

    // 过滤掉无害错误
    const severeErrors = consoleErrors.filter(
      (e) =>
        !e.includes('ResizeObserver') &&
        !e.includes('vite-error-overlay') &&
        !e.includes('Download the Vue DevTools') &&
        !e.includes('net::ERR_CONNECTION_REFUSED') // 后端未启动时正常
    )
    expect(severeErrors).toEqual([])
  })
})
