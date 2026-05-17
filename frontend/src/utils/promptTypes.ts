/**
 * 文件路径 → pipeline 名称映射
 * 用于从 pipeline 定义加载 prompt，替代静态的 guessPromptType
 */
export const FILE_TO_PIPELINE: Record<string, string> = {
  'style-guide.md': 'style-guide',
  'blueprint.md': 'blueprint',
  'outline.md': 'outline',
  'materials/worldbuilding.md': 'worldbuilding',
  'characters/main.md': 'character',
  '书名与创意.md': 'title',
}

/** 根据文件路径查对应的 pipeline 名称 */
export function getPipelineForFile(filePath: string): string | null {
  for (const [key, pipeline] of Object.entries(FILE_TO_PIPELINE)) {
    if (filePath.endsWith(key)) return pipeline
  }
  return null
}

/**
 * 根据文件路径推测对应的 Prompt 模板类型（兜底用）
 */
export function guessPromptType(filePath: string): string | null {
  if (/\/sec-\d+\.md$/.test(filePath)) return 'generate/chapter'
  if (/style-guide\.md$/i.test(filePath)) return 'generate/continuation'
  if (/story-state\.md$/i.test(filePath)) return 'generate/continuation'
  if (/recent-context\.md$/i.test(filePath)) return 'generate/continuation'
  if (/\.json$/.test(filePath) && filePath.includes('characters')) return 'extract/character'
  if (/\.md$/.test(filePath)) return 'generate/continuation'
  return null
}
