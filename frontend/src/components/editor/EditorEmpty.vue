<template>
  <div class="editor-empty">
    <i class="fa-solid fa-feather"></i>
    <h3>{{ title }}</h3>
    <p>{{ subtitle }}</p>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
  }>(),
  {
    title: '暂无打开的文件',
    subtitle: '从左侧文件树选择一个文件开始编辑',
  }
)
</script>

<style scoped>
.editor-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);
  user-select: none;
}

.editor-empty i {
  font-size: 56px;
  opacity: 0.25;
  color: var(--accent-primary);
}

.editor-empty h3 {
  font-size: 18px;
  font-weight: 500;
  color: var(--text-secondary);
  margin: 0;
}

.editor-empty p {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}
</style>
