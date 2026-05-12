<template>
  <div class="save-status" :class="statusClass">
    <i :class="iconClass"></i>
    <span>{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: 'saved' | 'saving' | 'unsaved' | 'error'
}>()

const statusClass = computed(() => `status-${props.status}`)

const iconClass = computed(() => {
  switch (props.status) {
    case 'saved': return 'fa-solid fa-check'
    case 'saving': return 'fa-solid fa-spinner fa-spin'
    case 'unsaved': return 'fa-solid fa-circle'
    case 'error': return 'fa-solid fa-exclamation-circle'
  }
})

const label = computed(() => {
  switch (props.status) {
    case 'saved': return '已保存'
    case 'saving': return '保存中...'
    case 'unsaved': return '未保存'
    case 'error': return '保存失败'
  }
})
</script>

<style scoped>
.save-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.status-saved {
  color: var(--accent-success);
}

.status-saving {
  color: var(--text-muted);
}

.status-unsaved {
  color: var(--accent-warning);
}

.status-unsaved i {
  font-size: 8px;
}

.status-error {
  color: var(--accent-danger);
}
</style>
