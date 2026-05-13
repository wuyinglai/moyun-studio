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

// ─── 生成流程测试 ──────────────────────────────────────

test('10 - 从新建到项目页面完整流程', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(1500)

  // 打开新建项目弹窗
  const newProjectBtn = page.locator('button').filter({ hasText: '新建项目' }).first()
  await expect(newProjectBtn).toBeVisible()
  await newProjectBtn.click()
  await page.waitForTimeout(500)

  // 选择题材（genre 是必选）
  const genreRadio = page.locator('.ant-radio-group').first()
  await expect(genreRadio).toBeVisible()
  const firstGenreBtn = genreRadio.locator('.ant-radio-button-wrapper').first()
  await firstGenreBtn.click()
  await page.waitForTimeout(200)

  // 点击"生成并打开"
  const generateBtn = page.locator('button').filter({ hasText: '生成并打开' }).first()
  await expect(generateBtn).toBeEnabled({ timeout: 5000 })
  await generateBtn.click()

  // 弹窗应关闭，页面应导航到项目页
  await page.waitForTimeout(3000)
  const modalCount = await page.locator('.ant-modal').count()
  console.log(`[CHECK] 弹窗数量（应为0）: ${modalCount}`)

  // 检查是否在项目页（URL 包含 /project/）
  const currentUrl = page.url()
  console.log(`[CHECK] 当前 URL: ${currentUrl}`)
  const isProjectPage = currentUrl.includes('/project/')
  console.log(`[CHECK] 是否在项目页: ${isProjectPage}`)

  // 文件树应已加载
  const treeItems = await page.locator('.file-tree-item, [class*="tree-node"]').count()
  console.log(`[CHECK] 文件树节点: ${treeItems}`)
  const treeText = await page.locator('.file-tree-item, [class*="tree-node"]').first().textContent().catch(() => '')
  console.log(`[CHECK] 文件树首个节点: ${treeText?.trim()}`)

  // 编辑器应打开（内容可能正在流式生成）
  const editor = page.locator('.cm-editor, .CodeMirror').first()
  const editorVisible = await editor.isVisible().catch(() => false)
  console.log(`[CHECK] 编辑器可见: ${editorVisible}`)

  // 等待生成，检查编辑器内容是否出现
  let hasContent = false
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000)
    const editorContent = await editor.textContent().catch(() => '') || ''
    if (editorContent.length > 50) {
      hasContent = true
      console.log(`[CHECK] ✅ 编辑器内容已出现 (${editorContent.length} 字符，等待 ${i + 1}s)`)
      break
    }
  }
  if (!hasContent) {
    console.log('[ISSUE] ❌ 生成超时（30s），编辑器内容为空')
    // 检查控制台错误
    page.on('console', msg => {
      if (msg.type() === 'error') console.log(`  [CONSOLE_ERROR] ${msg.text()}`)
    })
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10-generation-result.png'), fullPage: false })
})

test('11 - 正文生成全流程', async ({ page, request }) => {
  test.setTimeout(300000)

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('http://localhost:3000', { waitUntil: 'load' })
  await page.waitForTimeout(1500)

  // ─── 创建项目（沿用 test 10 流程） ──────────────────
  const newProjectBtn = page.locator('button').filter({ hasText: '新建项目' }).first()
  await expect(newProjectBtn).toBeVisible()
  await newProjectBtn.click()
  await page.waitForTimeout(500)

  // 选择题材
  const genreRadio = page.locator('.ant-radio-group').first()
  await expect(genreRadio).toBeVisible()
  const firstGenreBtn = genreRadio.locator('.ant-radio-button-wrapper').first()
  const genreText = await firstGenreBtn.textContent()
  await firstGenreBtn.click()
  await page.waitForTimeout(200)

  // 点击"生成并打开"
  const generateBtn = page.locator('button').filter({ hasText: '生成并打开' }).first()
  await expect(generateBtn).toBeEnabled({ timeout: 5000 })
  await generateBtn.click()

  // 等待导航到项目页
  await page.waitForURL(/\/project\//, { timeout: 10000 })
  await page.waitForTimeout(2000)

  // 等待标题生成完成
  const editor = page.locator('.cm-content').first()
  let titleContent = ''
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(1000)
    titleContent = await editor.textContent().catch(() => '') || ''
    if (titleContent.length > 50) {
      console.log(`[CHECK] ✅ 标题已生成 (${titleContent.length} 字符，等待 ${i + 1}s)`)
      break
    }
  }
  expect(titleContent.length).toBeGreaterThan(50)
  console.log(`[CHECK] 标题内容预览: "${titleContent.substring(0, 80)}..."`)

  // 从 URL 获取 projectId
  const currentUrl = page.url()
  const projectId = currentUrl.match(/\/project\/([^/]+)/)?.[1] || ''
  expect(projectId).toBeTruthy()
  console.log(`[CHECK] projectId: ${projectId}`)

  // ─── 通过 API 完成大纲流程 ──────────────────────────

  // 步骤 A: 生成大纲
  const cleanGenre = genreText?.trim() || ''
  console.log('[CHECK] 正在生成大纲...')
  const outlineResp = await request.post(
    `http://localhost:8000/api/wizard/${projectId}/generate-outline`,
    {
      data: {
        genre: cleanGenre,
        tone: '正剧',
        theme: '成长',
        background: '架空世界',
        writing_style: '细腻描写',
        target_word_count: 50000,
        book_name: '',
        book_description: '',
      },
      timeout: 120000,
    }
  )
  expect(outlineResp.ok()).toBeTruthy()
  const outlineData = await outlineResp.json()
  const outline = outlineData?.data?.outline || ''
  expect(outline.length).toBeGreaterThan(100)
  console.log(`[CHECK] ✅ 大纲已生成 (${outline.length} 字符)`)

  // 步骤 B: 确认大纲，创建章节文件
  console.log('[CHECK] 正在确认大纲，创建章节文件...')
  const confirmResp = await request.post(
    `http://localhost:8000/api/wizard/${projectId}/confirm-outline`,
    {
      data: { outline },
    }
  )
  expect(confirmResp.ok()).toBeTruthy()
  console.log('[CHECK] ✅ 大纲已确认，章节文件已创建')

  // ─── 通过 batch generate API 生成正文 ──────────

  const sectionPath = 'chapters/vol-01/ch-001/sec-001.md'

  // 验证章节文件存在
  const fileCheckResp = await request.get(
    `http://localhost:8000/api/file?project_id=${projectId}&path=${sectionPath}`
  )
  expect(fileCheckResp.ok()).toBeTruthy()
  let fileData = await fileCheckResp.json()
  let fileContent = fileData?.data?.content || ''
  console.log(`[CHECK] 生成前章节文件: ${fileContent.length} 字符 — "${fileContent.substring(0, 50)}..."`)

  // 调用 batch generate API 生成正文（使用 generate/chapter 模板）
  console.log('[CHECK] ⏳ 正在生成正文（batch generate），预计 30-120 秒...')
  const batchResp = await request.post(
    `http://localhost:8000/api/generate/batch`,
    {
      data: {
        project_id: projectId,
        volume_number: 1,
        chapter_number: 1,
        section_numbers: [1],
        prompt_type: 'generate/chapter',
        temperature: 0.7,
      },
      timeout: 180000, // 最长 3 分钟
    }
  )
  expect(batchResp.ok()).toBeTruthy()
  const batchData = await batchResp.json()
  console.log('[CHECK] ✅ 正文生成完成:', JSON.stringify(batchData).substring(0, 200))

  // 验证生成后的文件内容
  const afterGenResp = await request.get(
    `http://localhost:8000/api/file?project_id=${projectId}&path=${sectionPath}`
  )
  expect(afterGenResp.ok()).toBeTruthy()
  const afterData = await afterGenResp.json()
  const bodyContent = afterData?.data?.content || ''
  console.log(`[CHECK] 生成后章节文件: ${bodyContent.length} 字符`)
  console.log(`[CHECK] 内容预览: "${bodyContent.substring(0, 100)}..."`)

  // ─── 正文质量验证 ────────────────────────────────
  console.log(`[CHECK] 最终正文长度: ${bodyContent.length} 字符`)
  expect(bodyContent.length).toBeGreaterThan(300)

  // 段落检查
  const paragraphs = bodyContent.split(/\n\s*\n/).filter(p => p.trim().length > 0)
  console.log(`[CHECK] 段落数: ${paragraphs.length}`)
  expect(paragraphs.length).toBeGreaterThanOrEqual(3)

  // 叙事标点检查
  const hasPeriod = bodyContent.includes('。')
  const hasComma = bodyContent.includes('，')
  const hasQuote = bodyContent.includes('「') || bodyContent.includes('"') || bodyContent.includes('"')
  console.log(`[CHECK] 句号: ${hasPeriod}, 逗号: ${hasComma}, 引号: ${hasQuote}`)
  expect(hasPeriod).toBeTruthy()

  // ─── UI 验证：刷新页面，点击文件树，编辑器应显示正文 ──
  console.log('[CHECK] 🔄 刷新页面，验证文件树展示和编辑器加载...')
  await page.reload({ waitUntil: 'load' })
  await page.waitForTimeout(2000)

  // 等待文件树出现
  const treeNode = page.locator('[class*="tree-node"]').first()
  await expect(treeNode).toBeVisible({ timeout: 10000 })

  // 在文件树中找到"第1节"并点击
  const secOne = page.locator('[class*="tree-node"] .node-name, .node-name').filter({ hasText: '第1节' }).first()
  await expect(secOne).toBeVisible({ timeout: 10000 })
  await secOne.click()
  await page.waitForTimeout(1500)

  // 验证编辑器显示文件内容
  const editorAfter = page.locator('.cm-content').first()
  let uiContent = ''
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(500)
    uiContent = await editorAfter.textContent().catch(() => '') || ''
    if (uiContent.length > 50) {
      console.log(`[CHECK] ✅ UI 编辑器已显示内容 (${uiContent.length} 字符，等待 ${(i + 1) * 0.5}s)`)
      break
    }
  }
  console.log(`[CHECK] UI 编辑器最终内容: ${uiContent.length} 字符`)
  if (uiContent.length > 50) {
    console.log(`[CHECK] UI 内容预览: "${uiContent.substring(0, 100)}..."`)
  } else {
    console.log('[ISSUE] ⚠️ 编辑器内容为空或不足 50 字符')
  }

  // 截图（编辑器应显示正文）
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '11-body-text-generation.png'),
    fullPage: false,
  })
  console.log('[CHECK] ✅ 截图已保存: 11-body-text-generation.png')
})
