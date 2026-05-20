/**
 * E2E 测试工具函数
 */

import { Page, expect } from '@playwright/test'
import { SELECTORS } from './selectors'

/**
 * 等待页面加载完成（非白屏）
 */
export async function waitForAppReady(page: Page, timeout = 15000): Promise<void> {
  await page.waitForSelector('body', { timeout })
  // 等待 Vue 挂载
  await page.waitForTimeout(1000)
}

/**
 * 检查页面无严重 console error
 * 返回收集到的 error 列表
 */
export async function collectConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = []
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
      errors.push(text)
    }
  })
  return errors
}

/**
 * 断言页面无严重 console error
 */
export async function assertNoSevereErrors(page: Page, timeout = 3000): Promise<void> {
  const errors = await collectConsoleErrors(page)
  // 等待一段时间收集错误
  await page.waitForTimeout(timeout)
  // 过滤掉无害错误后，不应有剩余
  const severeErrors = errors.filter(
    (e) =>
      !e.includes('ResizeObserver') &&
      !e.includes('vite-error-overlay') &&
      !e.includes('Download the Vue DevTools')
  )
  expect(severeErrors).toEqual([])
}

/**
 * 通过 data-testid 定位元素
 */
export function getByTestId(page: Page, testId: string) {
  return page.locator(`[data-testid="${testId}"]`)
}

/**
 * 打开设置弹窗
 */
export async function openSettings(page: Page): Promise<void> {
  await getByTestId(page, 'settings-button').click()
  await page.waitForSelector(SELECTORS.SETTINGS_MODAL, { timeout: 5000 })
}

/**
 * 关闭弹窗（按 Escape）
 */
export async function closeModal(page: Page): Promise<void> {
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)
}

/**
 * 清除 Vite 错误覆盖层
 */
export async function dismissViteOverlay(page: Page): Promise<void> {
  await page.evaluate(() => {
    document.querySelector('vite-error-overlay')?.remove()
  })
}

/**
 * 等待 LLM 生成完成（轮询编辑器内容变化）
 */
export async function waitForGeneration(
  page: Page,
  minContentLength = 100,
  maxWaitMs = 120000
): Promise<string> {
  const startTime = Date.now()
  let content = ''

  while (Date.now() - startTime < maxWaitMs) {
    const editor = page.locator('.cm-content').first()
    content = (await editor.textContent().catch(() => '')) || ''
    if (content.length >= minContentLength) {
      return content
    }
    await page.waitForTimeout(1000)
  }

  return content
}
