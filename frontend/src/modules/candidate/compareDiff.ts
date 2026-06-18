/**
 * T10.2 Candidate Compare MVP — line-level diff utilities.
 *
 * Pure functions, no dependencies on backend or LLM.
 * Uses a simplified LCS-based diff for stable, crash-free MVP output.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DiffLineKind = 'same' | 'added' | 'removed' | 'changed'

export interface CompareDiffLine {
  left?: string
  right?: string
  kind: DiffLineKind
}

export interface CompareSummary {
  leftChars: number
  rightChars: number
  deltaChars: number
  addedLines: number
  removedLines: number
  changedLines: number
  identical: boolean
}

// ---------------------------------------------------------------------------
// LCS-based line diff
// ---------------------------------------------------------------------------

/**
 * Compute the Longest Common Subsequence table for two string arrays.
 * Uses Myers-style DP with O(m*n) time and space.
 * Capped at 2000 lines per side to avoid performance issues.
 */
function lcsTable(left: string[], right: string[]): number[][] {
  const m = Math.min(left.length, 2000)
  const n = Math.min(right.length, 2000)
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (left[i - 1] === right[j - 1]) {
        dp[i]![j] = dp[i - 1]![j - 1]! + 1
      } else {
        dp[i]![j] = Math.max(dp[i - 1]![j]!, dp[i]![j - 1]!)
      }
    }
  }
  return dp
}

/**
 * Compute line-level diff between two texts.
 * Returns an array of CompareDiffLine entries.
 */
export function computeLineDiff(leftText: string, rightText: string): CompareDiffLine[] {
  const leftLines = leftText.split('\n')
  const rightLines = rightText.split('\n')

  // Fast path: identical
  if (leftText === rightText) {
    return leftLines.map((line) => ({ left: line, right: line, kind: 'same' as const }))
  }

  // Fast path: either side empty
  if (leftLines.length === 0) {
    return rightLines.map((line) => ({ right: line, kind: 'added' as const }))
  }
  if (rightLines.length === 0) {
    return leftLines.map((line) => ({ left: line, kind: 'removed' as const }))
  }

  const dp = lcsTable(leftLines, rightLines)
  const result: CompareDiffLine[] = []

  let i = Math.min(leftLines.length, 2000)
  let j = Math.min(rightLines.length, 2000)

  // Backtrack through LCS table
  const stack: CompareDiffLine[] = []
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && leftLines[i - 1] === rightLines[j - 1]) {
      stack.push({ left: leftLines[i - 1], right: rightLines[j - 1], kind: 'same' })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i]![j - 1]! >= dp[i - 1]![j]!)) {
      stack.push({ right: rightLines[j - 1], kind: 'added' })
      j--
    } else {
      stack.push({ left: leftLines[i - 1], kind: 'removed' })
      i--
    }
  }

  // Reverse to get forward order
  while (stack.length > 0) {
    result.push(stack.pop()!)
  }

  // Post-process: pair adjacent removed+added as 'changed'
  return pairChanges(result)
}

/**
 * Pair adjacent removed + added lines as 'changed' for cleaner display.
 */
function pairChanges(lines: CompareDiffLine[]): CompareDiffLine[] {
  const out: CompareDiffLine[] = []
  let idx = 0
  while (idx < lines.length) {
    const line = lines[idx]!
    if (line.kind === 'removed') {
      // Collect consecutive removed lines
      const removed: CompareDiffLine[] = [line]
      let next = idx + 1
      while (next < lines.length && lines[next]!.kind === 'removed') {
        removed.push(lines[next]!)
        next++
      }
      // Collect consecutive added lines immediately after
      const added: CompareDiffLine[] = []
      while (next < lines.length && lines[next]!.kind === 'added') {
        added.push(lines[next]!)
        next++
      }
      // Pair them as 'changed'
      const pairCount = Math.min(removed.length, added.length)
      for (let p = 0; p < pairCount; p++) {
        out.push({ left: removed[p]!.left, right: added[p]!.right, kind: 'changed' })
      }
      // Unpaired removed
      for (let p = pairCount; p < removed.length; p++) {
        out.push(removed[p]!)
      }
      // Unpaired added
      for (let p = pairCount; p < added.length; p++) {
        out.push(added[p]!)
      }
      idx = next
    } else {
      out.push(line)
      idx++
    }
  }
  return out
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

/**
 * Compute a human-readable summary of the diff.
 */
export function computeSummary(leftText: string, rightText: string, diff: CompareDiffLine[]): CompareSummary {
  const leftChars = leftText.length
  const rightChars = rightText.length
  let addedLines = 0
  let removedLines = 0
  let changedLines = 0

  for (const line of diff) {
    if (line.kind === 'added') addedLines++
    else if (line.kind === 'removed') removedLines++
    else if (line.kind === 'changed') changedLines++
  }

  return {
    leftChars,
    rightChars,
    deltaChars: rightChars - leftChars,
    addedLines,
    removedLines,
    changedLines,
    identical: leftText === rightText,
  }
}

// ---------------------------------------------------------------------------
// Label helpers
// ---------------------------------------------------------------------------

/** Right-side label based on candidate action. */
export function candidateActionLabel(action: string): string {
  const labels: Record<string, string> = {
    polish: '润色候选稿',
    rewrite: '重写候选稿',
    continue: '续写候选稿',
    repair: '修复版候选稿',
    feedback_revision: '反馈修订候选稿',
    expand: '扩写候选稿',
    shrink: '缩写候选稿',
    modify: '修改候选稿',
    chat: '聊天改稿候选稿',
  }
  return labels[action] || '当前候选稿'
}
