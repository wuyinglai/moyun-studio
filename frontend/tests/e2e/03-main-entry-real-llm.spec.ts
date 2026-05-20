/**
 * 03 - 主入口真实 LLM 测试
 *
 * 验证主创作工作台入口核心流程：
 * 配置真实 LLM → 创建项目 → 打开/创建 sec-001.md → 保存正文 → 写下一场景 → 生成 sec-002.md → 质量评价
 *
 * 需要 MOYUN_E2E_REAL_LLM=true 才会执行。
 */

import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { openMainEntry } from './helpers/entryHelpers'
import { getLLMEnv, shouldSkipLLMTests } from './helpers/llmEnv'
import { getByTestId, dismissViteOverlay, createErrorCollector, filterSevereErrors } from './helpers/e2eUtils'
import { TEST_PROJECT } from './helpers/testData'
import { getNextScenePath, buildScenePath } from './helpers/scenePath'
import { evaluateFictionScene } from './helpers/qualityRubric'

const llmEnv = getLLMEnv()

// 整个 describe 跳过条件
test.describe('主入口真实 LLM 测试', () => {
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')

  // ── 测试 1：配置真实 LLM ──────────────────────────────
  test('配置真实 LLM 并测试连接', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 打开设置
    await getByTestId(page, 'settings-button').click()
    await page.waitForTimeout(500)

    // 确认设置弹窗可见
    const settingsModal = getByTestId(page, 'settings-modal')
    await expect(settingsModal).toBeVisible({ timeout: 5000 })

    // 选择 provider
    const providerSelect = getByTestId(page, 'llm-provider-select')
    await providerSelect.click()
    await page.waitForTimeout(300)

    // 选择 deepseek 或 openai
    const providerOption = page.locator('.ant-select-item-option').filter({ hasText: /DeepSeek|OpenAI/i }).first()
    if (await providerOption.isVisible()) {
      await providerOption.click()
    } else {
      // 选择第一个可用选项
      await page.locator('.ant-select-item-option').first().click()
    }
    await page.waitForTimeout(300)

    // 填写 base_url（如果可见）
    const baseUrlInput = getByTestId(page, 'llm-base-url-input')
    if (await baseUrlInput.isVisible()) {
      await baseUrlInput.click()
      await baseUrlInput.fill('')
      await baseUrlInput.fill(llmEnv.baseUrl)
    }

    // 填写 model — 找到模型输入框
    const modelInput = page.locator('.ant-modal').locator('input').filter({ has: page.locator('[placeholder*="模型"]') }).first()
    if (await modelInput.isVisible().catch(() => false)) {
      await modelInput.click()
      await modelInput.fill('')
      await modelInput.fill(llmEnv.model)
    } else {
      // 回退：找设置弹窗内所有 input，模型是第4个
      const inputs = page.locator('.ant-modal .ant-input, .ant-modal .ant-input-password')
      const inputCount = await inputs.count()
      for (let i = 0; i < inputCount; i++) {
        const placeholder = await inputs.nth(i).getAttribute('placeholder')
        if (placeholder?.includes('模型') || placeholder?.includes('model')) {
          await inputs.nth(i).fill(llmEnv.model)
          break
        }
      }
    }

    // 填写 API Key（如果存在）
    if (llmEnv.apiKey) {
      const apiKeyInput = getByTestId(page, 'llm-api-key-input')
      if (await apiKeyInput.isVisible().catch(() => false)) {
        await apiKeyInput.click()
        await apiKeyInput.fill('')
        await apiKeyInput.fill(llmEnv.apiKey)
      } else {
        // 回退：找 password 类型输入框
        const passwordInputs = page.locator('.ant-modal input[type="password"], .ant-modal .ant-input-password input')
        if (await passwordInputs.count() > 0) {
          await passwordInputs.first().fill(llmEnv.apiKey)
        }
      }
    }

    // 点击测试连接
    await getByTestId(page, 'llm-test-button').click()
    await page.waitForTimeout(5000)

    // 检查连接结果
    const alert = page.locator('.ant-modal .ant-alert').first()
    await expect(alert).toBeVisible({ timeout: 15000 })

    // 验证 localStorage 不包含 API Key 明文
    const localStorageKeys = await page.evaluate(() => Object.keys(localStorage))
    for (const key of localStorageKeys) {
      const value = await page.evaluate((k) => localStorage.getItem(k), key)
      if (llmEnv.apiKey && value) {
        expect(value).not.toContain(llmEnv.apiKey)
      }
    }

    // 保存设置（点击 OK 按钮）
    const okBtn = page.locator('.ant-modal .ant-btn-primary').filter({ hasText: /保存|确定|OK/i }).first()
    if (await okBtn.isVisible()) {
      await okBtn.click()
      await page.waitForTimeout(500)
    } else {
      // 关闭弹窗
      await page.keyboard.press('Escape')
    }
  })

  // ── 测试 2：创建项目 ──────────────────────────────
  test('创建项目', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(1500)

    // 点击新建项目
    await getByTestId(page, 'new-project-button').click()
    await page.waitForTimeout(500)

    // 确认弹窗可见
    const modal = getByTestId(page, 'create-project-modal')
    await expect(modal.or(page.locator('.ant-modal').first())).toBeVisible({ timeout: 5000 })

    // 填写项目名称
    const nameInput = getByTestId(page, 'create-project-name-input')
    await expect(nameInput).toBeVisible({ timeout: 5000 })
    await nameInput.click()
    await nameInput.fill(TEST_PROJECT.name)

    // 选择题材 — 点击第一个可用的 radio-button
    const genreRadio = page.locator('.ant-modal .ant-radio-button-wrapper').first()
    if (await genreRadio.isVisible()) {
      await genreRadio.click()
      await page.waitForTimeout(300)
    }

    // 选择写作风格
    const styleRadios = page.locator('.ant-modal .ant-radio-button-wrapper')
    const styleCount = await styleRadios.count()
    if (styleCount > 5) {
      // 写作风格在题材之后，选择中间的
      await styleRadios.nth(Math.min(6, styleCount - 1)).click()
    }

    // 展开高级设置（如果折叠了）
    const collapseHeader = page.locator('.ant-collapse-header').first()
    if (await collapseHeader.isVisible().catch(() => false)) {
      await collapseHeader.click()
      await page.waitForTimeout(300)
    }

    // 选择作品规模 = 5万字
    const scaleRadios = page.locator('.ant-radio-button-wrapper')
    const scaleCount = await scaleRadios.count()
    for (let i = 0; i < scaleCount; i++) {
      const text = await scaleRadios.nth(i).textContent()
      if (text?.includes('5万')) {
        await scaleRadios.nth(i).click()
        break
      }
    }

    // 提交创建
    const submitBtn = getByTestId(page, 'create-project-submit')
    await expect(submitBtn).toBeEnabled({ timeout: 3000 })
    await submitBtn.click()

    // 等待项目创建（可能需要 LLM 生成初始内容）
    await page.waitForTimeout(3000)

    // 验证项目已创建 — 文件树应加载
    const fileTree = getByTestId(page, 'file-tree')
    await expect(fileTree).toBeVisible({ timeout: 15000 })

    // 验证文件树中有内容
    const treeContent = page.locator('.tree-content, .file-tree .tree-node, .file-tree [class*="node"]')
    await expect(treeContent.first()).toBeVisible({ timeout: 10000 })
  })

  // ── 测试 3：创建/打开 sec-001.md 并保存正文 ──────────────────────────────
  test('打开 sec-001.md 并保存正文', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // 尝试在文件树中找到 sec-001.md 或创建它
    const sec001Path = buildScenePath(1, 1, 1)
    const sec001Name = 'sec-001.md'

    // 检查文件树中是否已有 sec-001.md
    let sec001Node = page.locator('.file-tree').locator(`text=${sec001Name}`).first()
    const sec001Exists = await sec001Node.isVisible().catch(() => false)

    if (!sec001Exists) {
      // 需要创建文件 — 使用新建文件按钮
      // 先找到 chapters/vol-01/ch-001 目录，如果不存在需要展开
      const ch001Dir = page.locator('.file-tree').locator('text=ch-001').first()
      const ch001Visible = await ch001Dir.isVisible().catch(() => false)

      if (ch001Visible) {
        await ch001Dir.click()
        await page.waitForTimeout(500)
      }

      // 使用新建文件功能 — 通过 API 直接创建更可靠
      await page.evaluate(async (filePath) => {
        const projectId = window.__MOYUN_PROJECT_ID__
        if (!projectId) return
        await fetch('/api/file/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: projectId, path: filePath, content: '' }),
        })
      }, sec001Path)

      // 刷新文件树
      const refreshBtn = page.locator('.file-tree .tree-refresh-btn, .file-tree button[title*="刷新"]').first()
      if (await refreshBtn.isVisible().catch(() => false)) {
        await refreshBtn.click()
      }
      await page.waitForTimeout(1000)
    }

    // 点击 sec-001.md 打开
    sec001Node = page.locator('.file-tree').locator(`text=${sec001Name}`).first()
    if (await sec001Node.isVisible().catch(() => false)) {
      await sec001Node.click()
      await page.waitForTimeout(500)
    }

    // 在编辑器中写入测试正文
    // CodeMirror 编辑器需要特殊方式输入
    const editorArea = page.locator('.cm-content, .CodeMirror, [data-testid="editor-textarea"]').first()
    if (await editorArea.isVisible().catch(() => false)) {
      await editorArea.click()
      // 全选并替换
      await page.keyboard.press('Control+a')
      await page.keyboard.press('Backspace')
      await page.keyboard.type(TEST_PROJECT.initialText, { delay: 10 })
    } else {
      // 回退：通过 API 直接写入
      await page.evaluate(async (content) => {
        const projectId = window.__MOYUN_PROJECT_ID__
        if (!projectId) return
        await fetch('/api/file/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: projectId, path: 'chapters/vol-01/ch-001/sec-001.md', content }),
        })
      }, TEST_PROJECT.initialText)
    }

    // 保存
    const saveBtn = page.locator('[data-testid="save-file-button"], button:has-text("保存")').first()
    if (await saveBtn.isVisible().catch(() => false)) {
      await saveBtn.click()
    } else {
      // Ctrl+S 保存
      await page.keyboard.press('Control+s')
    }
    await page.waitForTimeout(1000)

    // 刷新页面
    await page.reload()
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // 再次打开 sec-001.md
    sec001Node = page.locator('.file-tree').locator(`text=${sec001Name}`).first()
    if (await sec001Node.isVisible().catch(() => false)) {
      await sec001Node.click()
      await page.waitForTimeout(1000)
    }

    // 验证内容存在
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toContain('林澈')

    // 无 Vue runtime error
    const errors = createErrorCollector(page)
    await page.waitForTimeout(2000)
    const severeErrors = filterSevereErrors(errors)
    expect(severeErrors.filter((e) => e.includes('Vue') || e.includes('runtime'))).toEqual([])
  })

  // ── 测试 4：写下一场景生成 sec-002.md ──────────────────────────────
  test('写下一场景生成 sec-002.md', async ({ page }) => {
    await openMainEntry(page)
    await dismissViteOverlay(page)
    await page.waitForTimeout(2000)

    // 确保 sec-001.md 已打开
    const sec001Node = page.locator('.file-tree').locator('text=sec-001.md').first()
    if (await sec001Node.isVisible().catch(() => false)) {
      await sec001Node.click()
      await page.waitForTimeout(500)
    }

    // 点击"写下一部分"
    const writeNextBtn = getByTestId(page, 'write-next-button')
    await expect(writeNextBtn).toBeVisible({ timeout: 10000 })
    await writeNextBtn.click()

    // 等待 LLM 生成完成（最长 180 秒）
    // 观察文件树中是否出现 sec-002.md 或编辑器内容变化
    const sec002Name = 'sec-002.md'
    const maxWait = 180000
    const startTime = Date.now()
    let sec002Found = false

    while (Date.now() - startTime < maxWait) {
      // 检查文件树
      const sec002Node = page.locator('.file-tree').locator(`text=${sec002Name}`).first()
      if (await sec002Node.isVisible().catch(() => false)) {
        sec002Found = true
        break
      }

      // 检查是否有生成中的指示
      const generatingIndicator = page.locator('.generating, .llm-generating, [class*="generating"]').first()
      const isGenerating = await generatingIndicator.isVisible().catch(() => false)

      if (!isGenerating && Date.now() - startTime > 10000) {
        // 可能已经生成完了但文件名不同，或者生成失败
        // 再检查一次文件树
        await page.waitForTimeout(2000)
        const sec002Retry = page.locator('.file-tree').locator(`text=${sec002Name}`).first()
        if (await sec002Retry.isVisible().catch(() => false)) {
          sec002Found = true
          break
        }
      }

      await page.waitForTimeout(3000)
    }

    expect(sec002Found).toBe(true)

    // 打开 sec-002.md 查看内容
    const sec002Node = page.locator('.file-tree').locator(`text=${sec002Name}`).first()
    await sec002Node.click()
    await page.waitForTimeout(1000)

    // 获取编辑器内容
    let sec002Content = ''
    const cmContent = page.locator('.cm-content').first()
    if (await cmContent.isVisible().catch(() => false)) {
      sec002Content = (await cmContent.textContent()) || ''
    }

    // 如果 CodeMirror 不可见，尝试 textarea
    if (!sec002Content) {
      const textarea = page.locator('.chapter-textarea, textarea').first()
      if (await textarea.isVisible().catch(() => false)) {
        sec002Content = (await textarea.inputValue()) || ''
      }
    }

    // 验证内容
    expect(sec002Content.length).toBeGreaterThan(0)

    // 字数检查（宽容 150-2000）
    expect(sec002Content.length).toBeGreaterThanOrEqual(150)
    expect(sec002Content.length).toBeLessThanOrEqual(2000)

    // 提示词泄露检查
    const leakPatterns = ['作为AI', '以下是', '场景目标', '根据你的要求', '我将为你']
    for (const pattern of leakPatterns) {
      expect(sec002Content).not.toContain(pattern)
    }

    // 上下文延续检查
    const contextKeywords = ['林澈', '地铁站', '芯片', '广告屏', '寻人启事', '黑塔', '沈知夏']
    const hasContext = contextKeywords.some((kw) => sec002Content.includes(kw))
    expect(hasContext).toBe(true)

    // 质量评价并写入结果
    const qualityResult = evaluateFictionScene(sec002Content, {
      model: llmEnv.model,
      provider: llmEnv.provider,
      entry: 'main',
      test: 'write_next_scene',
      previousText: TEST_PROJECT.initialText,
    })

    // 写入质量报告
    const resultsDir = path.join(__dirname, '..', '..', 'test-results')
    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir, { recursive: true })
    }
    const reportPath = path.join(resultsDir, 'main-entry-quality.json')
    fs.writeFileSync(reportPath, JSON.stringify(qualityResult, null, 2), 'utf-8')

    // 测试断言
    expect(qualityResult.passed).toBe(true)
  })

  // ── 测试 5：场景路径跳转规则 ──────────────────────────────
  test('场景路径跳转规则', () => {
    // sec-001 → sec-002
    const sec001 = buildScenePath(1, 1, 1)
    const nextOf001 = getNextScenePath(sec001)
    expect(nextOf001).toBe(buildScenePath(1, 1, 2))

    // sec-005 → ch-002/sec-001
    const sec005 = buildScenePath(1, 1, 5)
    const nextOf005 = getNextScenePath(sec005)
    expect(nextOf005).toBe(buildScenePath(1, 2, 1))

    // ch-012/sec-005 → vol-02/ch-001/sec-001
    const sec125 = buildScenePath(1, 12, 5)
    const nextOf125 = getNextScenePath(sec125)
    expect(nextOf125).toBe(buildScenePath(2, 1, 1))
  })
})
