<template>
  <header class="app-header">
    <!-- 左侧：Logo + 项目名 -->
    <div class="header-left">
      <div class="logo">
        <i class="fa-solid fa-feather-pointed"></i>
        <span class="logo-text">墨韵</span>
      </div>
      <div class="project-name" v-if="projectStore.currentProject">
        {{ projectStore.currentProject.name }}
      </div>
      <div class="project-name project-name--empty" v-else>未打开项目</div>
    </div>

    <!-- 中间：通知区域 M06 -->
    <div class="header-center" id="header-notifications">
      <!-- NotificationContainer 在这里会被渲染，但为了布局独立，保留占位 -->
    </div>

    <!-- 右侧：LLM状态 + 按钮 -->
    <div class="header-right">
      <!-- LLM连接状态 M0103 -->
      <div
        class="llm-status"
        :class="{ 'llm-status--connected': llmStore.isConnected }"
        @click="uiStore.openSettings()"
        :title="`SSE: ${connectionStatus}`"
      >
        <span class="status-dot"></span>
        <span class="status-text">{{ llmStore.isConnected ? '已连接' : '未连接' }}</span>
        <span v-if="sseConnected" class="sse-dot" title="SSE已连接"></span>
      </div>

      <!-- LLM调用中动画 M0104 -->
      <div class="llm-generating" v-if="llmStore.isGenerating">
        <i class="fa-solid fa-spinner fa-spin"></i>
        <span>AI生成中...</span>
      </div>

      <!-- Thinking开关 M0107 -->
      <div class="thinking-toggle" v-if="llmStore.config && llmStore.config.apiType">
        <span class="thinking-label">Thinking</span>
        <button
          class="toggle-btn"
          :class="{ 'toggle-btn--on': llmStore.config.thinking }"
          @click="toggleThinking"
        >
          <span class="toggle-knob"></span>
        </button>
      </div>

      <!-- 打开项目按钮 M0108 -->
      <button class="btn btn-secondary" @click="uiStore.openOpenProject()">
        <i class="fa-solid fa-folder-open"></i>
        打开项目
      </button>

      <!-- 新建项目按钮 M0109 -->
      <button class="btn btn-primary" @click="uiStore.openCreateProject()">
        <i class="fa-solid fa-plus"></i>
        新建项目
      </button>

      <!-- 设置按钮 M0110 -->
      <button class="btn btn-icon" @click="uiStore.openSettings()" title="设置">
        <i class="fa-solid fa-gear"></i>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useLLMStore } from '@/stores/llm'
import { useUIStore } from '@/stores/ui'
import { useSSE, sseService } from '@/composables/useSSE'

const projectStore = useProjectStore()
const llmStore = useLLMStore()
const uiStore = useUIStore()
const { isConnected: sseConnected, isReconnecting } = useSSE()

const connectionStatus = computed(() => {
  if (isReconnecting.value) return '重连中...'
  if (llmStore.isConnected && sseConnected.value) return '已连接'
  return '未连接'
})

onMounted(async () => {
  // 加载 LLM 配置和连接状态
  await llmStore.loadConfig()
  if (llmStore.config.apiKey) {
    await llmStore.testConnection()
  }
})

async function toggleThinking() {
  llmStore.config.thinking = !llmStore.config.thinking
  await llmStore.saveConfig({ thinking: llmStore.config.thinking })
}
</script>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
  font-weight: 600;
  color: var(--accent-primary);

  .fa-feather-pointed {
    font-size: 20px;
  }
}

.logo-text {
  font-family: var(--font-family-ch);
}

.project-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;

  &--empty {
    color: var(--text-muted);
    font-style: italic;
  }
}

.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.llm-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background 0.2s;

  &:hover {
    background: var(--bg-card);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent-danger);
  }

  &--connected .status-dot {
    background: var(--accent-success);
  }
}

.llm-generating {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--accent-primary);

  .fa-spinner {
    color: var(--accent-primary);
  }
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 8px;

  .thinking-label {
    font-size: 13px;
    color: var(--text-secondary);
  }

  .toggle-btn {
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    position: relative;
    cursor: pointer;
    transition: background 0.2s;

    .toggle-knob {
      position: absolute;
      top: 2px;
      left: 2px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: var(--text-secondary);
      transition: transform 0.2s, background 0.2s;
    }

    &--on {
      background: var(--accent-primary);

      .toggle-knob {
        transform: translateX(16px);
        background: white;
      }
    }
  }
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
  cursor: pointer;

  &:active {
    transform: scale(0.97);
  }

  &-primary {
    background: var(--accent-primary);
    color: white;
    border: none;

    &:hover {
      filter: brightness(1.1);
    }
  }

  &-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);

    &:hover {
      border-color: var(--accent-primary);
      color: var(--accent-primary);
    }
  }

  &-icon {
    width: 34px;
    height: 34px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    border-radius: var(--radius-md);

    &:hover {
      background: var(--bg-card);
      color: var(--text-primary);
    }
  }
}
</style>
