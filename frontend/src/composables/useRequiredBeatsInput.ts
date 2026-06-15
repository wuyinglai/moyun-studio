import { computed, ref } from 'vue'

export interface BeatInputItem {
  id: string
  text: string
}

const requiredBeatsText = ref('')
const forbiddenBeatsText = ref('')

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

export function useRequiredBeatsInput() {
  const requiredBeats = computed(() => parseBeatLines(requiredBeatsText.value, 'beat'))
  const forbiddenBeats = computed(() => parseBeatLines(forbiddenBeatsText.value, 'forbid'))
  const hasBeatInput = computed(() => requiredBeats.value.length > 0 || forbiddenBeats.value.length > 0)

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
    getBeatValidationExtraVars,
  }
}
