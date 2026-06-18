/**
 * T10.1 Quality Explanation UI — dimension definitions and copy text.
 *
 * Transforms raw CandidateQualityMetadata into user-friendly explanations
 * following the T10.1a design spec.
 */

import type { CandidateInfo, CandidateQualityMetadata } from '@/shared/api/types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type QualityDimensionKey =
  | 'instruction_following'
  | 'continuity'
  | 'style_preservation'
  | 'change_scope'
  | 'forbidden_check'

export type QualityStatus = 'pass' | 'warning' | 'unknown'
export type ChangeScopeValue = 'small' | 'medium' | 'large' | 'unknown'

export interface DimensionExplanation {
  key: QualityDimensionKey
  label: string
  statusLabel: string
  description: string
  status: QualityStatus | ChangeScopeValue
  cssClass: string
}

export interface QualityExplanationSummary {
  passCount: number
  warningCount: number
  unknownCount: number
  dimensions: DimensionExplanation[]
  collapsedText: string
}

// ---------------------------------------------------------------------------
// Status label mappings (T10.1a §7)
// ---------------------------------------------------------------------------

function statusLabel(value: string): string {
  if (value === 'pass') return '通过'
  if (value === 'warning') return '需注意'
  return '未检测'
}

function statusCssClass(value: string): string {
  if (value === 'pass') return 'expl-pass'
  if (value === 'warning') return 'expl-warning'
  return 'expl-unknown'
}

function scopeLabel(value: string): string {
  if (value === 'small') return '变化较小'
  if (value === 'medium') return '变化适中'
  if (value === 'large') return '变化较大'
  return '无法判断'
}

function scopeCssClass(value: string): string {
  if (value === 'small') return 'expl-pass'
  if (value === 'medium') return 'expl-warning'
  if (value === 'large') return 'expl-danger'
  return 'expl-unknown'
}

// ---------------------------------------------------------------------------
// Per-dimension description builders (T10.1a §8)
// ---------------------------------------------------------------------------

function instructionDescription(q: CandidateQualityMetadata, c: CandidateInfo): string {
  if (q.instruction_following === 'pass') {
    return '候选稿满足当前 required / forbidden beats 检查。'
  }
  if (q.instruction_following === 'warning') {
    // Try to surface beat validation summary
    const bv = c.beat_validation
    if (bv?.summary) return bv.summary
    return '有 required / forbidden beats 相关提示，建议预览确认。'
  }
  return '没有可用的 beats 检查结果。'
}

function continuityDescription(q: CandidateQualityMetadata, c: CandidateInfo): string {
  const usedCount = Number(c.continuity_anchors?.used_count || 0)
  if (q.continuity === 'pass' && usedCount > 0) {
    return `本次生成参考了 ${usedCount} 条连续性锚点。`
  }
  if (q.continuity === 'pass') {
    return '连续性检查未发现明显问题。'
  }
  if (q.continuity === 'warning') {
    return '连续性存在提示，建议人工确认人物状态、线索等是否一致。'
  }
  if (usedCount > 0) {
    return `本次生成参考了 ${usedCount} 条连续性锚点，但未做完整连续性判断。`
  }
  return '当前项目未设置连续性锚点，或当前模式不适用。'
}

function styleDescription(q: CandidateQualityMetadata, c: CandidateInfo): string {
  if (q.style_preservation === 'pass') {
    return '润色模式默认更重视保留原意和原句风格。'
  }
  const action = c.action
  if (action === 'rewrite' || action === 'continue' || action === 'feedback_revision') {
    return '重写、续写和修复模式不强行判断文风保持。'
  }
  return '当前模式没有可用的文风保持判断。'
}

function changeScopeDescription(q: CandidateQualityMetadata): string {
  if (q.change_scope === 'small') return '候选稿相对原文变化较小。'
  if (q.change_scope === 'medium') return '候选稿相对原文变化适中。'
  if (q.change_scope === 'large') return '改动较大不一定是坏事，但建议 adopt 前先预览。'
  return '无法判断改动幅度。'
}

function forbiddenDescription(q: CandidateQualityMetadata): string {
  if (q.forbidden_check === 'pass') {
    return '未发现违反 forbidden beats 的内容。'
  }
  if (q.forbidden_check === 'warning') {
    return '可能触及 forbidden beats，建议预览确认。'
  }
  return '未设置 forbidden beats 或未检测。'
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build a full quality explanation summary from candidate data.
 * Old candidates without quality metadata get a minimal placeholder.
 */
export function buildQualityExplanation(candidate: CandidateInfo): QualityExplanationSummary {
  const q = candidate.quality
  if (!q) {
    return {
      passCount: 0,
      warningCount: 0,
      unknownCount: 0,
      dimensions: [],
      collapsedText: '质量提示：暂无质量解释',
    }
  }

  const dimensions: DimensionExplanation[] = [
    {
      key: 'instruction_following',
      label: '指令遵守',
      statusLabel: statusLabel(q.instruction_following),
      description: instructionDescription(q, candidate),
      status: q.instruction_following,
      cssClass: statusCssClass(q.instruction_following),
    },
    {
      key: 'continuity',
      label: '连续性',
      statusLabel: statusLabel(q.continuity),
      description: continuityDescription(q, candidate),
      status: q.continuity,
      cssClass: statusCssClass(q.continuity),
    },
    {
      key: 'style_preservation',
      label: '文风保持',
      statusLabel: statusLabel(q.style_preservation),
      description: styleDescription(q, candidate),
      status: q.style_preservation,
      cssClass: statusCssClass(q.style_preservation),
    },
    {
      key: 'change_scope',
      label: '改动幅度',
      statusLabel: scopeLabel(q.change_scope),
      description: changeScopeDescription(q),
      status: q.change_scope,
      cssClass: scopeCssClass(q.change_scope),
    },
    {
      key: 'forbidden_check',
      label: '禁区检查',
      statusLabel: statusLabel(q.forbidden_check),
      description: forbiddenDescription(q),
      status: q.forbidden_check,
      cssClass: statusCssClass(q.forbidden_check),
    },
  ]

  let passCount = 0
  let warningCount = 0
  let unknownCount = 0

  for (const d of dimensions) {
    if (d.key === 'change_scope') {
      // change_scope uses different value semantics
      if (d.status === 'small') passCount++
      else if (d.status === 'large') warningCount++
      else unknownCount++
    } else {
      if (d.status === 'pass') passCount++
      else if (d.status === 'warning') warningCount++
      else unknownCount++
    }
  }

  const parts: string[] = []
  if (passCount > 0) parts.push(`${passCount} 项通过`)
  if (warningCount > 0) parts.push(`${warningCount} 项需注意`)
  if (unknownCount > 0) parts.push(`${unknownCount} 项未检测`)

  const collapsedText = parts.length > 0
    ? `质量提示：${parts.join('，')}`
    : '质量提示：暂无质量数据'

  return { passCount, warningCount, unknownCount, dimensions, collapsedText }
}

/**
 * Whether the repair explanation should be shown inside the expanded quality area.
 * Only true when the repair button itself is visible — i.e. candidate is pending
 * AND has a repairable warning (instruction_following=warning, forbidden_check=warning,
 * or change_scope=large). Mirrors hasRepairableWarning() in CandidatePanel.vue.
 */
export function shouldShowRepairExplanation(candidate: CandidateInfo): boolean {
  if (candidate.status !== 'pending') return false
  const q = candidate.quality
  if (!q) return false
  return (
    q.instruction_following === 'warning' ||
    q.forbidden_check === 'warning' ||
    q.change_scope === 'large'
  )
}

/**
 * Return a description for why the repair button appears.
 */
export function repairExplanation(candidate: CandidateInfo): string {
  const q = candidate.quality
  if (!q) return '系统发现候选稿存在可修复提示，你可以生成一个新的修复版候选稿。'

  const reasons: string[] = []
  if (q.instruction_following === 'warning') reasons.push('信息点检查')
  if (q.forbidden_check === 'warning') reasons.push('禁区检查')
  if (q.change_scope === 'large') reasons.push('改动幅度较大')

  if (reasons.length > 0) {
    return `系统发现候选稿在${reasons.join('、')}方面存在提示，你可以生成一个新的修复版候选稿。`
  }
  return '系统发现候选稿存在可修复提示，你可以生成一个新的修复版候选稿。'
}

/** Candidate-only safety boundary text (T10.1a §10). */
export const CANDIDATE_SAFETY_TEXT =
  '所有质量提示仅供参考。AI 不会自动修改正文，只有你点击采纳后，正文才会更新。'
