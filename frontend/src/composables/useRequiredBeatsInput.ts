import { computed, ref } from 'vue'

export interface BeatInputItem {
  id: string
  text: string
}

const requiredBeatsText = ref('')
const forbiddenBeatsText = ref('')
const MAX_BEAT_LINE_LENGTH = 80

function parseBeatLines(text: string, prefix: string): BeatInputItem[] {
  return text
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .map((line, index) => ({
      id: `${prefix}-${index + 1}`,
      text: line,
    }))
}

function findLongBeatLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(line => line.length > MAX_BEAT_LINE_LENGTH)
}

export function useRequiredBeatsInput() {
  const requiredBeats = computed(() => parseBeatLines(requiredBeatsText.value, 'beat'))
  const forbiddenBeats = computed(() => parseBeatLines(forbiddenBeatsText.value, 'forbid'))
  const hasBeatInput = computed(() => requiredBeats.value.length > 0 || forbiddenBeats.value.length > 0)
  const beatInputSummary = computed(() => {
    if (!hasBeatInput.value) return '未设置检查项，生成将保持默认流程。'
    return `已设置 ${requiredBeats.value.length} 个必须信息点，${forbiddenBeats.value.length} 个禁止项。`
  })
  const longBeatLineWarnings = computed(() => [
    ...findLongBeatLines(requiredBeatsText.value),
    ...findLongBeatLines(forbiddenBeatsText.value),
  ])
  const hasLongBeatLine = computed(() => longBeatLineWarnings.value.length > 0)

  function getBeatValidationExtraVars(): Record<string, unknown> {
    if (!hasBeatInput.value) return {}

    const extraVars: Record<string, unknown> = {
      _enable_beat_validation: true,
    }
    if (requiredBeats.value.length > 0) {
      extraVars.required_beats = requiredBeats.value
    }
    if (forbiddenBeats.value.length > 0) {
      extraVars.forbidden_beats = forbiddenBeats.value
    }
    return extraVars
  }

  return {
    requiredBeatsText,
    forbiddenBeatsText,
    requiredBeats,
    forbiddenBeats,
    hasBeatInput,
    beatInputSummary,
    longBeatLineWarnings,
    hasLongBeatLine,
    getBeatValidationExtraVars,
  }
}
