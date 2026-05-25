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
  if (/style-guide\.md$/i.test(filePath)) return 'generate/continuation'
  if (/story-state\.md$/i.test(filePath)) return 'generate/continuation'
  if (/recent-context\.md$/i.test(filePath)) return 'generate/continuation'
  if (/\.json$/.test(filePath) && filePath.includes('characters')) return 'extract/character'
  if (/\.md$/.test(filePath)) return 'generate/continuation'
  return null
}
