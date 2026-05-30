/**
 * File path -> pipeline name mapping.
 * Used to load the prompt from pipeline definitions instead of guessing.
 */
export const FILE_TO_PIPELINE: Record<string, string> = {
  'style-guide.md': 'style-guide',
  'blueprint.md': 'blueprint',
  'outline.md': 'outline',
  'materials/worldbuilding.md': 'worldbuilding',
  'characters/main.md': 'character',
  '书名与创意.md': 'title',
}

/** Return the pipeline name for a project file path. */
export function getPipelineForFile(filePath: string): string | null {
  for (const [key, pipeline] of Object.entries(FILE_TO_PIPELINE)) {
    if (filePath.endsWith(key)) return pipeline
  }
  return null
}

/**
 * Guess the legacy prompt type for files that do not have a pipeline mapping.
 */
export function guessPromptType(filePath: string): string | null {
  if (/书名与创意\.md$/i.test(filePath)) return 'generate/title'
  if (/\/sec-\d+\.md$/.test(filePath)) return 'generate/chapter'
  // 有专用管线的文件不应走 generate/continuation，统一委托 getPipelineForFile()
  // 这样新增管线文件时无需同步修改此函数，消除维护漂移风险
  if (getPipelineForFile(filePath)) return null
  // 以下为系统管理文件，不应生成内容
  // story-state.md → 故事状态面板生成
  // recent-context.md → 上下文面板生成
  if (/story-state\.md$/i.test(filePath)) return null
  if (/recent-context\.md$/i.test(filePath)) return null
  if (/\.json$/.test(filePath) && filePath.includes('characters')) return 'extract/character'
  if (/\.md$/.test(filePath)) return 'generate/continuation'
  return null
}
