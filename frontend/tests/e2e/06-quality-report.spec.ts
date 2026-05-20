/**
 * 06 - 统一质量报告
 *
 * 读取各入口质量 JSON，生成汇总报告。
 * 包含 qualityRubric 单元测试 + 统一报告生成。
 *
 * 需要 MOYUN_E2E_REAL_LLM=true 才会执行真实 LLM 相关部分。
 */

import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import { evaluateFictionScene, quickQualityCheck } from './helpers/qualityRubric'
import { generateQualityReport } from './helpers/qualityReport'
import { getLLMEnv, shouldSkipLLMTests } from './helpers/llmEnv'

const llmEnv = getLLMEnv()

test.describe('质量评分工具单元测试', () => {
  test('quickQualityCheck 对合格文本返回通过', () => {
    const goodText =
      '这是一段测试文本。它包含多个段落，每段都有内容。这段文字需要足够长才能通过字数检查，所以我们要多写一些内容来确保字数达标。\n\n' +
      '第二段也有一些文字，用来测试质量检查函数。我们需要确保整段文本的字数超过一百五十字的最低要求，这样才能通过基础有效性检查。\n\n' +
      '第三段继续补充内容，确保字数足够。质量检查函数会验证段落分隔、中文标点和字数等维度，所以每个方面都需要照顾到。'
    const result = quickQualityCheck(goodText)
    expect(result.passed).toBe(true)
    expect(result.checks.every((c) => c.passed)).toBe(true)
  })

  test('quickQualityCheck 对短文本返回失败', () => {
    const shortText = '太短'
    const result = quickQualityCheck(shortText)
    expect(result.passed).toBe(false)
  })

  test('evaluateFictionScene 对空内容返回 0 分', () => {
    const result = evaluateFictionScene('', {
      model: 'test',
      provider: 'test',
    })
    expect(result.score).toBe(0)
    expect(result.grade).toBe('不合格')
    expect(result.passed).toBe(false)
    expect(result.issues).toContain('内容为空')
  })

  test('evaluateFictionScene 对合格场景返回合格分数', () => {
    const goodScene =
      '林澈站在废弃地铁站的入口，雨水顺着铁栏往下淌。广告屏每隔十秒闪一下，屏幕上却不是商业广告，而是一张三年前的寻人启事。\n\n' +
      '他没有立刻进去。口袋里的芯片微微发烫，像是在提醒他，有人正等着他走进这条被封死的地下通道。\n\n' +
      '沈知夏从阴影中走出来，低声说："你迟到了。"她握紧手中的录音笔，眼神里有一丝不安。但林澈知道，她不会轻易退缩。'

    const result = evaluateFictionScene(goodScene, {
      model: 'test',
      provider: 'test',
      entry: 'main',
      test: 'unit_test',
      previousText: '林澈在地铁站入口等待。',
    })

    expect(result.score).toBeGreaterThanOrEqual(55)
    expect(result.passed).toBe(true)
    expect(result.metrics.hasCharacter).toBe(true)
    expect(result.metrics.hasLocation).toBe(true)
    expect(result.metrics.contextContinuity).toBe(true)
  })

  test('evaluateFictionScene 对提示词泄露严重扣分', () => {
    const leakedText =
      '作为AI，我将为你生成以下场景。以下是林澈的故事：\n\n' +
      '林澈站在地铁站入口。他看了看四周。'

    const result = evaluateFictionScene(leakedText, {
      model: 'test',
      provider: 'test',
    })

    expect(result.metrics.hasForbiddenPhrases).toBe(true)
    expect(result.issues.some((i) => i.includes('提示词泄露'))).toBe(true)
  })

  test('evaluateFictionScene 对大纲格式扣分', () => {
    const outlineText =
      '## 第一章\n\n' +
      '1. 林澈到达地铁站\n' +
      '2. 发现芯片异常\n' +
      '3. 遇到沈知夏\n' +
      '- 场景1：雨夜\n' +
      '- 场景2：对话'

    const result = evaluateFictionScene(outlineText, {
      model: 'test',
      provider: 'test',
    })

    expect(result.issues.some((i) => i.includes('大纲'))).toBe(true)
  })

  test('evaluateFictionScene 评分等级正确', () => {
    // 优秀场景
    const excellentScene =
      '林澈的手指在冰冷的铁栏上停住，雨水沿着指缝滑落。广告屏又闪了一下，那张寻人启事上的女孩似乎在对他笑。\n\n' +
      '"你不该来。"沈知夏的声音从身后传来，带着一丝颤抖。她攥紧录音笔，指节发白。\n\n' +
      '林澈没有回头。口袋里的芯片越来越烫，像一颗即将引爆的心脏。他知道，一旦走进那条通道，就没有回头路了。\n\n' +
      '但他还是迈出了第一步。地铁站的深处，传来一阵若有若无的机械运转声。'

    const result = evaluateFictionScene(excellentScene, {
      model: 'test',
      provider: 'test',
      previousText: '林澈在地铁站入口等待。',
    })

    expect(result.score).toBeGreaterThanOrEqual(70)
    expect(['优秀', '合格']).toContain(result.grade)
  })
})

test.describe('统一质量报告生成', () => {
  test.skip(shouldSkipLLMTests(), '需要 MOYUN_E2E_REAL_LLM=true')

  test('生成统一质量报告', () => {
    const { report, reportPath, mdPath } = generateQualityReport({
      provider: llmEnv.provider,
      model: llmEnv.model,
      baseUrl: llmEnv.baseUrl,
    })

    // 验证报告结构
    expect(report.testEnvironment.provider).toBe(llmEnv.provider)
    expect(report.testEnvironment.model).toBe(llmEnv.model)
    expect(report.testEnvironment.realLLM).toBe(true)

    // 验证报告文件已写入
    expect(fs.existsSync(reportPath)).toBe(true)
    expect(fs.existsSync(mdPath)).toBe(true)

    // 验证 Markdown 报告内容
    const mdContent = fs.readFileSync(mdPath, 'utf-8')
    expect(mdContent).toContain('# Moyun Studio Real LLM E2E Quality Report')
    expect(mdContent).toContain('## Test Environment')
    expect(mdContent).toContain('## Summary')
    expect(mdContent).toContain('## Key Issues')
    expect(mdContent).toContain('## Recommendations')

    // 验证通过标准
    // 1. 所有核心生成项 score >= 55
    const allAbove55 = report.summary.every((s) => s.score >= 55)
    if (report.summary.length > 0) {
      expect(allAbove55).toBe(true)
    }

    // 2. 至少 70% 生成项 score >= 70
    if (report.summary.length > 0) {
      const above70Ratio = report.summary.filter((s) => s.score >= 70).length / report.summary.length
      expect(above70Ratio).toBeGreaterThanOrEqual(0.7)
    }

    // 3. 不允许出现严重问题
    const hasPromptLeak = report.keyIssues.some((i) => i.includes('提示词泄露'))
    const hasEmptyOutput = report.keyIssues.some((i) => i.includes('空输出'))
    const hasOutline = report.keyIssues.some((i) => i.includes('大纲'))
    expect(hasPromptLeak).toBe(false)
    expect(hasEmptyOutput).toBe(false)
    expect(hasOutline).toBe(false)

    // 如果失败，输出报告路径
    if (!report.passed) {
      console.log(`Quality report: ${reportPath}`)
      console.log(`Markdown report: ${mdPath}`)
    }

    expect(report.passed).toBe(true)
  })
})
