/**
 * 小说场景质量评分标准（五维度，总分 100）
 *
 * 1. 基础有效性 20 分
 * 2. 场景完整性 20 分
 * 3. 连续性 20 分
 * 4. 去 AI 味 20 分
 * 5. 文学质感 20 分
 */

export interface QualityMetrics {
  charCount: number
  hasCharacter: boolean
  hasLocation: boolean
  hasAction: boolean
  hasCliffhanger: boolean
  hasForbiddenPhrases: boolean
  hasDialogue: boolean
  hasDetail: boolean
  hasEmotionCarrier: boolean
  hasVariedSentences: boolean
  contextContinuity: boolean
}

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
  metrics: QualityMetrics
}

/** 提示词泄露关键词 */
const PROMPT_LEAK_PATTERNS = [
  '作为AI',
  '作为一个人工智能',
  '以下是',
  '下面是',
  '根据要求',
  '根据你的要求',
  '我将为你',
  '场景目标',
  'As an AI',
  'Here is',
  'I will',
]

/** AI 味关键词（扣分项） */
const AI_FLAVOR_PATTERNS = [
  '他终于明白',
  '真正重要的是',
  '命运的齿轮',
  '这一切都是值得的',
  '他意识到',
  '她终于理解了',
  '一切都有了答案',
  '命运的安排',
]

/** 大纲/说明文特征 */
const OUTLINE_PATTERNS = [
  /^#{1,6}\s/m,          // Markdown 标题
  /^\d+\.\s/m,           // 数字编号列表
  /^[-*]\s/m,            // 无序列表
  /^场景\s*\d/m,         // "场景 N" 格式
  /^第[一二三四五六七八九十]+[章节幕]/m,  // 章节标题格式
]

/** 抽象情绪词（过多则扣分） */
const ABSTRACT_EMOTION_WORDS = [
  '感动', '震撼', '温暖', '心酸', '欣慰', '感慨', '唏嘘',
  '动容', '感伤', '忧伤', '惆怅', '释然', '豁然开朗',
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

/** 人物关键词 */
const CHARACTER_PATTERNS = [
  /[林沈王张李陈刘赵黄周吴徐孙胡朱高林何郭马罗]/,
  /他|她|他们|她们/,
]

/** 地点/空间关键词 */
const LOCATION_PATTERNS = [
  /站|楼|室|巷|街|道|桥|塔|门|窗|走廊|楼梯|房间|大厅|广场|角落/,
  /地铁|火车|飞机|车|船/,
  /雨|雪|风|雾|夜|晨|昏/,
]

/** 动作/事件关键词 */
const ACTION_PATTERNS = [
  /走|跑|站|坐|躺|抓|握|推|拉|敲|打|扔|捡|翻|看|听|说|喊|叫|笑|哭|叹/,
  /打开|关闭|拿起|放下|转身|回头|靠近|远离|进入|离开/,
]

/** 悬念/承接关键词 */
const CLIFFHANGER_PATTERNS = [
  /但|却|然而|不过|只是|突然|忽然|就在|直到|谁知|没想到|不料|竟然|居然/,
  /？|\.\.\./,
  /还没|尚未|正要|刚要|即将/,
]

/** 对话标记 */
const DIALOGUE_PATTERNS = [
  /[""「」『』]/,
  /说道|问道|喊道|低声|轻声|喃喃|嘀咕|回应|回答/,
]

/** 具体细节标记 */
const DETAIL_PATTERNS = [
  /\d+/,                    // 数字
  /厘米|米|公里|千克|度/,    // 量词
  /红|蓝|绿|黑|白|灰|黄|紫/, // 颜色
  /铁|木|石|玻璃|金属|塑料/,  // 材质
  /冷|热|湿|干|滑|粗糙|光滑/, // 触感
]

/** 情绪承载物/动作细节 */
const EMOTION_CARRIER_PATTERNS = [
  /握紧|攥紧|咬唇|皱眉|叹气|深呼吸|闭眼|睁眼|低头|抬头/,
  /颤抖|发抖|僵硬|放松|紧绷|心跳|呼吸/,
  /沉默|无言|欲言又止|吞咽|咽了口/,
]

/**
 * 评价小说场景内容质量（五维度评分）
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

  // 空内容直接返回 0 分
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
      metrics: {
        charCount: 0,
        hasCharacter: false,
        hasLocation: false,
        hasAction: false,
        hasCliffhanger: false,
        hasForbiddenPhrases: false,
        hasDialogue: false,
        hasDetail: false,
        hasEmotionCarrier: false,
        hasVariedSentences: false,
        contextContinuity: false,
      },
    }
  }

  const trimmedText = text.trim()
  const charCount = trimmedText.length

  // ── 维度 1：基础有效性 20 分 ──────────────────────────────
  let basicScore = 0

  // 非空：5 分
  basicScore += 5

  // 字数合理：5 分（150-2000 宽容范围）
  if (charCount >= 150 && charCount <= 2000) {
    basicScore += 5
  } else if (charCount >= 100) {
    basicScore += 3
    issues.push(`字数偏少: ${charCount}字（建议150字以上）`)
  } else {
    issues.push(`字数过少: ${charCount}字（最低150字）`)
  }

  // 不是大纲/说明/标题：5 分
  const isOutline = OUTLINE_PATTERNS.some((p) => p.test(trimmedText))
  if (!isOutline) {
    basicScore += 5
  } else {
    issues.push('内容像大纲或说明文，不是正文')
  }

  // 无提示词泄露：5 分
  const hasLeak = PROMPT_LEAK_PATTERNS.some((p) => trimmedText.includes(p))
  if (!hasLeak) {
    basicScore += 5
  } else {
    const leakedPatterns = PROMPT_LEAK_PATTERNS.filter((p) => trimmedText.includes(p))
    issues.push(`提示词泄露: 包含"${leakedPatterns.join('", "')}"`)
  }

  // ── 维度 2：场景完整性 20 分 ──────────────────────────────
  let sceneScore = 0

  const hasCharacter = CHARACTER_PATTERNS.some((p) => p.test(trimmedText))
  if (hasCharacter) sceneScore += 5
  else issues.push('缺少具体人物')

  const hasLocation = LOCATION_PATTERNS.some((p) => p.test(trimmedText))
  if (hasLocation) sceneScore += 5
  else issues.push('缺少明确地点或空间')

  const hasAction = ACTION_PATTERNS.some((p) => p.test(trimmedText))
  if (hasAction) sceneScore += 5
  else issues.push('缺少动作或事件推进')

  const hasCliffhanger = CLIFFHANGER_PATTERNS.some((p) => p.test(trimmedText))
  if (hasCliffhanger) sceneScore += 5
  else issues.push('缺少结尾承接点或悬念')

  // ── 维度 3：连续性 20 分 ──────────────────────────────
  let continuityScore = 0

  // 承接前文人物
  const contextContinuity = CONTEXT_KEYWORDS.some((kw) => trimmedText.includes(kw))
  if (context.previousText) {
    // 从前文中提取人名（简单提取：2-3字中文词）
    const prevNames = context.previousText.match(/[\u4e00-\u9fa5]{2,3}/g) || []
    const uniqueNames = [...new Set(prevNames)].slice(0, 20)
    const hasPrevCharacter = uniqueNames.some((name) => trimmedText.includes(name))
    if (hasPrevCharacter || contextContinuity) continuityScore += 5
    else issues.push('未承接前文人物')
  } else {
    continuityScore += contextContinuity ? 5 : 0
    if (!contextContinuity) issues.push('缺少上下文关键词')
  }

  // 承接前文物件/线索
  if (context.previousText) {
    const prevItems = ['芯片', '广告屏', '寻人启事', '地铁', '黑塔', '通道', '铁栏']
    const hasPrevItem = prevItems.some((item) => context.previousText!.includes(item) && trimmedText.includes(item))
    if (hasPrevItem) continuityScore += 5
    else continuityScore += 2 // 宽容：不一定非要延续同一物件
  } else {
    continuityScore += 3
  }

  // 不突然换题材/世界观
  const genreKeywords = ['AI', '系统', '城市', '芯片', '数据', '监控', '算法', '网络', '程序']
  const hasGenreShift = context.previousText
    ? genreKeywords.some((kw) => context.previousText!.includes(kw)) && !trimmedText.includes('仙') && !trimmedText.includes('修真') && !trimmedText.includes('灵气')
    : false
  if (!hasGenreShift) continuityScore += 5
  else {
    issues.push('突然换了题材/世界观')
  }

  // 不提前跳到过远剧情
  const timeSkipPatterns = ['三年后', '五年后', '十年后', '多年后', '后来', '最终']
  const hasTimeSkip = timeSkipPatterns.some((p) => trimmedText.includes(p))
  if (!hasTimeSkip) continuityScore += 5
  else issues.push('提前跳到过远剧情')

  // ── 维度 4：去 AI 味 20 分 ──────────────────────────────
  let deAiScore = 20

  // 出现"作为AI"：-10
  if (trimmedText.includes('作为AI') || trimmedText.includes('作为一个人工智能')) {
    deAiScore -= 10
  }

  // 出现"以下是/下面是/根据要求"：-5
  if (['以下是', '下面是', '根据要求', '根据你的要求'].some((p) => trimmedText.includes(p))) {
    deAiScore -= 5
  }

  // 出现 AI 味套话：-5
  const hasAiFlavor = AI_FLAVOR_PATTERNS.some((p) => trimmedText.includes(p))
  if (hasAiFlavor) {
    deAiScore -= 5
    issues.push('包含 AI 味套话')
  }

  // 过多抽象情绪词：-5
  const emotionCount = ABSTRACT_EMOTION_WORDS.filter((w) => trimmedText.includes(w)).length
  if (emotionCount >= 3) {
    deAiScore -= 5
    issues.push(`抽象情绪词过多: ${emotionCount}个`)
  }

  // 段尾主题升华明显：-5
  const lastParagraph = trimmedText.split(/\n\s*\n/).pop() || ''
  const sublimationPatterns = ['这一切', '生命', '命运', '意义', '真相', '终究', '宿命']
  const hasSublimation = sublimationPatterns.some((p) => lastParagraph.includes(p))
  if (hasSublimation && lastParagraph.length < 100) {
    deAiScore -= 5
    issues.push('段尾主题升华明显')
  }

  deAiScore = Math.max(0, deAiScore)

  // ── 维度 5：文学质感 20 分 ──────────────────────────────
  let literaryScore = 0

  // 有具体细节：5
  const hasDetail = DETAIL_PATTERNS.some((p) => p.test(trimmedText))
  if (hasDetail) literaryScore += 5
  else issues.push('缺少具体细节描写')

  // 有对话或潜台词：5
  const hasDialogue = DIALOGUE_PATTERNS.some((p) => p.test(trimmedText))
  if (hasDialogue) literaryScore += 5
  // 对话不是必须的，没有也不扣太多

  // 有情绪承载物或动作细节：5
  const hasEmotionCarrier = EMOTION_CARRIER_PATTERNS.some((p) => p.test(trimmedText))
  if (hasEmotionCarrier) literaryScore += 5
  else issues.push('缺少情绪承载物或动作细节')

  // 句式不完全重复：5
  const sentences = trimmedText.split(/[。！？]/).filter((s) => s.trim().length > 5)
  const uniqueStarts = new Set(sentences.map((s) => s.trim().slice(0, 4)))
  const hasVariedSentences = sentences.length < 3 || uniqueStarts.size / sentences.length > 0.5
  if (hasVariedSentences) literaryScore += 5
  else issues.push('句式重复过多')

  // ── 汇总 ──────────────────────────────
  const score = Math.max(0, Math.min(100, basicScore + sceneScore + continuityScore + deAiScore + literaryScore))
  let grade: string
  if (score >= 85) grade = '优秀'
  else if (score >= 70) grade = '合格'
  else if (score >= 55) grade = '可用但需修改'
  else grade = '不合格'

  const passed = score >= 55

  const metrics: QualityMetrics = {
    charCount,
    hasCharacter,
    hasLocation,
    hasAction,
    hasCliffhanger,
    hasForbiddenPhrases: hasLeak,
    hasDialogue,
    hasDetail,
    hasEmotionCarrier,
    hasVariedSentences,
    contextContinuity,
  }

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
    metrics,
  }
}

/** 简单的自动化质量检查（向后兼容） */
export function quickQualityCheck(text: string): {
  passed: boolean
  checks: Array<{ name: string; passed: boolean; detail: string }>
} {
  const checks = [
    {
      name: '最低字数（≥150字）',
      passed: text.length >= 150,
      detail: `实际 ${text.length} 字`,
    },
    {
      name: '段落分隔（≥2段）',
      passed: text.split(/\n\s*\n/).filter((p) => p.trim().length > 0).length >= 2,
      detail: `实际 ${text.split(/\n\s*\n/).filter((p) => p.trim().length > 0).length} 段`,
    },
    {
      name: '中文标点',
      passed: text.includes('。') && text.includes('，'),
      detail: `句号: ${text.includes('。')}, 逗号: ${text.includes('，')}`,
    },
    {
      name: '非纯空白',
      passed: text.trim().length > 0,
      detail: `有效字符 ${text.trim().length}`,
    },
  ]

  return {
    passed: checks.every((c) => c.passed),
    checks,
  }
}

export const QUALITY_RUBRIC = {
  basicValidity: { label: '基础有效性', maxScore: 20 },
  sceneCompleteness: { label: '场景完整性', maxScore: 20 },
  continuity: { label: '连续性', maxScore: 20 },
  deAiFlavor: { label: '去AI味', maxScore: 20 },
  literaryQuality: { label: '文学质感', maxScore: 20 },
} as const

export type RubricKey = keyof typeof QUALITY_RUBRIC
