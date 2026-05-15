/**
 * 根据文件路径推测对应的 Prompt 模板类型
 */
export function guessPromptType(filePath: string): string | null {
  if (/\/sec-\d+\.md$/.test(filePath)) return 'generate/chapter'
  if (/outline\.md$/i.test(filePath)) return 'generate/outline'
  if (/style-guide\.md$/i.test(filePath)) return 'generate/continuation'
  if (/story-state\.md$/i.test(filePath)) return 'generate/continuation'
  if (/recent-context\.md$/i.test(filePath)) return 'generate/continuation'
  if (/\.json$/.test(filePath) && filePath.includes('characters')) return 'extract/character'
  if (/worldbuilding\.md$/i.test(filePath)) return 'generate/worldbuilding'
  if (/\.md$/.test(filePath)) return 'generate/continuation'
  return null
}
