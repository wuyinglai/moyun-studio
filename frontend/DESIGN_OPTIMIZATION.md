# 墨韵写作助手 - 设计优化方案

## 🎨 设计理念

**主题：现代简约东方美学**

融合传统东方美学与现代设计风格，打造一个专注、优雅、高效的写作环境。

---

## 📐 布局重构建议

### 当前布局
```
┌─────────────────────────────────────────────────────────┐
│  [Logo] 项目名称            [状态] [按钮] [按钮] [设置] │
├─────────────┬─────────────────────────────┬─────────────┤
│             │  编辑器                      │             │
│  文件树     │  (75%)                       │  Prompt     │
│             │                             │             │
│  (20%)      ├─────────────────────────────┤  (25%)      │
│             │  聊天区                      │             │
│             │  (25%)                       │             │
└─────────────┴─────────────────────────────┴─────────────┘
```

### 优化后布局
```
┌─────────────────────────────────────────────────────────┐
│  📖 墨韵    ➕ 新建  📂 打开  ⚙️ 设置  [🔴] LLM: 已连接 │
├─────────────┬─────────────────────────────┬─────────────┤
│             │  ┌───────────────────────┐  │  📋 Prompt  │
│  📁 项目    │  │  # 第一章              │  │  📊 状态    │
│             │  │                       │  │  ✨ 风格    │
│  大纲/文件   │  │  编辑器区域           │  │  📜 历史    │
│             │  │                       │  │  ⚡ 任务    │
│  [可折叠]    │  └───────────────────────┘  │  [标签切换] │
│             │                             │             │
│             │  ┌───────────────────────┐  │             │
│             │  │  💭 AI 聊天区          │  │             │
│             │  │  (可折叠)              │  │             │
│             │  └───────────────────────┘  │             │
└─────────────┴─────────────────────────────┴─────────────┘
```

---

## 🌈 配色方案

### 方案一：水墨丹青（主推荐）
```css
--bg-primary: #0f1419
--bg-secondary: #161c22
--bg-card: #1c232a
--bg-tertiary: #242d35

--accent-primary: #6b8cff
--accent-secondary: #8b5cf6
--accent-success: #22c55e
--accent-warning: #f59e0b
--accent-error: #ef4444

--text-primary: #f1f5f9
--text-secondary: #cbd5e1
--text-muted: #64748b

--border-color: #2d3748
--divider-color: #1f2937

--shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.3)
--shadow-glow: 0 0 30px rgba(107, 140, 255, 0.15)
```

### 方案二：竹影轻风
```css
--bg-primary: #f5f3f0
--bg-secondary: #e8e4dd
--bg-card: #faf9f7
--bg-tertiary: #f0ede6

--accent-primary: #10b981
--accent-secondary: #059669
--accent-success: #22c55e
--accent-warning: #f59e0b
--accent-error: #ef4444

--text-primary: #1f2937
--text-secondary: #4b5563
--text-muted: #9ca3af

--border-color: #e5e7eb
--divider-color: #f3f4f6
```

---

## ✨ 组件设计细节

### 1. Header 顶栏优化
- **高度**：从 52px 增加到 60px
- **Logo**：使用更具设计感的字体，添加微动画
- **按钮**：采用胶囊形状，hover 时有微妙的色彩渐变
- **状态指示**：使用脉冲动画增强视觉反馈

### 2. 文件树面板
- **添加大纲视图**：可切换 文件树 / 大纲
- **文件图标**：使用更细腻的图标
- **拖拽排序**：支持文件拖拽（已预留 sortable.js）
- **右键菜单**：添加文件操作右键菜单
- **空状态**：优雅的空状态插画

### 3. 编辑器区域
- **更好的打字体验**：优化行高和字重
- **语法高亮**：更丰富的 Markdown 配色
- **实时预览**：添加分屏预览选项
- **写作统计**：实时字数、阅读时长估算

### 4. Chat 面板
- **气泡设计**：更圆润的聊天气泡
- **思考过程**：优雅的折叠展开动画
- **消息操作**：复制、重新生成、编辑提示
- **快捷回复**：常用问题的快捷回复

### 5. 右侧面板（扩展更多功能！）
| Tab | 功能 |
|-----|------|
| 📋 Prompt | 提示词管理、变量替换 |
| 📊 状态 | 故事状态、文风指南、近期上下文（这三个已存在但未整合到UI！） |
| ✨ 风格 | 写作风格配置、语气调整 |
| 📜 历史 | 对话历史、修订记录（已有 store） |
| ⚡ 任务 | 任务队列、执行状态 |

---

## 🎯 交互改进

### 动画效果
1. **加载动画**：优雅的骨架屏
2. **过渡动画**：面板切换、Tab 切换的平滑过渡
3. **微交互**：按钮 hover、输入框 focus 的微妙反馈
4. **打字效果**：AI 回复的打字机动画

### 快捷键优化
```
Ctrl/Cmd + N  → 新建文件
Ctrl/Cmd + S  → 保存
Ctrl/Cmd + B  → 加粗
Ctrl/Cmd + I  → 斜体
Ctrl/Cmd + K  → 插入链接
Ctrl/Cmd + /  → AI 生成（已预留快捷键系统）
```

---

## 📱 响应式设计

考虑未来支持：
- 平板模式：左右面板可侧滑
- 手机模式：底部 Tab 切换
- 全屏模式：沉浸式写作

---

## 🎨 视觉细节

### 字体选择
```css
--font-title: "Noto Serif SC", "Source Han Serif SC", serif
--font-body: "Noto Sans SC", "PingFang SC", "Helvetica Neue", sans-serif
--font-mono: "JetBrains Mono", "Fira Code", monospace
```

### 圆角和阴影
```css
--radius-sm: 6px
--radius-md: 10px
--radius-lg: 16px
--radius-xl: 24px

--shadow-soft: 0 2px 12px rgba(0,0,0,0.08)
--shadow-medium: 0 4px 24px rgba(0,0,0,0.12)
--shadow-large: 0 8px 40px rgba(0,0,0,0.15)
```

### 间距规范
```
--space-xs: 4px
--space-sm: 8px
--space-md: 12px
--space-lg: 16px
--space-xl: 24px
--space-2xl: 32px
```

---

## 🚀 功能建议（已有代码但未暴露）

### 已实现但需UI：
1. ✅ 故事状态管理 ([stores/storyState.ts](file:///d:/newmoyun/frontend/src/stores/storyState.ts))
2. ✅ 文风指南管理 ([stores/styleGuide.ts](file:///d:/newmoyun/frontend/src/stores/styleGuide.ts))
3. ✅ 近期上下文 ([stores/recentContext.ts](file:///d:/newmoyun/frontend/src/stores/recentContext.ts))
4. ✅ 反馈系统 ([stores/feedback.ts](file:///d:/newmoyun/frontend/src/stores/feedback.ts))
5. ✅ 修订日志 ([stores/revisionLog.ts](file:///d:/newmoyun/frontend/src/stores/revisionLog.ts))
6. ✅ 快捷键系统 ([composables/useHotkeys.ts](file:///d:/newmoyun/frontend/src/composables/useHotkeys.ts))

### 可以快速添加：
- 主题切换（深色/浅色）
- 字数统计悬浮窗
- 每日写作目标
- 写作专注模式
- 导出为多种格式

---

## 📋 下一步实施计划

1. **第一阶段**：更新配色和基础样式
2. **第二阶段**：重新设计 Header 和主要组件
3. **第三阶段**：完善右侧面板，添加更多 Tab
4. **第四阶段**：添加动画和微交互
5. **第五阶段**：集成预留功能（故事状态、文风指南等）

---

*这个设计方案保持了代码的可扩展性，在不破坏现有架构的前提下提供了明确的升级路径！* 🎉
