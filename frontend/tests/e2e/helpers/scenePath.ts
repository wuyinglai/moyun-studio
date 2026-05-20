/**
 * 场景路径工具（E2E 测试用）
 *
 * 复用前端 scenePath 逻辑，在测试端独立实现，
 * 避免测试代码依赖前端源码。
 */

export interface SceneConfig {
  scenes_per_chapter: number
  chapters_per_volume: number
}

const DEFAULT_CONFIG: SceneConfig = {
  scenes_per_chapter: 5,
  chapters_per_volume: 12,
}

const SCENE_PATH_RE = /chapters\/vol-(\d+)\/ch-(\d+)\/sec-(\d+)\.md$/

export interface ScenePathInfo {
  volume: number
  chapter: number
  scene: number
}

/** 解析场景文件路径 */
export function parseScenePath(path: string): ScenePathInfo | null {
  const m = path.match(SCENE_PATH_RE)
  if (!m) return null
  return {
    volume: parseInt(m[1], 10),
    chapter: parseInt(m[2], 10),
    scene: parseInt(m[3], 10),
  }
}

/** 构建场景文件路径 */
export function buildScenePath(volume: number, chapter: number, scene: number): string {
  const vol = String(volume).padStart(2, '0')
  const ch = String(chapter).padStart(3, '0')
  const sec = String(scene).padStart(3, '0')
  return `chapters/vol-${vol}/ch-${ch}/sec-${sec}.md`
}

/** 获取下一个场景路径 */
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
