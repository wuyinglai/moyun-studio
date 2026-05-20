/**
 * 06 - 质量报告测试
 *
 * 包含 quickQualityCheck 工具函数的单元级验证，
 * 以及真实 LLM 生成内容的质量评估占位。
 */

import { test, expect } from '@playwright/test'
import { quickQualityCheck } from './helpers/qualityRubric'
import { shouldSkipLLMTests } from './helpers/llmEnv'

test.describe('质量报告测试', () => {
  test('quickQualityCheck 对合格文本返回通过', () => {
    const goodText =
      '这是一段测试文本。它包含多个段落，每段都有内容。\n\n' +
      '第二段也有一些文字，用来测试质量检查函数。\n\n' +
      '第三段继续补充内容，确保字数足够。'
    const result = quickQualityCheck(goodText)
    expect(result.passed).toBe(true)
    expect(result.checks.every((c) => c.passed)).toBe(true)
  })

  test('quickQualityCheck 对短文本返回失败', () => {
    const shortText = '太短'
    const result = quickQualityCheck(shortText)
    expect(result.passed).toBe(false)
  })

  test('quickQualityCheck 对无段落分隔文本返回失败', () => {
    const flatText = '这是一段没有段落分隔的文本，虽然字数可能够了，但是缺少段落结构。'
    const result = quickQualityCheck(flatText)
    expect(result.passed).toBe(false)
  })

  // 真实 LLM 测试：需要 MOYUN_E2E_REAL_LLM=true
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')

  test('真实 LLM 生成内容质量检查（占位）', async ({ page }) => {
    // TODO: 后续补充 — 使用真实 LLM 生成内容 → 质量检查
    test.skip()
  })
})
