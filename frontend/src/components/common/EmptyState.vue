<template>
  <div class="empty-state">
    <div class="empty-icon">
      <i :class="icon"></i>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description" v-if="description">{{ description }}</p>
    <div class="empty-action" v-if="$slots.action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    icon?: string
    title?: string
    description?: string
  }>(),
  {
    icon: 'fa-solid fa-inbox',
    title: '暂无内容',
    description: '',
  }
)
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 12px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--accent-primary);
  opacity: 0.4;
  border-radius: 50%;
  background: var(--bg-card);
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.empty-description {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  max-width: 280px;
}

.empty-action {
  margin-top: 8px;
}
</style>
