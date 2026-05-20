/**
 * 小说场景质量评价工具
 *
 * 用于 E2E 测试中对 LLM 生成内容做自动化质量评估。
 * 不依赖外部 LLM 评审，纯规则检查。
 */

export interface QualityResult {
  entry: string
  test: string
  model: string
  provider: string
  length: number
  score: number
  grade: string
  passed: boolean
  issues: string[]
}

/** 提示词泄露关键词 */
const PROMPT_LEAK_PATTERNS = [
  '作为AI',
  '以下是',
  '场景目标',
  '根据你的要求',
  '我将为你',
  '作为一个人工智能',
  'As an AI',
  'Here is',
  'I will',
]

/** 上下文延续关键词（近未来悬疑场景） */
const CONTEXT_KEYWORDS = [
  '林澈',
  '地铁站',
  '芯片',
  '广告屏',
  '寻人启事',
  '黑塔',
  '沈知夏',
]

/**
 * 评价小说场景内容质量
 *
 * @param text 生成的内容
 * @param context 上下文信息（前文、角色、场景等）
 * @param options 评价选项
 */
export function evaluateFictionScene(
  text: string,
  context: {
    model: string
    provider: string
    entry?: string
    test?: string
    previousText?: string
  },
): QualityResult {
  const issues: string[] = []
  let score = 100

  // 1. 空内容检查
  if (!text || text.trim().length === 0) {
    return {
      entry: context.entry || 'main',
      test: context.test || 'unknown',
      model: context.model,
      provider: context.provider,
      length: 0,
      score: 0,
      grade: '不合格',
      passed: false,
      issues: ['内容为空'],
    }
  }

  const trimmedText = text.trim()
  const charCount = trimmedText.length

  // 2. 字数评分（目标 300-1200，宽容 150-2000）
  if (charCount < 150) {
    issues.push(`字数过少: ${charCount}字（最低150字）`)
    score -= 30
  } else if (charCount < 300) {
    issues.push(`字数偏少: ${charCount}字（建议300字以上）`)
    score -= 10
  } else if (charCount > 2000) {
    issues.push(`字数偏多: ${charCount}字（建议1200字以内）`)
    score -= 5
  }

  // 3. 段落结构
  const paragraphs = trimmedText.split(/\n\s*\n/).filter((p) => p.trim().length > 0)
  if (paragraphs.length < 2) {
    issues.push(`段落过少: ${paragraphs.length}段（建议至少2段）`)
    score -= 10
  }

  // 4. 中文标点
  if (!trimmedText.includes('。') || !trimmedText.includes('，')) {
    issues.push('缺少中文标点')
    score -= 15
  }

  // 5. 提示词泄露检查
  for (const pattern of PROMPT_LEAK_PATTERNS) {
    if (trimmedText.includes(pattern)) {
      issues.push(`提示词泄露: 包含"${pattern}"`)
      score -= 20
    }
  }

  // 6. 上下文延续检查
  const hasContextKeyword = CONTEXT_KEYWORDS.some((kw) => trimmedText.includes(kw))
  if (!hasContextKeyword) {
    issues.push('内容未延续前文情境（缺少关键词）')
    score -= 15
  }

  // 7. 重复检查（与上一段重复率过高）
  if (context.previousText) {
    const prevChars = new Set(context.previousText.slice(-200))
    const currChars = new Set(trimmedText.slice(0, 200))
    let overlap = 0
    for (const ch of currChars) {
      if (prevChars.has(ch) && ch.trim()) overlap++
    }
    const overlapRate = overlap / Math.max([...currChars].filter((c) => c.trim()).length, 1)
    if (overlapRate > 0.8) {
      issues.push('与上一段内容重复率过高')
      score -= 20
    }
  }

  // 计算最终分数和等级
  score = Math.max(0, Math.min(100, score))
  const passed = score >= 60
  let grade: string
  if (score >= 90) grade = '优秀'
  else if (score >= 75) grade = '良好'
  else if (score >= 60) grade = '合格'
  else grade = '不合格'

  return {
    entry: context.entry || 'main',
    test: context.test || 'unknown',
    model: context.model,
    provider: context.provider,
    length: charCount,
    score,
    grade,
    passed,
    issues,
  }
}
