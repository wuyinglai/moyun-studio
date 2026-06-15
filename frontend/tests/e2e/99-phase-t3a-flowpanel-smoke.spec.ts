/**
 * Phase T3-A — FlowPanel Playwright UI 冒烟测试
 * 
 * 测试范围：
 * 1. 首页加载
 * 2. Lite 写作页面
 * 3. FlowPanel Tab
 * 4. 成功示例
 * 5. 失败示例
 * 6. 实时流程空态
 * 7. 新建项目 UI
 * 8. 尝试生成
 */
import { test, expect, chromium, type Page } from '@playwright/test'

// ── Gate：Phase T3-A 冒烟测试需要真实环境 ──────────────────────────
const PHASE_SMOKE_ENABLED = process.env.MOYUN_E2E_ALLOW_PHASE_SMOKE === '1'

import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const screenshotDir = path.resolve(__dirname, '../../../docs/testing/screenshots')

test.describe('Phase T3-A FlowPanel UI 冒烟测试', () => {
  test.skip(
    !PHASE_SMOKE_ENABLED,
    'MOYUN_E2E_ALLOW_PHASE_SMOKE=1 未设置，跳过 Phase T3-A 冒烟测试（无 mock，需要真实环境）',
  )

  let page: Page
  let consoleErrors: string[] = []

  test.beforeAll(async () => {
    const browser = await chromium.launch()
    const context = await browser.newContext()
    page = await context.newPage()

    // 收集控制台错误
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })
  })

  test('1. 首页加载成功', async () => {
    console.log('测试 1: 首页加载...')
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' })
    await page.waitForTimeout(2000)

    const title = await page.title()
    console.log('页面标题:', title)

    await page.screenshot({ path: path.join(screenshotDir, 't3a-01-home.png') })

    const bodyText = await page.locator('body').textContent()
    expect(bodyText?.length).toBeGreaterThan(0)
    console.log('✓ 首页加载完成')
  })

  test('2. 进入 Lite 写作页面', async () => {
    console.log('测试 2: Lite 写作页面...')

    // 尝试找到 Lite 入口按钮
    const liteButton = page.getByText('Lite').or(page.getByText('爽文')).or(page.getByText('轻量'))
    if (await liteButton.count() > 0) {
      await liteButton.first().click()
      await page.waitForTimeout(3000)
    }

    await page.screenshot({ path: path.join(screenshotDir, 't3a-02-lite-page.png') })

    const bodyText = await page.locator('body').textContent()
    console.log('页面包含内容:', bodyText?.slice(0, 200))
    expect(bodyText?.length).toBeGreaterThan(0)
    console.log('✓ Lite 页面加载完成')
  })

  test('3. 右边栏 FlowPanel Tab', async () => {
    console.log('测试 3: FlowPanel Tab...')

    // 尝试点击右边栏的流程 Tab
    const flowTab = page.getByText('流程').or(page.locator('.right-panel').getByRole('tab', { name: /流程/ }))
    
    if (await flowTab.count() > 0) {
      await flowTab.first().click()
      await page.waitForTimeout(2000)
    }

    await page.screenshot({ path: path.join(screenshotDir, 't3a-03-flow-tab.png') })
    console.log('✓ FlowPanel Tab 截图完成')
  })

  test('4. 成功示例展示', async () => {
    console.log('测试 4: 成功示例...')

    // 尝试点击成功示例按钮
    const successBtn = page.getByText('成功示例').or(page.locator('button:has-text("成功")'))
    if (await successBtn.count() > 0) {
      await successBtn.first().click()
      await page.waitForTimeout(1500)
    }

    // 尝试展开节点
    const expandButtons = page.locator('.flow-node').or(page.locator('[data-testid*="flow"]'))
    if (await expandButtons.count() > 0) {
      await expandButtons.first().click({ timeout: 5000 }).catch(() => {})
      await page.waitForTimeout(1000)
    }

    await page.screenshot({ path: path.join(screenshotDir, 't3a-04-flow-success-artifacts.png') })
    console.log('✓ 成功示例截图完成')
  })

  test('5. 失败示例展示', async () => {
    console.log('测试 5: 失败示例...')

    const failureBtn = page.getByText('失败示例').or(page.locator('button:has-text("失败")'))
    if (await failureBtn.count() > 0) {
      await failureBtn.first().click()
      await page.waitForTimeout(1500)
    }

    await page.screenshot({ path: path.join(screenshotDir, 't3a-05-flow-error.png') })
    console.log('✓ 失败示例截图完成')
  })

  test('6. 实时流程空态', async () => {
    console.log('测试 6: 实时流程空态...')

    const realtimeBtn = page.getByText('实时流程').or(page.locator('button:has-text("实时")'))
    if (await realtimeBtn.count() > 0) {
      await realtimeBtn.first().click()
      await page.waitForTimeout(1500)
    }

    await page.screenshot({ path: path.join(screenshotDir, 't3a-06-realtime-empty.png') })
    console.log('✓ 实时流程空态截图完成')
  })

  test('7. 新建项目 UI 流程', async () => {
    console.log('测试 7: 新建项目 UI...')

    try {
      const newProjectBtn = page.getByText('新建项目').or(page.locator('button:has-text("新建")'))
      if (await newProjectBtn.count() > 0) {
        await newProjectBtn.first().click()
        await page.waitForTimeout(2000)
      }

      await page.screenshot({ path: path.join(screenshotDir, 't3a-07-create-project.png') })
    } catch (e) {
      console.log('创建项目流程跳过:', e)
    }
    console.log('✓ 新建项目 UI 截图完成')
  })

  test('8. 尝试触发生成（无真实 LLM）', async () => {
    console.log('测试 8: 尝试生成...')

    const genButton = page.getByText('写下一场景').or(page.getByText('生成开局卡')).or(page.locator('button:has-text("生成")'))
    if (await genButton.count() > 0) {
      try {
        await genButton.first().click()
        await page.waitForTimeout(3000)
      } catch (e) {
        console.log('生成尝试失败（预期，无 API Key）:', e)
      }
    }

    await page.screenshot({ path: path.join(screenshotDir, 't3a-08-generation-attempt.png') })
    console.log('✓ 生成尝试截图完成')
  })

  test.afterAll(async () => {
    console.log('\nPhase T3-A 测试完成！')
    console.log('控制台错误数:', consoleErrors.length)
    if (consoleErrors.length > 0) {
      console.log('控制台错误详情:')
      consoleErrors.slice(0, 5).forEach(err => console.log('  -', err))
    }
  })
})
