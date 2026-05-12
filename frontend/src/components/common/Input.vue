<template>
  <div class="moyun-input" :class="{ 'has-error': error, 'is-disabled': disabled }">
    <label v-if="label" class="input-label" :for="inputId">{{ label }}</label>
    <div class="input-wrapper">
      <i v-if="prefix" :class="prefix"></i>
      <input
        :id="inputId"
        v-bind="$attrs"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :type="type"
        class="input-field"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <i v-if="suffix" :class="suffix"></i>
    </div>
    <span v-if="error" class="input-error">{{ error }}</span>
    <span v-else-if="hint" class="input-hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    modelValue?: string
    label?: string
    placeholder?: string
    type?: string
    disabled?: boolean
    error?: string
    hint?: string
    prefix?: string
    suffix?: string
    id?: string
  }>(),
  {
    modelValue: '',
    type: 'text',
    disabled: false,
  }
)

defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const inputId = computed(() => props.id || `input-${Math.random().toString(36).slice(2, 9)}`)
</script>

<style scoped>
.moyun-input { display: flex; flex-direction: column; gap: 4px; }

.input-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 10px;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: var(--accent-primary);
}

.has-error .input-wrapper {
  border-color: var(--accent-danger);
}

.is-disabled .input-wrapper {
  opacity: 0.5;
}

.input-wrapper i {
  color: var(--text-muted);
  font-size: 13px;
}

.input-field {
  flex: 1;
  background: none;
  border: none;
  padding: 8px 6px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
}

.input-field::placeholder { color: var(--text-muted); }

.input-error { font-size: 12px; color: var(--accent-danger); }
.input-hint { font-size: 12px; color: var(--text-muted); }
</style>
