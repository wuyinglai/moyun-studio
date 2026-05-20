/** 场景模块 - 类型定义 */

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

export const DEFAULT_SCENE_CONFIG: SceneConfig = {
  scenes_per_chapter: 5,
  chapters_per_volume: 12,
}
