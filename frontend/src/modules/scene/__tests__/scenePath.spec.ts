/**
 * 场景路径契约测试 — 前端
 *
 * 验证 scenePath.ts 的路径解析、构建、进位逻辑与契约文档一致。
 * 契约文档：docs/contracts/scene-path-contract.md
 *
 * 注意：此测试需要 vitest 运行。如未安装 vitest，可通过 E2E 间接覆盖。
 * 安装：npm install -D vitest && npx vitest run src/modules/scene/__tests__/scenePath.spec.ts
 */

import { describe, it, expect } from 'vitest'
import {
  parseScenePath,
  buildScenePath,
  isSceneFile,
  getNextScenePath,
  parseVolumeDir,
  parseChapterDir,
  parseSceneFileName,
  buildChapterPlanPath,
} from '../scenePath'

describe('parseScenePath', () => {
  it('标准路径解析', () => {
    const info = parseScenePath('chapters/vol-01/ch-001/sec-003.md')
    expect(info).not.toBeNull()
    expect(info!.volume).toBe(1)
    expect(info!.chapter).toBe(1)
    expect(info!.scene).toBe(3)
  })

  it('高编号路径', () => {
    const info = parseScenePath('chapters/vol-12/ch-123/sec-999.md')
    expect(info).not.toBeNull()
    expect(info!.volume).toBe(12)
    expect(info!.chapter).toBe(123)
    expect(info!.scene).toBe(999)
  })

  it('包含项目前缀的完整路径', () => {
    const info = parseScenePath('my-project/chapters/vol-01/ch-002/sec-005.md')
    expect(info).not.toBeNull()
    expect(info!.volume).toBe(1)
    expect(info!.chapter).toBe(2)
    expect(info!.scene).toBe(5)
  })

  it('非场景路径返回 null', () => {
    expect(parseScenePath('foo/bar.md')).toBeNull()
  })

  it('缺少层级返回 null', () => {
    expect(parseScenePath('chapters/vol-01/sec-001.md')).toBeNull()
  })

  it('ch-plan.md 不是场景文件', () => {
    expect(parseScenePath('chapters/vol-01/ch-001/ch-plan.md')).toBeNull()
  })

  it('路径中间有额外层级返回 null', () => {
    expect(parseScenePath('chapters/vol-01/extra/ch-001/sec-001.md')).toBeNull()
  })

  it('空字符串返回 null', () => {
    expect(parseScenePath('')).toBeNull()
  })
})

describe('buildScenePath', () => {
  it('标准路径构建', () => {
    expect(buildScenePath(1, 1, 3)).toBe('chapters/vol-01/ch-001/sec-003.md')
  })

  it('零填充', () => {
    expect(buildScenePath(1, 1, 1)).toBe('chapters/vol-01/ch-001/sec-001.md')
    expect(buildScenePath(9, 99, 999)).toBe('chapters/vol-09/ch-099/sec-999.md')
  })

  it('高编号路径构建', () => {
    expect(buildScenePath(12, 123, 999)).toBe('chapters/vol-12/ch-123/sec-999.md')
  })
})

describe('isSceneFile', () => {
  it('场景文件返回 true', () => {
    expect(isSceneFile('chapters/vol-01/ch-001/sec-001.md')).toBe(true)
  })

  it('ch-plan.md 返回 false', () => {
    expect(isSceneFile('chapters/vol-01/ch-001/ch-plan.md')).toBe(false)
  })

  it('随机文件返回 false', () => {
    expect(isSceneFile('story-state.md')).toBe(false)
  })
})

describe('getNextScenePath — 核心进位规则', () => {
  // ── 场景进位 ──────────────────────────────────────────

  it('sec-001 → sec-002', () => {
    expect(getNextScenePath('chapters/vol-01/ch-001/sec-001.md'))
      .toBe('chapters/vol-01/ch-001/sec-002.md')
  })

  it('sec-003 → sec-004', () => {
    expect(getNextScenePath('chapters/vol-01/ch-001/sec-003.md'))
      .toBe('chapters/vol-01/ch-001/sec-004.md')
  })

  // ── 章进位 ──────────────────────────────────────────

  it('sec-005 → 下一章 sec-001', () => {
    expect(getNextScenePath('chapters/vol-01/ch-001/sec-005.md'))
      .toBe('chapters/vol-01/ch-002/sec-001.md')
  })

  it('ch-011/sec-005 → ch-012/sec-001', () => {
    expect(getNextScenePath('chapters/vol-01/ch-011/sec-005.md'))
      .toBe('chapters/vol-01/ch-012/sec-001.md')
  })

  // ── 卷进位 ──────────────────────────────────────────

  it('ch-012/sec-005 → vol-02/ch-001/sec-001', () => {
    expect(getNextScenePath('chapters/vol-01/ch-012/sec-005.md'))
      .toBe('chapters/vol-02/ch-001/sec-001.md')
  })

  it('vol-02 最后一场景进位到 vol-03', () => {
    expect(getNextScenePath('chapters/vol-02/ch-012/sec-005.md'))
      .toBe('chapters/vol-03/ch-001/sec-001.md')
  })

  // ── 自定义配置 ──────────────────────────────────────

  it('自定义 scenes_per_chapter=3', () => {
    expect(getNextScenePath('chapters/vol-01/ch-001/sec-003.md', { scenes_per_chapter: 3, chapters_per_volume: 12 }))
      .toBe('chapters/vol-01/ch-002/sec-001.md')
  })

  it('自定义 chapters_per_volume=6', () => {
    expect(getNextScenePath('chapters/vol-01/ch-006/sec-005.md', { scenes_per_chapter: 5, chapters_per_volume: 6 }))
      .toBe('chapters/vol-02/ch-001/sec-001.md')
  })

  // ── 非法路径 ────────────────────────────────────────

  it('非法路径返回 null', () => {
    expect(getNextScenePath('foo/bar.md')).toBeNull()
  })

  it('空字符串返回 null', () => {
    expect(getNextScenePath('')).toBeNull()
  })
})

describe('build ↔ parse 往返测试', () => {
  const cases = [
    [1, 1, 1],
    [1, 1, 5],
    [1, 12, 5],
    [3, 7, 2],
    [99, 999, 999],
  ] as const

  it.each(cases)('build(%i, %i, %i) → parse → 原始值', (vol, ch, sec) => {
    const path = buildScenePath(vol, ch, sec)
    const info = parseScenePath(path)
    expect(info).not.toBeNull()
    expect(info!.volume).toBe(vol)
    expect(info!.chapter).toBe(ch)
    expect(info!.scene).toBe(sec)
  })
})

describe('辅助解析函数', () => {
  it('parseVolumeDir', () => {
    expect(parseVolumeDir('vol-01')).toBe(1)
    expect(parseVolumeDir('vol-12')).toBe(12)
    expect(parseVolumeDir('invalid')).toBeNull()
  })

  it('parseChapterDir', () => {
    expect(parseChapterDir('ch-001')).toBe(1)
    expect(parseChapterDir('ch-012')).toBe(12)
    expect(parseChapterDir('invalid')).toBeNull()
  })

  it('parseSceneFileName', () => {
    expect(parseSceneFileName('sec-001.md')).toBe(1)
    expect(parseSceneFileName('sec-005.md')).toBe(5)
    expect(parseSceneFileName('invalid')).toBeNull()
  })
})

describe('buildChapterPlanPath', () => {
  it('标准路径', () => {
    expect(buildChapterPlanPath(1, 1)).toBe('chapters/vol-01/ch-001/ch-plan.md')
  })
})
