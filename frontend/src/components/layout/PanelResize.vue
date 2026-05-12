<template>
  <div class="panel-resize-handle" :class="direction" @mousedown="startDrag">
    <div class="handle-gutter"></div>
  </div>
</template>

<script setup lang="ts">
/**
 * PanelResize.vue - 可拖拽分隔线组件
 * 用于 AppLayout.vue 中替代 Split.js 的 gutter 自定义样式
 * Split.js 已通过其 gutter 元素渲染，本组件为备用/辅助方案
 */
const props = withDefaults(
  defineProps<{
    direction?: 'horizontal' | 'vertical'
    minSize?: number
    maxSize?: number
  }>(),
  {
    direction: 'horizontal',
    minSize: 100,
    maxSize: Infinity,
  }
)

const emit = defineEmits<{
  (e: 'resize', delta: number): void
  (e: 'resize-start'): void
  (e: 'resize-end'): void
}>()

let startPos = 0

function startDrag(e: MouseEvent) {
  e.preventDefault()
  startPos = props.direction === 'horizontal' ? e.clientX : e.clientY
  emit('resize-start')

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(e: MouseEvent) {
  const current = props.direction === 'horizontal' ? e.clientX : e.clientY
  const delta = current - startPos
  startPos = current
  emit('resize', delta)
}

function stopDrag() {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  emit('resize-end')
}
</script>

<style scoped>
.panel-resize-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  transition: background 0.2s;
  z-index: 10;
}

.panel-resize-handle:hover,
.panel-resize-handle:active {
  background: var(--accent-primary);
}

.horizontal {
  width: 6px;
  cursor: col-resize;
}

.vertical {
  height: 6px;
  cursor: row-resize;
}

.handle-gutter {
  border-radius: 3px;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.horizontal .handle-gutter {
  width: 2px;
  height: 32px;
  background: var(--text-muted);
}

.vertical .handle-gutter {
  width: 32px;
  height: 2px;
  background: var(--text-muted);
}

.panel-resize-handle:hover .handle-gutter {
  opacity: 1;
  background: white;
}
</style>
