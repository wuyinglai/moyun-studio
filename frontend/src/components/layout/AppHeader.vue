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
import { onMounted, computed } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useLLMStore } from '@/stores/llm'
import { useUIStore } from '@/stores/ui'
import { useSSE } from '@/composables/useSSE'

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
  height: 60px;
  padding: 0 24px;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 16px;
  position: relative;
  backdrop-filter: blur(10px);

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
    opacity: 0.3;
  }
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
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--accent-primary);
  cursor: pointer;
  transition: transform 0.15s ease;

  &:hover {
    transform: scale(1.02);
  }

  .fa-feather-pointed {
    font-size: 24px;
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
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
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 9999px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transition: all 0.25s ease;

  &:hover {
    border-color: var(--accent-primary);
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent-error);
    position: relative;

    &::after {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 100%;
      height: 100%;
      border-radius: 50%;
      background: inherit;
      animation: pulse 2s ease-out infinite;
    }
  }

  &--connected .status-dot {
    background: var(--accent-success);
  }
}

.llm-generating {
  display: flex;
  align-items: center;
  gap: 8px;
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
    width: 40px;
    height: 22px;
    border-radius: 11px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    position: relative;
    cursor: pointer;
    transition: all 0.25s ease;

    .toggle-knob {
      position: absolute;
      top: 2px;
      left: 2px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--text-secondary);
      transition: transform 0.25s ease, background 0.25s ease;
    }

    &--on {
      background: var(--accent-primary);
      border-color: var(--accent-primary);

      .toggle-knob {
        transform: translateX(18px);
        background: white;
      }
    }
  }
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 9999px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.25s ease;
  cursor: pointer;
  border: none;
  position: relative;
  overflow: hidden;

  &:active {
    transform: scale(0.97);
  }

  &-primary {
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    color: white;
    box-shadow: 0 4px 14px rgba(107, 140, 255, 0.3);

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(107, 140, 255, 0.4);
    }
  }

  &-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);

    &:hover {
      background: var(--bg-hover);
      border-color: var(--accent-primary);
      color: var(--accent-primary);
    }
  }

  &-icon {
    width: 42px;
    height: 42px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    border-radius: 12px;

    &:hover {
      background: var(--bg-card);
      color: var(--accent-primary);
    }
  }
}
</style>
