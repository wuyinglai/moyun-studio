/**
 * 统一质量报告生成工具
 *
 * 读取各入口的质量 JSON，生成汇总 JSON 和 Markdown 报告。
 */

import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export interface SingleQualityResult {
  entry: string
  test: string
  model: string
  provider: string
  length: number
  score: number
  grade: string
  passed: boolean
  issues: string[]
  metrics?: Record<string, unknown>
}

export interface CandidateBatchQuality {
  model: string
  provider: string
  polish: {
    score: number
    grade: string
    passed: boolean
    issues: string[]
  }
  batch_generate: Array<{
    path: string
    score: number
    grade: string
    passed: boolean
    issues: string[]
  }>
}

export interface UnifiedReport {
  testEnvironment: {
    provider: string
    model: string
    baseUrl: string
    date: string
    realLLM: boolean
  }
  summary: Array<{
    entry: string
    score: number
    grade: string
    passed: boolean
  }>
  keyIssues: string[]
  recommendations: string[]
  passed: boolean
}

const RESULTS_DIR = path.join(__dirname, '..', '..', 'test-results')

function readJsonFile<T>(filePath: string): T | null {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
    }
  } catch {
    // 文件不存在或解析失败
  }
  return null
}

/** 生成统一质量报告 */
export function generateQualityReport(llmEnv: {
  provider: string
  model: string
  baseUrl: string
}): { report: UnifiedReport; reportPath: string; mdPath: string } {
  // 读取各入口质量数据
  const mainEntry = readJsonFile<SingleQualityResult>(
    path.join(RESULTS_DIR, 'main-entry-quality.json'),
  )
  const liteEntry = readJsonFile<SingleQualityResult>(
    path.join(RESULTS_DIR, 'lite-entry-quality.json'),
  )
  const candidateBatch = readJsonFile<CandidateBatchQuality>(
    path.join(RESULTS_DIR, 'candidate-batch-quality.json'),
  )

  // 汇总
  const summary: UnifiedReport['summary'] = []

  if (mainEntry) {
    summary.push({
      entry: `Main Entry - ${mainEntry.test || 'Write Next Scene'}`,
      score: mainEntry.score,
      grade: mainEntry.grade,
      passed: mainEntry.passed,
    })
  }

  if (liteEntry) {
    summary.push({
      entry: `Lite Entry - ${liteEntry.test || 'Quick Generate'}`,
      score: liteEntry.score,
      grade: liteEntry.grade,
      passed: liteEntry.passed,
    })
  }

  if (candidateBatch) {
    if (candidateBatch.polish) {
      summary.push({
        entry: 'Polish Candidate',
        score: candidateBatch.polish.score,
        grade: candidateBatch.polish.grade,
        passed: candidateBatch.polish.passed,
      })
    }
    for (const item of candidateBatch.batch_generate) {
      summary.push({
        entry: `Batch ${path.basename(item.path, '.md')}`,
        score: item.score,
        grade: item.grade,
        passed: item.passed,
      })
    }
  }

  // 关键问题
  const keyIssues: string[] = []

  const allResults = [mainEntry, liteEntry].filter(Boolean) as SingleQualityResult[]
  if (candidateBatch) {
    if (candidateBatch.polish) {
      allResults.push({
        entry: 'polish',
        test: 'polish',
        model: candidateBatch.model,
        provider: candidateBatch.provider,
        length: 0,
        score: candidateBatch.polish.score,
        grade: candidateBatch.polish.grade,
        passed: candidateBatch.polish.passed,
        issues: candidateBatch.polish.issues,
      })
    }
  }

  const hasAiFlavor = allResults.some((r) => r.issues?.some((i) => i.includes('AI 味') || i.includes('提示词泄露')))
  const hasPromptLeak = allResults.some((r) => r.issues?.some((i) => i.includes('提示词泄露')))
  const hasMissingContinuity = allResults.some((r) => r.issues?.some((i) => i.includes('承接') || i.includes('上下文')))
  const hasShortContent = allResults.some((r) => r.issues?.some((i) => i.includes('字数过少') || i.includes('字数偏少')))
  const hasLongContent = allResults.some((r) => r.issues?.some((i) => i.includes('字数偏多')))
  const hasEmptyOutput = allResults.some((r) => r.score === 0)
  const hasOutline = allResults.some((r) => r.issues?.some((i) => i.includes('大纲')))

  if (hasAiFlavor) keyIssues.push('存在 AI 味内容')
  if (hasPromptLeak) keyIssues.push('存在提示词泄露')
  if (hasMissingContinuity) keyIssues.push('缺少场景承接')
  if (hasShortContent) keyIssues.push('部分生成内容过短')
  if (hasLongContent) keyIssues.push('部分生成内容过长')
  if (hasEmptyOutput) keyIssues.push('存在空输出')
  if (hasOutline) keyIssues.push('生成内容像大纲而非正文')
  if (keyIssues.length === 0) keyIssues.push('无明显问题')

  // 建议
  const recommendations: string[] = []

  if (hasAiFlavor) recommendations.push('建议调整 prompt 以减少 AI 味输出')
  if (hasPromptLeak) recommendations.push('需要加强 prompt 隔离，防止提示词泄露到输出')
  if (hasMissingContinuity) recommendations.push('建议在 prompt 中加强前文上下文引用')
  if (hasShortContent) recommendations.push('建议调整模型参数（如 max_tokens）以生成更长内容')
  if (hasOutline) recommendations.push('建议在 prompt 中明确要求生成正文而非大纲')

  // 对比主入口和轻量入口
  if (mainEntry && liteEntry) {
    if (mainEntry.score > liteEntry.score + 10) {
      recommendations.push('主入口生成质量明显高于轻量入口，建议检查轻量入口 prompt')
    } else if (liteEntry.score > mainEntry.score + 10) {
      recommendations.push('轻量入口生成质量高于主入口，可参考其 prompt 优化主入口')
    } else {
      recommendations.push('两个入口生成质量相近，整体稳定')
    }
  }

  if (recommendations.length === 0) recommendations.push('整体质量良好，无需特别调整')

  // 通过标准
  const allPassed = summary.length > 0 && summary.every((s) => s.passed)
  const atLeast70PercentGood = summary.length > 0 && summary.filter((s) => s.score >= 70).length / summary.length >= 0.7
  const noFatalIssues = !hasPromptLeak && !hasEmptyOutput && !hasOutline
  const passed = allPassed && atLeast70PercentGood && noFatalIssues

  const report: UnifiedReport = {
    testEnvironment: {
      provider: llmEnv.provider,
      model: llmEnv.model,
      baseUrl: llmEnv.baseUrl.replace(/\/v1\/?$/, ''), // 脱敏：去掉路径后缀
      date: new Date().toISOString().split('T')[0],
      realLLM: true,
    },
    summary,
    keyIssues,
    recommendations,
    passed,
  }

  // 写入 JSON
  if (!fs.existsSync(RESULTS_DIR)) {
    fs.mkdirSync(RESULTS_DIR, { recursive: true })
  }
  const reportPath = path.join(RESULTS_DIR, 'llm-quality-report.json')
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8')

  // 写入 Markdown
  const mdPath = path.join(RESULTS_DIR, 'llm-quality-report.md')
  const md = generateMarkdown(report)
  fs.writeFileSync(mdPath, md, 'utf-8')

  return { report, reportPath, mdPath }
}

function generateMarkdown(report: UnifiedReport): string {
  const lines: string[] = []

  lines.push('# Moyun Studio Real LLM E2E Quality Report')
  lines.push('')

  lines.push('## Test Environment')
  lines.push('')
  lines.push(`- Provider: ${report.testEnvironment.provider}`)
  lines.push(`- Model: ${report.testEnvironment.model}`)
  lines.push(`- Base URL: ${report.testEnvironment.baseUrl}`)
  lines.push(`- Date: ${report.testEnvironment.date}`)
  lines.push(`- Real LLM: ${report.testEnvironment.realLLM}`)
  lines.push('')

  lines.push('## Summary')
  lines.push('')
  lines.push('| Entry / Feature | Score | Grade | Passed |')
  lines.push('|---|---:|---|---|')
  for (const item of report.summary) {
    const passedText = item.passed ? 'Yes' : 'No'
    lines.push(`| ${item.entry} | ${item.score} | ${item.grade} | ${passedText} |`)
  }
  lines.push('')

  lines.push('## Key Issues')
  lines.push('')
  for (const issue of report.keyIssues) {
    lines.push(`- ${issue}`)
  }
  lines.push('')

  lines.push('## Recommendations')
  lines.push('')
  for (const rec of report.recommendations) {
    lines.push(`- ${rec}`)
  }
  lines.push('')

  lines.push('## Overall Result')
  lines.push('')
  lines.push(report.passed ? '**PASSED** - All quality checks passed.' : '**FAILED** - Some quality checks did not pass.')
  lines.push('')

  return lines.join('\n')
}
