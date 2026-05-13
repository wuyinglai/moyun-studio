/**
 * 墨韵 UI 自动截图测试
 *
 * 用 Playwright 模拟用户操作、截图，用于人工审查界面问题。
 *
 * 运行: cd frontend && npx playwright test ../tests/ui_screenshots.spec.ts
 * 截图输出: tests/screenshots/
 */

import { test, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'

const SCREENSHOT_DIR = path.resolve(process.cwd(), 'e2e-tests', 'screenshots')

// 确保截图目录存在
test.beforeAll(() => {
  if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
})

// 每个测试前先清 console 缓存、关闭 Vite 错误覆盖层
test.beforeEach(async ({ page }) => {
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.log(`[CONSOLE_ERROR] ${msg.text()}`)
    }
  })
  // 清除 Vite 错误覆盖层（如果有）
  await page.keyboard.press('Escape').catch(() => {})
})

// ─── 首页 ──────────────────────────────────────────────

test('01 - 首页加载', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(1500)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})
  // 关闭 Vite 错误覆盖层（如果有）
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01-homepage.png'), fullPage: false })

  // 检查页面有实际内容
  const bodyText = await page.locator('body').textContent()
  console.log(`[CHECK] body 文本长度: ${bodyText?.length || 0}`)
  if (!bodyText || bodyText.length < 10) {
    console.log('[ISSUE] 页面内容可能为空！')
  }

  // 检查 header 存在
  const header = page.locator('header.app-header').first()
  console.log(`[CHECK] header 可见: ${await header.isVisible().catch(() => false)}`)
})

test('02 - 打开新建项目弹窗', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(1500)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  // 查找"新建项目"按钮
  const newProjectBtn = page.locator('button').filter({ hasText: '新建项目' }).first()
  await expect(newProjectBtn).toBeVisible()
  await newProjectBtn.click()
  await page.waitForTimeout(500)

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02-create-project-modal.png'), fullPage: false })

  // 检查弹窗可见
  const modal = page.locator('.ant-modal').first()
  await expect(modal).toBeVisible()

  // 检查按钮：应有"生成并打开"按钮
  const generateBtn = modal.getByText('生成并打开')
  const generateBtnCount = await generateBtn.count()
  console.log(`[CHECK] 新建项目弹窗 - "生成并打开" 按钮数量: ${generateBtnCount}`)
  if (generateBtnCount === 0) {
    console.log('[ISSUE] 新建项目弹窗缺少"生成并打开"按钮！')
  }

  // 检查页脚按钮是否存在
  const footerBtns = await modal.locator('.ant-modal-footer button, [class*="footer"] button').count()
  console.log(`[CHECK] 页脚按钮数量: ${footerBtns}`)
  // 题材 radio group 应该存在
  const genreRadio = modal.locator('.ant-radio-group').first()
  await expect(genreRadio).toBeVisible()
})

test('03 - 打开打开项目弹窗', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(2000)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  // 查找"打开项目"按钮（用 button 标签限定，避免匹配到"未打开项目"文本）
  const openProjectBtn = page.locator('button', { hasText: '打开项目' }).first()
  await expect(openProjectBtn).toBeVisible()
  console.log('[CHECK] 打开项目按钮可见，点击中...')
  await openProjectBtn.click()
  await page.waitForTimeout(1500)

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03-open-project-modal.png'), fullPage: false })

  // 检查弹窗 — 存在任意 .ant-modal 即认为弹窗打开
  const modalCount = await page.locator('.ant-modal').count()
  console.log(`[CHECK] 页面上 .ant-modal 数量: ${modalCount}`)
  if (modalCount === 0) {
    console.log('[ISSUE] 点击"打开项目"后未出现弹窗！')
  } else {
    const modal = page.locator('.ant-modal').first()
    // 检查按钮（定位 modal 内所有 button）
    const allBtns = await modal.locator('.ant-modal-footer button, .ant-modal-content button').allTextContents()
    console.log(`[CHECK] 弹窗内按钮文本: ${allBtns.map(t => t.trim().replace(/\s+/g, '')).filter(Boolean).join(' | ') || '(空)'}`)
    const cancelBtn = modal.locator('.ant-modal-content button', { hasText: /取消/ })
    const openBtn = modal.locator('.ant-modal-content button', { hasText: /打开/ })
    console.log(`[CHECK] "取消"按钮存在: ${await cancelBtn.isVisible().catch(() => false)}`)
    console.log(`[CHECK] "打开"按钮存在: ${await openBtn.isVisible().catch(() => false)}`)

    // 检查项目列表
    const projectItems = await modal.locator('.ant-list-item, [class*="project-item"], .ant-table-row').count()
    console.log(`[CHECK] 项目列表项数量: ${projectItems}`)
  }
})

test('04 - 设置弹窗', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(1000)

  // 查找设置按钮（图标按钮，文字在 title 属性中）
  const settingsBtn = page.locator('button[title="设置"]').first()
  if (await settingsBtn.isVisible()) {
    await settingsBtn.click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04-settings-modal.png'), fullPage: false })
    // 关闭 — 按 Escape
    await page.keyboard.press('Escape')
  } else {
    console.log('[CHECK] 设置按钮未找到，跳过')
  }
})

// ─── 项目页面 ──────────────────────────────────────────

test('05 - 打开项目页面', async ({ page }) => {
  await page.goto('http://localhost:3000/project/e7b83e15', { waitUntil: 'load' })
  await page.waitForTimeout(2000)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05-project-page.png'), fullPage: false })

  // 检查三栏布局是否出现
  const leftPanel = page.locator('.left-panel, [class*="left"]').first()
  const rightPanel = page.locator('.right-panel, [class*="right"]').first()
  console.log(`[CHECK] 左栏可见: ${await leftPanel.isVisible().catch(() => false)}`)
  console.log(`[CHECK] 右栏可见: ${await rightPanel.isVisible().catch(() => false)}`)

  // 文件树应该加载
  const treeItems = await page.locator('.ant-tree-node-content-wrapper, .file-tree-item, [class*="tree-node"]').count()
  console.log(`[CHECK] 文件树节点数: ${treeItems}`)

  // 编辑器区域应该存在
  const editor = page.locator('.CodeMirror, .cm-editor, .markdown-editor, [class*="editor"]').first()
  console.log(`[CHECK] 编辑器可见: ${await editor.isVisible().catch(() => false)}`)

  // 页头部分
  const header = page.locator('header, .app-header, .ant-layout-header').first()
  console.log(`[CHECK] header 可见: ${await header.isVisible().catch(() => false)}`)
})

test('06 - 工具栏按钮全部可见', async ({ page }) => {
  await page.goto('http://localhost:3000/project/e7b83e15', { waitUntil: 'load' })
  await page.waitForTimeout(2000)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06-toolbar.png'), fullPage: false })

  // 检查工具栏按钮（非生成状态）
  const toolbarButtons = [
    '后退', '前进', '重写', '生成下一个文件',
    'Token', '对比', '反馈', '修改日志',
    '批量生成', '质量审查', '提取',
  ]

  for (const label of toolbarButtons) {
    const btn = page.locator('button').filter({ hasText: label }).first()
    const visible = await btn.isVisible().catch(() => false)
    if (!visible) {
      console.log(`[ISSUE] 工具栏按钮"${label}"不可见！`)
    }
  }
})

// ─── Modals ────────────────────────────────────────────

test('07 - 各功能弹窗打开测试', async ({ page }) => {
  test.setTimeout(120000) // 每个弹窗前重载页面，需要更多时间
  await page.goto('http://localhost:3000/project/e7b83e15', { waitUntil: 'load' })
  await page.waitForTimeout(2000)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  interface ModalTest {
    name: string
    buttonLabel: string
    // 点击按钮后需要额外等待
    waitAfter?: number
  }

  const modals: ModalTest[] = [
    { name: 'Token', buttonLabel: 'Token' },
    { name: '对比', buttonLabel: '对比' },
    { name: '反馈', buttonLabel: '反馈' },
    { name: '修改日志', buttonLabel: '修改日志' },
    { name: '批量生成', buttonLabel: '批量生成' },
    { name: '质量审查', buttonLabel: '质量审查' },
    { name: '提取', buttonLabel: '提取' },
  ]

  for (const m of modals) {
    // 每个弹窗前重新加载页面，避免残留遮罩
    await page.goto('http://localhost:3000/project/e7b83e15', { waitUntil: 'load' })
    await page.waitForTimeout(1500)
    await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

    const btn = page.locator('button').filter({ hasText: m.buttonLabel }).first()
    if (!(await btn.isVisible().catch(() => false))) {
      console.log(`[ISSUE] 找不到"${m.name}"按钮，跳过`)
      continue
    }

    await btn.click()
    await page.waitForTimeout(600)

    // 截图
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, `07-modal-${m.name}.png`),
      fullPage: false,
    })

    // 检查弹窗是否打开了
    const modal = page.locator('.ant-modal').first()
    const isVisible = await modal.isVisible().catch(() => false)
    console.log(`[CHECK] ${m.name} 弹窗可见: ${isVisible}`)

    if (isVisible) {
      const bodyText = await modal.locator('.ant-modal-body, .ant-modal-content').first().textContent().catch(() => '')
      const empty = !bodyText || bodyText.trim().length < 5
      if (empty) {
        console.log(`[ISSUE] ${m.name} 弹窗内容为空！`)
      }
    }
  }
})

// ─── 项目列表 ──────────────────────────────────────────

test('08 - 侧边栏操作测试', async ({ page }) => {
  await page.goto('http://localhost:3000/project/e7b83e15', { waitUntil: 'load' })
  await page.waitForTimeout(2000)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  // 尝试点击文件树中的第一个文件
  const firstFile = page.locator('.ant-tree-node-content-wrapper, .file-tree-item, [class*="tree-node"]').first()
  if (await firstFile.isVisible().catch(() => false)) {
    await firstFile.click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08-file-selected.png'), fullPage: false })
    console.log('[CHECK] 文件选中后截图完成')
  } else {
    console.log('[CHECK] 文件树不可见，跳过')
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08-no-filetree.png'), fullPage: false })
  }
})

// ─── 首页 ──────────────────────────────────────────────

test('09 - 首页完整截图（大尺寸）', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(1500)
  await page.evaluate(() => document.querySelector('vite-error-overlay')?.remove()).catch(() => {})

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09-homepage-wide.png'), fullPage: false })

  // 检查是否有"墨韵"标题
  const title = await page.title()
  console.log(`[CHECK] 页面标题: ${title}`)

  // 检查 Font Awesome 是否加载
  const icon = page.locator('.fa-solid, .fa-regular').first()
  const iconVisible = await icon.isVisible().catch(() => false)
  console.log(`[CHECK] Font Awesome 图标正常渲染: ${iconVisible}`)
})

// ─── 摘要 ──────────────────────────────────────────────

test.afterAll(async () => {
  const files = fs.readdirSync(SCREENSHOT_DIR)
  console.log('\n=== 截图清单 ===')
  files.forEach(f => console.log(`  ${f}`))
  console.log(`共 ${files.length} 张截图，保存在 ${SCREENSHOT_DIR}`)
})
