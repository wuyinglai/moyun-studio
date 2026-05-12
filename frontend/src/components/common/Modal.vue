<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="handleOverlayClick">
        <div class="modal-box" :class="`modal-${size}`" role="dialog" :aria-label="title">
          <div class="modal-header" v-if="title || $slots.header">
            <slot name="header">
              <h2 class="modal-title">{{ title }}</h2>
            </slot>
            <button v-if="showClose" class="modal-close" @click="$emit('close')">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <div class="modal-body">
            <slot></slot>
          </div>

          <div class="modal-footer" v-if="$slots.footer">
            <slot name="footer"></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    visible: boolean
    title?: string
    size?: 'sm' | 'md' | 'lg' | 'xl'
    showClose?: boolean
    closeOnOverlay?: boolean
  }>(),
  {
    size: 'md',
    showClose: true,
    closeOnOverlay: true,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
}>()

function handleOverlayClick() {
  if (props.closeOnOverlay) emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-box {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.modal-sm { width: 360px; }
.modal-md { width: 520px; }
.modal-lg { width: 720px; }
.modal-xl { width: 960px; }

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: rgba(255,255,255,0.08);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

/* 动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .modal-box {
  transition: transform 0.2s ease;
}
.modal-enter-from .modal-box {
  transform: scale(0.95) translateY(-10px);
}
</style>
