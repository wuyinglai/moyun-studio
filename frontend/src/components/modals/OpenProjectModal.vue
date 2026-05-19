<template>
  <a-modal
    :open="visible"
    title="打开项目"
    :width="700"
    @cancel="close"
  >
    <div class="open-project-modal">
      <a-spin :spinning="isLoading">
        <a-input-search
          v-if="projects.length > 0"
          v-model:value="query"
          class="project-search"
          placeholder="搜索项目名称、题材、作者或 ID"
          allow-clear
        />

        <a-empty
          v-if="projects.length === 0"
          description="暂无项目"
        >
          <template #image>
            <i
              class="fa-solid fa-folder-open"
              style="font-size: 64px; opacity: 0.3"
            />
          </template>
          <template #description>
            <span>点击下方按钮创建第一个项目</span>
          </template>
        </a-empty>

        <a-empty
          v-else-if="filteredProjects.length === 0"
          description="未找到匹配项目"
        />

        <a-list
          v-else
          item-layout="horizontal"
          :data-source="filteredProjects"
          :grid="{ gutter: 16, sm: 2, md: 2, lg: 2, xl: 2, xxl: 2 }"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-card
                hoverable
                class="project-card"
                :class="{ active: selectedId === item.id }"
                @click="selectedId = item.id"
                @dblclick="openProject"
              >
                <template #cover>
                  <div class="project-cover">
                    <i class="fa-solid fa-book" />
                  </div>
                </template>
                <a-card-meta :title="item.name">
                  <template #description>
                    <div class="project-meta">
                      <a-tag
                        v-if="item.genre"
                        :color="'blue'"
                      >
                        {{ item.genre }}
                      </a-tag>
                      <span class="meta-stat">{{ item.total_words?.toLocaleString() || 0 }} 字</span>
                    </div>
                    <div class="project-stats">
                      <span class="meta-stat"><i class="fa-solid fa-calendar" /> {{ formatDate(item.created_at) }}</span>
                      <span class="meta-stat"><i class="fa-solid fa-chart-line" /> {{ item.completion_rate || 0 }}%</span>
                    </div>
                    <div class="project-id">
                      ID: {{ item.id }}
                    </div>
                    <p
                      v-if="item.author"
                      class="project-author"
                    >
                      <i class="fa-solid fa-user" /> {{ item.author }}
                    </p>
                  </template>
                </a-card-meta>
                <template #actions>
                  <a-popconfirm
                    title="确定要删除此项目吗？"
                    ok-text="删除"
                    cancel-text="取消"
                    ok-button-props="danger"
                    @confirm="deleteProject(item)"
                  >
                    <template #icon>
                      <i
                        class="fa-solid fa-exclamation-triangle"
                        style="color: #ff4d4f"
                      />
                    </template>
                    <a-button
                      type="text"
                      danger
                    >
                      <i class="fa-solid fa-trash" />
                    </a-button>
                  </a-popconfirm>
                </template>
              </a-card>
            </a-list-item>
          </template>
        </a-list>
      </a-spin>
    </div>

    <template #footer>
      <a-space>
        <a-button @click="close">
          取消
        </a-button>
        <a-button
          type="primary"
          :disabled="!selectedId"
          @click="openProject"
        >
          <i class="fa-solid fa-folder-open" />
          打开
        </a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/stores/project'
import { useFileStore } from '@/stores/file'
import type { FileNode } from '@/stores/file'
import { useEditorStore } from '@/stores/editor'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notification'

const projectStore = useProjectStore()
const fileStore = useFileStore()
const editorStore = useEditorStore()
const uiStore = useUIStore()
const notification = useNotificationStore()

const visible = computed(() => uiStore.modals.openProject)
const isLoading = computed(() => projectStore.isLoading)
const projects = computed(() => projectStore.projects)
const selectedId = ref<string | null>(null)
const query = ref('')
const filteredProjects = computed(() => {
  const q = query.value.trim().toLowerCase()
  const sorted = [...projects.value].sort((a, b) => {
    const bTime = new Date(b.updated_at || b.created_at || 0).getTime()
    const aTime = new Date(a.updated_at || a.created_at || 0).getTime()
    return bTime - aTime
  })
  if (!q) return sorted
  return sorted.filter((item) => {
    return [item.name, item.genre, item.author, item.id, item.project_id]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(q))
  })
})

watch(visible, async (val) => {
  if (val) {
    await projectStore.loadProjects()
    selectedId.value = null
    query.value = ''
  }
})

async function openProject() {
  if (!selectedId.value) return

  try {
    const project = await projectStore.openProject(selectedId.value)
    await fileStore.loadTree(project.id)
    await openDefaultFile(project.id)
    notification.success(`已打开项目：${project.name}`)
    close()
  } catch {
    notification.error('打开项目失败')
  }
}

async function openDefaultFile(projectId: string) {
  if (fileStore.openFiles.length > 0 && editorStore.currentFilePath) return
  const outline = findFile(fileStore.tree, 'outline.md') || findFirstMarkdown(fileStore.tree)
  if (!outline) return
  const fileData = await fileStore.readFile(projectId, outline.path)
  fileStore.openFile(outline)
  editorStore.loadContent(outline.path, fileData.content || '', fileData.frontmatter)
  editorStore.setCurrentFile(outline.path)
}

function findFile(nodes: FileNode[], name: string): FileNode | null {
  for (const node of nodes) {
    if (node.type === 'file' && node.name === name) return node
    if (node.children) {
      const found = findFile(node.children, name)
      if (found) return found
    }
  }
  return null
}

function findFirstMarkdown(nodes: FileNode[]): FileNode | null {
  for (const node of nodes) {
    if (node.type === 'file' && node.name.endsWith('.md')) return node
    if (node.children) {
      const found = findFirstMarkdown(node.children)
      if (found) return found
    }
  }
  return null
}

async function deleteProject(project: Project) {
  try {
    await projectStore.deleteProject(project.id)
    notification.success(`项目 "${project.name}" 已删除`)

    if (selectedId.value === project.id) {
      selectedId.value = null
    }
  } catch {
    notification.error('删除失败')
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '未知'
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN')
  } catch {
    return dateStr
  }
}

function close() {
  uiStore.closeOpenProject()
  selectedId.value = null
  query.value = ''
}
</script>

<style scoped lang="scss">
.open-project-modal {
  .project-search {
    margin-bottom: 16px;
  }

  .project-cover {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

    i {
      font-size: 48px;
      color: white;
    }
  }

  .project-card {
    &.active {
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }

    :deep(.ant-card-actions) {
      background: var(--bg-secondary);
    }
  }

  .project-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .meta-stat {
    font-size: 12px;
    color: var(--text-muted);
  }

  .project-id {
    margin-top: 4px;
    font-size: 11px;
    color: var(--text-faint);
    word-break: break-all;
  }

  .project-stats {
    display: flex;
    gap: 12px;
    margin-top: 4px;
    font-size: 12px;
    color: var(--text-muted);

    i {
      font-size: 11px;
      margin-right: 2px;
    }
  }

  .project-author {
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 4px;
    margin: 0;

    i {
      font-size: 10px;
    }
  }
}
</style>
