<template>
  <button
    class="moyun-btn"
    :class="[`btn-${type}`, `btn-${size}`, { 'btn-loading': loading, 'btn-block': block }]"
    :disabled="disabled || loading"
    v-bind="$attrs"
  >
    <i v-if="loading" class="fa-solid fa-spinner fa-spin"></i>
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: 'primary' | 'secondary' | 'danger' | 'ghost'
    size?: 'sm' | 'md' | 'lg'
    disabled?: boolean
    loading?: boolean
    block?: boolean
  }>(),
  {
    type: 'primary',
    size: 'md',
    disabled: false,
    loading: false,
    block: false,
  }
)
</script>

<style scoped>
.moyun-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: var(--radius-md);
  font-family: inherit;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-md { padding: 6px 16px; font-size: 14px; }
.btn-lg { padding: 8px 20px; font-size: 15px; }

.btn-block { width: 100%; }

.btn-primary {
  background: var(--accent-primary);
  color: white;
}
.btn-primary:hover:not(:disabled) { background: #2563eb; }

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border-color);
}
.btn-secondary:hover:not(:disabled) { background: rgba(255,255,255,0.08); }

.btn-danger {
  background: var(--accent-danger);
  color: white;
}
.btn-danger:hover:not(:disabled) { opacity: 0.85; }

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}
.btn-ghost:hover:not(:disabled) {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
}

.moyun-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-loading { pointer-events: none; }
</style>
