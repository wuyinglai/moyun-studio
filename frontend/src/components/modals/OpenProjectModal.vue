<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal modal--wide">
          <!-- 头部 -->
          <div class="modal-header">
            <h3 class="modal-title">
              <i class="fa-solid fa-folder-open"></i>
              打开项目
            </h3>
            <button class="modal-close" @click="close">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>

          <!-- 项目列表 -->
          <div class="modal-body">
            <div v-if="isLoading" class="loading-state">
              <i class="fa-solid fa-spinner fa-spin"></i>
              <span>加载中...</span>
            </div>

            <div v-else-if="projects.length === 0" class="empty-state">
              <i class="fa-solid fa-folder-open"></i>
              <h4>暂无项目</h4>
              <p>点击下方按钮创建第一个项目</p>
            </div>

            <div v-else class="project-grid">
              <div
                v-for="project in projects"
                :key="project.id"
                class="project-card"
                :class="{ active: selectedId === project.id }"
                @click="selectedId = project.id"
                @dblclick="openProject"
              >
                <div class="project-icon">
                  <i class="fa-solid fa-book"></i>
                </div>
                <div class="project-info">
                  <h4 class="project-name">{{ project.name }}</h4>
                  <div class="project-meta">
                    <span v-if="project.genre" class="meta-tag">{{ project.genre }}</span>
                    <span class="meta-stat">{{ project.total_words?.toLocaleString() || 0 }} 字</span>
                  </div>
                  <p class="project-author" v-if="project.author">
                    <i class="fa-solid fa-user"></i> {{ project.author }}
                  </p>
                </div>
                <div class="project-actions">
                  <button
                    class="btn-delete"
                    @click.stop="deleteProject(project)"
                    title="删除项目"
                  >
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部 -->
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="close">取消</button>
            <button class="btn btn-primary" @click="openProject" :disabled="!selectedId">
              <i class="fa-solid fa-folder-open"></i>
              打开
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useProjectStore, Project } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notification'

const projectStore = useProjectStore()
const fileStore = useFileStore()
const uiStore = useUIStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.openProject)
const isLoading = computed(() => projectStore.isLoading)
const projects = computed(() => projectStore.projects)
const selectedId = ref<string | null>(null)

// 加载项目列表
watch(visible, async (val) => {
  if (val) {
    await projectStore.loadProjects()
    selectedId.value = null
  }
})

async function openProject() {
  if (!selectedId.value) return

  try {
    const project = await projectStore.openProject(selectedId.value)
    await fileStore.loadTree(project.id)
    notification.success(`已打开项目：${project.name}`)
    close()
  } catch (e) {
    notification.error('打开项目失败')
  }
}

async function deleteProject(project: Project) {
  const confirmed = window.confirm(`确定要删除项目 "${project.name}" 吗？此操作不可恢复。`)
  if (!confirmed) return

  try {
    await projectStore.deleteProject(project.id)
    notification.success(`项目 "${project.name}" 已删除`)

    // 如果删除的是当前选中的项目
    if (selectedId.value === project.id) {
      selectedId.value = null
    }
  } catch (e) {
    notification.error('删除失败')
  }
}

function close() {
  uiStore.closeOpenProject()
  selectedId.value = null
}
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--bg-secondary);
  border-radius: var(--radius-xl);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);

  &--wide {
    max-width: 700px;
  }
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;

  i {
    color: var(--accent-primary);
  }
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all 0.2s;

  &:hover {
    background: var(--bg-card);
    color: var(--text-primary);
  }
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  max-height: 60vh;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-muted);

  i {
    font-size: 48px;
    opacity: 0.5;
  }

  h4 {
    font-size: 16px;
    color: var(--text-secondary);
  }

  p {
    font-size: 14px;
  }
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.project-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-primary);
    border-color: var(--border-color);
  }

  &.active {
    border-color: var(--accent-primary);
    background: rgba(59, 130, 246, 0.1);
  }
}

.project-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: 18px;
  flex-shrink: 0;
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.meta-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: 10px;
  color: var(--accent-primary);
}

.meta-stat {
  font-size: 12px;
  color: var(--text-muted);
}

.project-author {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;

  i {
    font-size: 10px;
  }
}

.project-actions {
  flex-shrink: 0;
}

.btn-delete {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  opacity: 0;

  .project-card:hover & {
    opacity: 1;
  }

  &:hover {
    background: var(--accent-danger);
    color: white;
  }
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &-primary {
    background: var(--accent-primary);
    color: white;

    &:hover:not(:disabled) {
      filter: brightness(1.1);
    }
  }

  &-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);

    &:hover:not(:disabled) {
      border-color: var(--accent-primary);
    }
  }
}

// 过渡动画
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;

  .modal {
    transition: transform 0.2s ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .modal {
    transform: scale(0.95);
  }
}
</style>
