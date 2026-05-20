/**
 * 质量评分标准
 */

export interface QualityScore {
  dimension: string
  score: number // 0-5
  reason: string
}

export const QUALITY_RUBRIC = {
  coherence: {
    label: '叙事连贯性',
    threshold: 3,
    description: '段落之间逻辑通顺，无突兀跳转',
  },
  characterConsistency: {
    label: '角色一致性',
    threshold: 3,
    description: '角色行为符合设定，无 OOC',
  },
  sceneDescription: {
    label: '场景描写',
    threshold: 3,
    description: '场景描写生动具体，有画面感',
  },
  languageQuality: {
    label: '语言质量',
    threshold: 3,
    description: '语言流畅，无病句，标点正确',
  },
  plotProgression: {
    label: '情节推进',
    threshold: 3,
    description: '情节有推进，非纯描写或重复',
  },
} as const

export type RubricKey = keyof typeof QUALITY_RUBRIC

/** 简单的自动化质量检查（不依赖 LLM 评审） */
export function quickQualityCheck(text: string): {
  passed: boolean
  checks: Array<{ name: string; passed: boolean; detail: string }>
} {
  const checks = [
    {
      name: '最低字数（≥300字）',
      passed: text.length >= 300,
      detail: `实际 ${text.length} 字`,
    },
    {
      name: '段落分隔（≥3段）',
      passed: text.split(/\n\s*\n/).filter((p) => p.trim().length > 0).length >= 3,
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
