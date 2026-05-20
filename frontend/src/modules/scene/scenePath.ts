/** 场景路径工具 — 统一管理 chapters/vol-NN/ch-NNN/sec-NNN.md 的解析与构建 */

export interface ScenePathInfo {
  volume: number
  chapter: number
  scene: number
  volumeDir: string
  chapterDir: string
  sceneFile: string
}

export interface SceneConfig {
  scenes_per_chapter: number
  chapters_per_volume: number
}

const DEFAULT_CONFIG: SceneConfig = {
  scenes_per_chapter: 5,
  chapters_per_volume: 12,
}

const SCENE_PATH_RE = /chapters\/vol-(\d+)\/ch-(\d+)\/sec-(\d+)\.md$/

/**
 * 解析场景文件路径
 * @example parseScenePath('chapters/vol-01/ch-001/sec-003.md')
 * // → { volume: 1, chapter: 1, scene: 3, volumeDir: 'vol-01', chapterDir: 'ch-001', sceneFile: 'sec-003.md' }
 */
export function parseScenePath(path: string): ScenePathInfo | null {
  const m = path.match(SCENE_PATH_RE)
  if (!m) return null
  const [, vol, ch, sec] = m
  return {
    volume: parseInt(vol, 10),
    chapter: parseInt(ch, 10),
    scene: parseInt(sec, 10),
    volumeDir: `vol-${vol}`,
    chapterDir: `ch-${ch}`,
    sceneFile: `sec-${sec}.md`,
  }
}

/**
 * 构建场景文件路径
 * @example buildScenePath(1, 1, 3) → 'chapters/vol-01/ch-001/sec-003.md'
 */
export function buildScenePath(volume: number, chapter: number, scene: number): string {
  const vol = String(volume).padStart(2, '0')
  const ch = String(chapter).padStart(3, '0')
  const sec = String(scene).padStart(3, '0')
  return `chapters/vol-${vol}/ch-${ch}/sec-${sec}.md`
}

/**
 * 判断路径是否为场景文件
 * @example isSceneFile('chapters/vol-01/ch-001/sec-003.md') → true
 */
export function isSceneFile(path: string): boolean {
  return SCENE_PATH_RE.test(path)
}

/**
 * 获取下一个场景路径，支持跨章/跨卷进位
 * @example getNextScenePath('chapters/vol-01/ch-001/sec-003.md')
 * // → 'chapters/vol-01/ch-001/sec-004.md'
 */
export function getNextScenePath(
  currentPath: string,
  config: SceneConfig = DEFAULT_CONFIG,
): string | null {
  const info = parseScenePath(currentPath)
  if (!info) return null

  if (info.scene < config.scenes_per_chapter) {
    return buildScenePath(info.volume, info.chapter, info.scene + 1)
  }
  if (info.chapter < config.chapters_per_volume) {
    return buildScenePath(info.volume, info.chapter + 1, 1)
  }
  return buildScenePath(info.volume + 1, 1, 1)
}

// ── 目录/文件名单项解析（供文件树等场景使用） ──────────

/** 解析卷目录名 → 卷号 */
export function parseVolumeDir(name: string): number | null {
  const m = name.match(/^vol-0*(\d+)$/)
  return m ? parseInt(m[1], 10) : null
}

/** 解析章目录名 → 章号 */
export function parseChapterDir(name: string): number | null {
  const m = name.match(/^ch-0*(\d+)$/)
  return m ? parseInt(m[1], 10) : null
}

/** 解析场景文件名 → 场景号 */
export function parseSceneFileName(name: string): number | null {
  const m = name.match(/^sec-0*(\d+)\.md$/)
  return m ? parseInt(m[1], 10) : null
}

/** 构建章规划路径 */
export function buildChapterPlanPath(volume: number, chapter: number): string {
  const vol = String(volume).padStart(2, '0')
  const ch = String(chapter).padStart(3, '0')
  return `chapters/vol-${vol}/ch-${ch}/ch-plan.md`
}
