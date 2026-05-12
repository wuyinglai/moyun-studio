# 墨韵 (MoYun) Vue 3 + Vite 前端重构方案 v2.0
# 严格对齐 D:/newmoyun/docs/原型生成说明.md 所有模块

> 日期: 2026-05-11
> 版本: v2.0（完整覆盖原型生成说明.md）

---

## 一、模块与功能清单（严格对照原型文档）

### M01 顶部工具栏
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0101 | Logo区域（墨韵图标+文字） | `AppHeader.vue` |
| M0102 | 项目名称（可编辑，仅展示） | `AppHeader.vue` |
| M0103 | LLM连接状态（实时更新，可点击） | `AppHeader.vue` + `useLLMStatus.ts` |
| M0104 | LLM调用中动画 | `AppHeader.vue` |
| M0107 | Thinking开关 | `AppHeader.vue` |
| M0108 | 打开项目按钮 → M0502 | `AppHeader.vue` |
| M0109 | 新建项目按钮 → M0501 | `AppHeader.vue` |
| M0110 | 设置按钮 → M0503 | `AppHeader.vue` |

### M02 左侧文件树
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0201 | 标题栏 + 刷新按钮 | `FileTree.vue` |
| M0202 | 文件夹结构（卷/章/节三级） | `FileTree.vue` |
| M0203 | 文件项（点击打开） | `FileTreeItem.vue` |
| M0204 | 项目结构（chapters/characters/materials） | `FileTree.vue` |
| M0205 | 空状态 | `FileTree.vue` |

### M03 中间编辑器区
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0301 | 标签页栏（多文件、关闭、折叠） | `EditorTabs.vue` |
| M0302-1 | 重写本文件按钮 | `EditorToolbar.vue` |
| M0302-2 | 写下一部分按钮 | `EditorToolbar.vue` |
| M0302-3 | 前进按钮（恢复版本） | `EditorToolbar.vue` |
| M0302-4 | 后退按钮（恢复版本） | `EditorToolbar.vue` |
| M0302-5 | 停止按钮（红色，任务中显示） | `EditorToolbar.vue` |
| M0303-1 | 空状态占位符 | `MarkdownEditor.vue` |
| M0303-2 | 内容区（CodeMirror 6） | `EditorPane.vue` |
| M0303-3 | 保存状态（右上角） | `MarkdownEditor.vue` |
| M0304-1 | 消息列表（用户右/AI左，流式追加） | `ChatPanel.vue` |
| M0304-2 | 输入框（Shift+Enter换行，Enter发送） | `ChatInput.vue` |
| M0304-3 | 发送按钮 | `ChatInput.vue` |

### M04 右侧面板
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0401 | Tab标签（Prompt & 执行） | `RightPanel.vue` |
| M0402-1 | 标题（发送给LLM的Prompt） | `PromptPanel.vue` |
| M0402-2 | 内容区（可编辑，变量引用） | `PromptPanel.vue` |
| M0402-3 | 引用文件（点击打开） | `PromptPanel.vue` |
| M0402-4 | 前进/后退（Prompt历史版本） | `PromptPanel.vue` |
| M0403-1 | 状态指示（空闲/运行中） | `ExecutionPanel.vue` |
| M0403-2 | LLM工作堆栈（任务列表） | `ExecutionPanel.vue` |
| M0403-3 | 任务卡片（等待中/执行中/已完成） | `TaskCard.vue` |
| M0403-4 | 执行日志（SSE实时追加） | `ExecutionLog.vue` |

### M05 模态框
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0501-1~5 | 创作参数（题材/基调/背景/主题/写作风格） | `CreateProjectModal.vue` |
| M0501-6 | 作品规模（5万/10万/15万/20万字） | `CreateProjectModal.vue` |
| M0501-7 | 作者名 | `CreateProjectModal.vue` |
| M0501-8 | 创建项目按钮 + 新建流程（步骤1-3） | `CreateProjectModal.vue` |
| M0502-1 | 项目列表（名称/创建时间/完成度） | `OpenProjectModal.vue` |
| M0502-2 | 打开按钮 | `OpenProjectModal.vue` |
| M0502-3 | 删除按钮（需确认） | `OpenProjectModal.vue` |
| M0503-1 | 主题选择（深邃夜紫/墨绿护眼/经典炭灰） | `SettingsModal.vue` |
| M0503-2 | 自动化等级（L1/L2） | `SettingsModal.vue` |
| M0503-3 | API类型（OpenAI/Ollama/Claude/其他） | `SettingsModal.vue` |
| M0503-4 | 后端地址 | `SettingsModal.vue` |
| M0503-5 | API Key | `SettingsModal.vue` |
| M0503-6 | 模型选择 | `SettingsModal.vue` |
| M0503-7 | Thinking开关 | `SettingsModal.vue` |
| M0503-8 | 测试连接按钮 | `SettingsModal.vue` |
| M0503-9 | 获取模型按钮 | `SettingsModal.vue` |

### M06 通知系统
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0601 | 通知项（成功/错误/警告，5秒自动消失） | `Notification.vue` + `NotificationContainer.vue` |

### M07 拖拽调整
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0701 | 左侧边栏分隔线 | `PanelResize.vue` |
| M0702 | 右侧面板分隔线 | `PanelResize.vue` |
| M0703 | 编辑器/聊天区分隔线 | `PanelResize.vue` |
| M0704 | 配置持久化（localStorage） | `usePanelConfig.ts` |

### M08 主题系统
| 编号 | 功能 | 实现组件 |
|------|------|----------|
| M0801 | 深邃夜紫（默认） | `theme.css` |
| M0802 | 墨绿护眼 | `theme.css` |
| M0803 | 经典炭灰 | `theme.css` |
| M0804 | 主题切换入口（设置模态框） | `SettingsModal.vue` |
| M0805 | 配置持久化 | `useTheme.ts` |

### M09 视觉风格
| 编号 | 功能 | 实现方式 |
|------|------|----------|
| M0901 | 字体（中文/英文/代码） | `base.css` |
| M0902 | 圆角（按钮8px/卡片12px/模态框16px） | `base.css` |
| M0903 | 图标（Font Awesome 6.4） | CDN 引入 |

### G01 全局功能（新增）
| 编号 | 功能 | 实现方式 |
|------|------|----------|
| G0120 | 文风指南管理（style-guide.md） | `stores/styleGuide.ts` + `StyleGuidePanel.vue` |
| G0121 | 故事状态管理（story-state.md） | `stores/storyState.ts` |
| G0122 | 近期上下文管理（recent-context.md） | `stores/recentContext.ts` |
| G0123 | 用户反馈管理（feedback/） | `stores/feedback.ts` |
| G0124 | 修改日志管理（revision-log/） | `stores/revisionLog.ts` |

### SSE 事件类型（全部处理）
| 事件类型 | 处理逻辑 | 实现位置 |
|----------|----------|----------|
| `generation` | 编辑器内逐字/逐段显示 | `useSSE.ts` |
| `file-created` | 刷新文件树 | `useSSE.ts` → `stores/file.ts` |
| `file-updated` | 更新编辑器内容 | `useSSE.ts` → `stores/editor.ts` |
| `file-renamed` | 刷新文件树，更新标签页 | `useSSE.ts` |
| `directory-created` | 刷新文件树 | `useSSE.ts` |
| `task` | 更新任务卡片 | `useSSE.ts` → `stores/task.ts` |
| `queue` | 刷新堆栈列表 | `useSSE.ts` |
| `llm-status` | 更新状态灯 | `useSSE.ts` → `stores/llm.ts` |
| `thinking` | 显示"AI正在思考..." | `useSSE.ts` |
| `error` | 显示错误横幅 | `useSSE.ts` → `stores/notification.ts` |
| `done` | 停止动画，显示完成提示 | `useSSE.ts` |

---

## 二、技术选型（严格遵循文档 + 用户决策）

| 类别 | 技术 | 说明 |
|------|------|------|
| 构建 | Vite | ^5.x |
| 框架 | Vue 3 (Composition API) | ^3.4.x |
| 语言 | TypeScript | ^5.x |
| UI 组件 | Ant Design Vue | ^4.x（与原型风格一致） |
| 状态管理 | Pinia | ^2.x |
| 编辑器 | CodeMirror 6 | ^6.x |
| Markdown 渲染 | marked.js | ^12.x |
| XSS 过滤 | DOMPurify | ^3.x |
| 布局分隔 | Split.js | ^1.x |
| 拖拽排序 | SortableJS | ^1.x |
| 快捷键 | hotkeys-js | ^3.x |
| HTTP | axios | ^1.x |
| 样式 | SCSS + CSS 变量 | 替代 TailwindCSS |
| 图标 | Font Awesome 6.4 | CDN |
| 字体 | 思源黑体 / Inter / JetBrains Mono | CDN |

---

## 三、目录结构（完整版）

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── assets/
│   │   ├── styles/
│   │   │   ├── variables.css       # CSS 变量（主题系统）
│   │   │   ├── base.css            # 基础样式重置 + 字体 + 圆角
│   │   │   ├── theme-dark-purple.css  # M0801 深邃夜紫
│   │   │   ├── theme-green.css     # M0802 墨绿护眼
│   │   │   ├── theme-dark-gray.css # M0803 经典炭灰
│   │   │   └── scrollbar.css      # 自定义滚动条
│   │   └── icons/                  # SVG 图标（备用）
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.vue       # M01 顶部工具栏
│   │   │   ├── AppLayout.vue       # 主布局（三栏）
│   │   │   ├── PanelResize.vue     # M07 可拖拽分隔线
│   │   │   ├── NotificationContainer.vue  # M06 通知容器
│   │   │   └── Notification.vue    # M06 单个通知
│   │   ├── file-tree/
│   │   │   ├── FileTree.vue        # M02 文件树容器
│   │   │   ├── FileTreeItem.vue    # M02 单个树节点
│   │   │   └── FileTreeEmpty.vue   # M0205 空状态
│   │   ├── editor/
│   │   │   ├── EditorTabs.vue      # M0301 标签页栏
│   │   │   ├── EditorToolbar.vue   # M0302 工具栏
│   │   │   ├── MarkdownEditor.vue  # M0303 编辑器主组件
│   │   │   ├── EditorPane.vue      # CodeMirror 6 编辑区
│   │   │   ├── EditorPreview.vue   # Markdown 预览
│   │   │   ├── EditorEmpty.vue     # M0303-1 空状态
│   │   │   └── SaveStatus.vue      # M0303-3 保存状态
│   │   ├── chat/
│   │   │   ├── ChatPanel.vue       # M0304 聊天面板
│   │   │   ├── ChatMessages.vue    # M0304-1 消息列表
│   │   │   ├── ChatMessage.vue     # 单条消息
│   │   │   └── ChatInput.vue       # M0304-2/3 输入框
│   │   ├── right-panel/
│   │   │   ├── RightPanel.vue      # M04 右侧面板容器
│   │   │   ├── PromptPanel.vue     # M0402 Prompt面板
│   │   │   ├── ExecutionPanel.vue  # M0403 执行面板
│   │   │   ├── TaskCard.vue        # M0403-3 任务卡片
│   │   │   └── ExecutionLog.vue   # M0403-4 执行日志
│   │   ├── project/
│   │   │   ├── CreateProjectModal.vue  # M0501 新建项目
│   │   │   ├── OpenProjectModal.vue    # M0502 打开项目
│   │   │   └── SettingsModal.vue       # M0503 设置
│   │   ├── global/
│   │   │   ├── StyleGuidePanel.vue  # G0120 文风指南
│   │   │   ├── StoryStatePanel.vue   # G0121 故事状态
│   │   │   └── RecentContextPanel.vue # G0122 近期上下文
│   │   └── common/
│   │       ├── Modal.vue           # 通用模态框
│   │       ├── Button.vue          # 按钮
│   │       ├── Input.vue           # 输入框
│   │       ├── Dropdown.vue        # 下拉菜单
│   │       ├── RadioGroup.vue      # 按钮组单选
│   │       └── EmptyState.vue      # 通用空状态
│   ├── composables/
│   │   ├── useFileTree.ts          # M02 文件树逻辑
│   │   ├── useMarkdownEditor.ts    # M03 编辑器逻辑
│   │   ├── useChat.ts              # M03 聊天逻辑
│   │   ├── useSSE.ts              # SSE 事件处理（全部事件类型）
│   │   ├── useHotkeys.ts           # 快捷键
│   │   ├── useAutoSave.ts          # 自动保存（防抖300ms）
│   │   ├── usePanelConfig.ts       # M07 面板配置持久化
│   │   ├── useTheme.ts             # M08 主题切换
│   │   ├── useMarkdown.ts          # Markdown 解析 + DOMPurify
│   │   └── usePromptTemplate.ts    # M0402 Prompt模板变量替换
│   ├── stores/
│   │   ├── project.ts              # M01/M05 项目状态
│   │   ├── file.ts                 # M02 文件状态
│   │   ├── editor.ts               # M03 编辑器状态
│   │   ├── chat.ts                 # M03 聊天状态
│   │   ├── rightPanel.ts           # M04 右侧面板状态
│   │   ├── llm.ts                  # M01/M05 LLM状态
│   │   ├── ui.ts                   # M06/M07/M08 UI状态
│   │   ├── notification.ts         # M06 通知状态
│   │   ├── task.ts                 # M04 任务状态
│   │   ├── styleGuide.ts           # G0120 文风指南
│   │   ├── storyState.ts           # G0121 故事状态
│   │   ├── recentContext.ts        # G0122 近期上下文
│   │   ├── feedback.ts             # G0123 用户反馈
│   │   └── revisionLog.ts         # G0124 修改日志
│   ├── services/
│   │   ├── api.ts                 # axios 实例 + 拦截器
│   │   ├── project.service.ts     # /api/projects
│   │   ├── file.service.ts        # /api/file, /api/tree
│   │   ├── llm.service.ts        # /api/llm/*
│   │   ├── chat.service.ts        # /api/chat (SSE)
│   │   ├── events.service.ts      # /api/events (SSE)
│   │   ├── task.service.ts        # /api/tasks
│   │   ├── styleGuide.service.ts  # style-guide.md
│   │   ├── storyState.service.ts  # story-state.md
│   │   └── recentContext.service.ts # recent-context.md
│   ├── types/
│   │   ├── api.ts                 # ApiResponse<T>
│   │   ├── project.ts             # Project, CreateProjectDTO
│   │   ├── file.ts                # FileNode, FileTree
│   │   ├── editor.ts              # EditorState, CursorPosition
│   │   ├── chat.ts                # ChatMessage, SSEEvent
│   │   ├── llm.ts                 # LLMConfig, ModelInfo
│   │   ├── task.ts                # Task, TaskStatus
│   │   └── index.ts               # 全局类型导出
│   ├── utils/
│   │   ├── markdown.ts             # marked + DOMPurify 封装
│   │   ├── wordCount.ts           # 字数统计
│   │   ├── storage.ts             # localStorage 封装
│   │   ├── pinyin.ts              # 拼音转换（可选）
│   │   └── promptHelper.ts        # Prompt 变量替换 @{filepath}
│   ├── router/
│   │   └── index.ts               # 路由配置（可选，SPA 可能不需要）
│   ├── App.vue
│   └── main.ts
├── index.html                      # Font Awesome CDN 在此引入
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── package.json
└── env.d.ts
```

---

## 四、核心组件设计

### 4.1 布局组件关系

```
App.vue
└── AppLayout.vue (三栏布局，Split.js)
    ├── 左侧: FileTree.vue (M02)
    ├── 中间: 
    │   ├── EditorTabs.vue (M0301)
    │   ├── EditorToolbar.vue (M0302)
    │   ├── MarkdownEditor.vue (M0303) / ChatPanel.vue (M0304)  ← Split.js 分隔
    │   └── SaveStatus.vue (M0303-3)
    └── 右侧: RightPanel.vue (M04)
        ├── PromptPanel.vue (M0402)
        └── ExecutionPanel.vue (M0403)
        
AppHeader.vue (M01)  ← 顶部固定
NotificationContainer.vue (M06)  ← 绝对定位在顶部中间
```

### 4.2 组件职责详解

#### AppHeader.vue (M01)
- 左侧：M0101 Logo + M0102 项目名称（可编辑）
- 中间：M0601 通知区域
- 右侧：M0103 LLM状态 + M0104 调用动画 + M0107 Thinking开关 + M0108 打开 + M0109 新建 + M0110 设置

#### FileTree.vue (M02)
- M0201 标题栏（刷新按钮）
- M0202 递归渲染卷/章/节结构
- M0203 点击文件 → 打开编辑器
- M0205 空状态
- 调用 `/api/tree` 获取文件树
- 监听 SSE `file-created`/`file-updated`/`file-renamed`/`directory-created` 刷新

#### MarkdownEditor.vue (M03)
- M0301 标签页栏（多文件）
- M0302 工具栏（重写/续写/前进/后退/停止）
- M0303 编辑区（EditorPane.vue with CodeMirror 6）
- M0304 聊天区（ChatPanel.vue）
- M0303-3 保存状态
- 使用 Split.js 分隔编辑区和聊天区（M0703）

#### RightPanel.vue (M04)
- M0401 Tab标签（Prompt & 执行）
- M0402 Prompt面板（可编辑，变量引用）
- M0403 执行面板（任务卡片 + 执行日志）
- 使用 Split.js 分隔 Prompt 和 执行面板（M0702）

#### NotificationContainer.vue (M06)
- M0601 通知项（成功/错误/警告）
- 5秒自动消失
- 关闭按钮

---

## 五、Pinia Store 设计

### 5.1 project.ts
```typescript
interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
}

// Actions
- loadProjects(): Promise<void>
- createProject(data: CreateProjectDTO): Promise<void>  // M0501-8 新建流程
- openProject(id: string): Promise<void>               // M0502-2
- deleteProject(id: string): Promise<void>             // M0502-3
- calculateCompletion(project: Project): number         // M0502 完成度计算
```

### 5.2 file.ts
```typescript
interface FileState {
  tree: FileNode[];
  openFiles: FileNode[];     // M0301 多文件标签
  currentFile: FileNode | null;
  unsavedFiles: Set<string>;
}

// Actions
- loadTree(projectId: string): Promise<void>           // M0201
- selectFile(node: FileNode): Promise<void>            // M0203
- createFile(path: string): Promise<void>
- deleteFile(path: string): Promise<void>
- renameFile(oldPath: string, newPath: string): Promise<void>
- saveFile(path: string, content: string): Promise<void>  // M0303-2 实时保存
- handleSSEFileEvent(event: SSEEvent): void           // SSE 文件事件
```

### 5.3 editor.ts
```typescript
interface EditorState {
  contents: Record<string, string>;  // 多文件内容缓存
  frontmatter: Record<string, any>;
  isDirty: boolean;
  wordCount: number;
  cursorPosition: { line: number; col: number };
}

// Actions
- loadFile(path: string): Promise<void>
- saveCurrentFile(): Promise<void>                      // M0303-2 防抖300ms
- rewriteCurrentFile(): Promise<void>                   // M0302-1
- writeNextPart(): Promise<void>                        // M0302-2
- undo(): Promise<void>                                 // M0302-4
- redo(): Promise<void>                                 // M0302-3
```

### 5.4 chat.ts
```typescript
interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  currentTool: string | null;
}

// Actions
- sendMessage(content: string): void                   // M0304-2/3 SSE流式
- handleSSEGeneration(event: SSEEvent): void           // `generation` 事件
- handleSSEThinking(event: SSEEvent): void             // `thinking` 事件
- handleSSEDone(event: SSEEvent): void                 // `done` 事件
- cancelStream(): void                                 // M0302-5 停止按钮
```

### 5.5 rightPanel.ts
```typescript
interface RightPanelState {
  activeTab: 'prompt' | 'execution';
  promptContent: string;
  promptHistory: string[];
  currentHistoryIndex: number;
}

// Actions
- loadPromptTemplate(operation: string): Promise<void>  // M0402-2
- updatePrompt(content: string): void                  // M0402-2 可编辑
- navigatePromptHistory(direction: 'forward' | 'backward'): void  // M0402-4
- loadTaskQueue(): Promise<void>                       // M0403-2
- handleSSETaskEvent(event: SSEEvent): void            // SSE `task`/`queue` 事件
```

### 5.6 llm.ts
```typescript
interface LLMState {
  config: LLMConfig;
  isConnected: boolean;
  isThinking: boolean;
  isGenerating: boolean;
}

// Actions
- loadConfig(): Promise<void>                         // M0103 加载配置
- testConnection(): Promise<boolean>                   // M0103/M0503-8
- fetchModels(): Promise<string[]>                     // M0503-9
- updateConfig(config: Partial<LLMConfig>): Promise<void>  // M0503-4~7
- handleSSEStatusEvent(event: SSEEvent): void          // SSE `llm-status` 事件
```

### 5.7 notification.ts (M06)
```typescript
interface NotificationState {
  notifications: Notification[];
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning';
  message: string;
  autoClose: boolean;  // 默认true，5秒后消失
}

// Actions
- addNotification(notification: Omit<Notification, 'id'>): void
- removeNotification(id: string): void
- clearAll(): void
```

### 5.8 task.ts (M04)
```typescript
interface TaskState {
  tasks: Task[];
  queue: string[];  // 任务ID队列
}

interface Task {
  id: string;
  name: string;
  status: 'waiting' | 'running' | 'completed' | 'failed';
  progress: number;
}

// Actions
- loadTasks(): Promise<void>
- handleSSETaskEvent(event: SSEEvent): void
- handleSSEQueueEvent(event: SSEEvent): void
```

### 5.9 ui.ts (M07/M08)
```typescript
interface UIState {
  theme: 'dark-purple' | 'green' | 'dark-gray';  // M08
  panelWidths: {
    left: number;    // M0701
    right: number;    // M0702
    editorChat: number;  // M0703 编辑区/聊天区比例
  };
  isSettingsOpen: boolean;
  isCreateProjectOpen: boolean;
  isOpenProjectOpen: boolean;
}

// Actions
- setTheme(theme: Theme): void                       // M0804/M0805
- setPanelWidth(panel: string, width: number): void  // M0704 持久化
- setEditorChatSplit(ratio: number): void             // M0703
```

---

## 六、API 服务层

### 6.1 axios 实例配置
```typescript
// services/api.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 响应拦截器（统一处理 { success, data, message }）
api.interceptors.response.use(
  (response) => {
    const { success, data, message } = response.data;
    if (!success) {
      throw new Error(message || '请求失败');
    }
    return data;  // 直接返回 data，不包一层
  },
  (error) => {
    const message = error.response?.data?.message || error.message;
    // 触发通知
    useNotificationStore().addNotification({
      type: 'error',
      message,
    });
    return Promise.reject(error);
  }
);
```

### 6.2 SSE 服务（处理全部事件类型）
```typescript
// services/events.service.ts
class EventService {
  private eventSource: EventSource | null = null;
  
  connect(callbacks: SSECallbacks): void {
    this.eventSource = new EventSource(`${baseURL}/api/events`);
    
    // 全部 SSE 事件类型
    this.eventSource.addEventListener('generation', (e) => {
      callbacks.onGeneration(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('file-created', (e) => {
      callbacks.onFileCreated(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('file-updated', (e) => {
      callbacks.onFileUpdated(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('file-renamed', (e) => {
      callbacks.onFileRenamed(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('directory-created', (e) => {
      callbacks.onDirectoryCreated(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('task', (e) => {
      callbacks.onTask(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('queue', (e) => {
      callbacks.onQueue(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('llm-status', (e) => {
      callbacks.onLLMStatus(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('thinking', (e) => {
      callbacks.onThinking(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('error', (e) => {
      callbacks.onError(JSON.parse(e.data));
    });
    this.eventSource.addEventListener('done', (e) => {
      callbacks.onDone(JSON.parse(e.data));
    });
  }
  
  disconnect(): void {
    this.eventSource?.close();
    this.eventSource = null;
  }
}
```

---

## 七、关键技术难点与解决方案

### 7.1 CodeMirror 6 集成
- **挑战**: CM6 配置复杂，与 Vue 响应式系统配合困难
- **方案**: 
  - `useMarkdownEditor.ts` composable 管理 EditorView 实例
  - 使用 `shallowRef` 存储 EditorView（避免深度响应式）
  - 监听 `update` 事件同步到 Pinia store
  - 提供 `getValue()` / `setValue()` / `insertText()` 方法

```typescript
// composables/useMarkdownEditor.ts
export function useMarkdownEditor(container: Ref<HTMLElement | null>) {
  const view = shallowRef<EditorView | null>(null);
  
  const initEditor = (initialContent: string) => {
    if (!container.value) return;
    
    view.value = new EditorView({
      doc: initialContent,
      extensions: [
        markdown(),
        EditorView.lineWrapping,
        oneDark,  // 根据主题切换
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const content = update.state.doc.toString();
            useEditorStore().updateContent(content);
          }
        }),
      ],
      parent: container.value,
    });
  };
  
  const getValue = () => view.value?.state.doc.toString() || '';
  const setValue = (content: string) => { /* ... */ };
  const insertText = (text: string) => { /* ... */ };
  
  return { view, initEditor, getValue, setValue, insertText };
}
```

### 7.2 Split.js 多区域布局
- **挑战**: 三个区域（左/中/右）+ 中间区域再分（编辑/聊天）
- **方案**:
  - 外层：Split.js 分三栏（左 | 中 | 右）
  - 中间栏内部：第二个 Split.js 分上下（编辑区 | 聊天区）
  - 拖动分隔线时实时保存到 localStorage（M0704）

```vue
<!-- AppLayout.vue -->
<template>
  <div class="app-layout">
    <Split v-model:sizes="layoutSizes" min-size="[200, 400, 300]" @resize="onLayoutResize">
      <div class="left-panel">
        <FileTree />
      </div>
      <div class="center-panel">
        <Split v-model:sizes="editorChatSizes" direction="vertical" min-size="[200, 100]">
          <div class="editor-area">
            <MarkdownEditor />
          </div>
          <div class="chat-area">
            <ChatPanel />
          </div>
        </Split>
      </div>
      <div class="right-panel">
        <RightPanel />
      </div>
    </Split>
  </div>
</template>
```

### 7.3 SSE 流式处理与多事件类型
- **挑战**: 多个 SSE 事件类型，需要正确路由到对应的 store
- **方案**:
  - `useSSE.ts` composable 统一处理所有事件类型
  - 每个事件类型对应一个处理函数，更新对应的 Pinia store
  - 支持 `AbortController` 取消请求（M0302-5 停止按钮）

### 7.4 Markdown 预览安全
- **挑战**: XSS 风险
- **方案**:
  - `marked.js` 解析 Markdown
  - `DOMPurify.sanitize()` 过滤 HTML
  - 自定义代码高亮（highlight.js 或 Shiki）

```typescript
// utils/markdown.ts
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export function renderMarkdown(content: string): string {
  const html = marked.parse(content, { breaks: true });
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'a'],
    ALLOWED_ATTR: ['href', 'class'],
  });
}
```

### 7.5 Prompt 模板变量替换
- **挑战**: 支持 `@{文件路径}`、`{{ story_state }}` 等变量引用
- **方案**:
  - `usePromptTemplate.ts` composable
  - 正则表达式匹配变量 `(@\\{[^}]+\\}|\\{\\{\\s*\\w+\\s*\\}\\})`
  - 异步加载引用的文件内容
  - 渲染到 M0402-2 Prompt面板

### 7.6 新建项目流程（M0501 步骤1-3）
- **挑战**: 多步骤向导，需要 SSE 流式生成
- **方案**:
  - `CreateProjectModal.vue` 分步骤显示
  - 步骤1：调用 `/api/chat` 生成书名+创意（SSE流式显示）
  - 步骤2：生成章节大纲（卷/章/节结构）
  - 步骤3：自动生成目录结构，开始写作

---

## 八、分阶段实施计划（修正版）

### Phase 1: 基础架构 + 布局（Day 1-3）

**目标**: 搭建项目，实现三栏布局和基础路由

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 1.1 | 初始化 Vite + Vue 3 + TypeScript + SCSS | - |
| 1.2 | 安装依赖（ant-design-vue, codemirror, marked, dompurify, split.js, sortablejs, hotkeys-js, axios） | - |
| 1.3 | 配置 Vite（路径别名、代理） | - |
| 1.4 | 创建目录结构 | 第三节 |
| 1.5 | 实现 CSS 变量和主题系统（M08） | M0801~M0805 |
| 1.6 | 实现 `AppLayout.vue` 三栏布局（Split.js） | M07 |
| 1.7 | 实现 `AppHeader.vue` 基础结构 | M01 |
| 1.8 | 配置 axios 实例 + 响应拦截器 | 6.1 |
| 1.9 | 创建 Pinia stores（project, ui, notification） | 第五节 |
| 1.10 | 实现 `NotificationContainer.vue` | M06 |

**交付物**: 可运行的三栏布局框架，主题可切换，通知系统可用

---

### Phase 2: 文件树 + 项目管理（Day 4-6）

**目标**: 实现文件树展示和项目 CRUD

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 2.1 | 实现 `FileTree.vue` + `FileTreeItem.vue` | M02 |
| 2.2 | 实现文件树空状态 | M0205 |
| 2.3 | 对接 `/api/tree` 获取文件树 | M0201 |
| 2.4 | 实现 `CreateProjectModal.vue`（创作参数+作品规模） | M0501 |
| 2.5 | 实现新建项目流程（步骤1-3，SSE流式） | M0501 |
| 2.6 | 实现 `OpenProjectModal.vue`（项目列表+完成度计算） | M0502 |
| 2.7 | 实现项目删除（确认对话框） | M0502-3 |
| 2.8 | 对接 `/api/projects/*` 接口 | M01/M05 |
| 2.9 | 实现 `useFileTree.ts` composable | M02 |

**交付物**: 可以创建/打开/删除项目，文件树可展示

---

### Phase 3: 编辑器核心（Day 7-10）

**目标**: 实现 Markdown 编辑器和预览

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 3.1 | 实现 `EditorTabs.vue` 多文件标签 | M0301 |
| 3.2 | 实现 `EditorToolbar.vue`（重写/续写/前进/后退/停止） | M0302 |
| 3.3 | 集成 CodeMirror 6 到 `EditorPane.vue` | M0303-2 |
| 3.4 | 实现 `useMarkdownEditor.ts` composable | 7.1 |
| 3.5 | 实现 Markdown 预览（`EditorPreview.vue`） | M0303-2 |
| 3.6 | 实现 `renderMarkdown()` 工具函数（marked + DOMPurify） | 7.4 |
| 3.7 | 实现自动保存（防抖300ms） | M0303-2 |
| 3.8 | 实现保存状态显示 | M0303-3 |
| 3.9 | 实现编辑器空状态 | M0303-1 |
| 3.10 | 对接 `/api/file` 读写接口 | M02/M03 |

**交付物**: 可以编辑和预览 Markdown，自动保存

---

### Phase 4: 聊天面板 + SSE（Day 11-13）

**目标**: 实现 AI 对话和 SSE 流式交互

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 4.1 | 实现 `ChatPanel.vue` 结构 | M0304 |
| 4.2 | 实现 `ChatMessages.vue` 消息列表（用户右/AI左） | M0304-1 |
| 4.3 | 实现 `ChatInput.vue`（Shift+Enter换行，Enter发送） | M0304-2/3 |
| 4.4 | 实现 `useChat.ts` composable | M03 |
| 4.5 | 实现 `useSSE.ts` 处理全部 SSE 事件类型 | SSE 事件类型 |
| 4.6 | 对接 `/api/chat` SSE 接口（流式输出） | M0304-1 |
| 4.7 | 实现停止按钮功能（`/api/stop`） | M0302-5 |
| 4.8 | 处理 `generation` 事件（逐字追加） | SSE |
| 4.9 | 处理 `thinking` 事件（"AI正在思考..."） | SSE |

**交付物**: 可以与 AI 对话，流式输出，可停止

---

### Phase 5: 右侧面板（Day 14-16）

**目标**: 实现 Prompt 面板和执行面板

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 5.1 | 实现 `RightPanel.vue` 容器 | M04 |
| 5.2 | 实现 `PromptPanel.vue`（可编辑，变量引用） | M0402 |
| 5.3 | 实现 `usePromptTemplate.ts` 变量替换 | 7.5 |
| 5.4 | 实现 Prompt 历史版本前进/后退 | M0402-4 |
| 5.5 | 实现 `ExecutionPanel.vue` | M0403 |
| 5.6 | 实现 `TaskCard.vue`（等待中/执行中/已完成） | M0403-3 |
| 5.7 | 实现 `ExecutionLog.vue`（SSE实时追加） | M0403-4 |
| 5.8 | 对接 `/api/tasks` 和 SSE `task`/`queue` 事件 | M04 |
| 5.9 | 实现工作堆栈显示 | M0403-2 |

**交付物**: Prompt 可编辑，执行面板显示任务和日志

---

### Phase 6: 设置 + 主题 + 拖拽（Day 17-19）

**目标**: 实现设置模态框、主题切换、面板拖拽

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 6.1 | 实现 `SettingsModal.vue`（主题/自动化等级/API配置） | M0503 |
| 6.2 | 实现主题切换（三套主题CSS） | M08 |
| 6.3 | 实现主题配置持久化 | M0805 |
| 6.4 | 实现 LLM 配置（API类型/地址/Key/模型） | M0503-3~6 |
| 6.5 | 实现测试连接和获取模型按钮 | M0503-8/9 |
| 6.6 | 实现 Thinking 开关 | M0107/M0503-7 |
| 6.7 | 实现面板拖拽调整（Split.js） | M07 |
| 6.8 | 实现配置持久化（localStorage） | M0704 |
| 6.9 | 实现快捷键（hotkeys-js） | G01 |

**交付物**: 可以切换主题，配置LLM，拖拽调整面板

---

### Phase 7: 全局功能 + 高级特性（Day 20-22）

**目标**: 实现 G0120~G0124 全局功能

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 7.1 | 实现文风指南管理（加载/编辑 `style-guide.md`） | G0120 |
| 7.2 | 实现故事状态管理（自动更新 `story-state.md`） | G0121 |
| 7.3 | 实现近期上下文管理（追加 `recent-context.md`） | G0122 |
| 7.4 | 实现用户反馈管理（保存到 `feedback/` 目录） | G0123 |
| 7.5 | 实现修改日志管理（保存到 `revision-log/` 目录） | G0124 |
| 7.6 | 实现完成度计算（有内容的节数/计划节总数） | M0502 |
| 7.7 | 实现版本前进/后退（Snapshot 恢复） | M0302-3/4 |
| 7.8 | 实现 SSE 全部事件处理（`file-created`, `file-updated`, etc.） | SSE |

**交付物**: 全局功能完整，SSE 事件全部处理

---

### Phase 8: 优化 + 测试（Day 23-25）

**目标**: 性能优化，bug修复，E2E测试

| 任务 | 描述 | 对应模块 |
|------|------|----------|
| 8.1 | 性能优化（虚拟滚动、懒加载、CodeMirror 大文件处理） | - |
| 8.2 | 添加加载状态和错误处理 | - |
| 8.3 | 响应式布局优化 | - |
| 8.4 | TypeScript 类型完善 | - |
| 8.5 | 编写组件单元测试（Vitest） | - |
| 8.6 | E2E 测试（Playwright） | - |
| 8.7 | 更新文档（README + 组件文档） | - |
| 8.8 | 构建优化（代码分割、懒加载） | - |
| 8.9 | 部署配置（Docker + Nginx） | - |

**交付物**: 可发布的产品级应用

---

## 九、关键文件清单

### 新建文件（frontend/ 目录）
全部在第三节「目录结构」中列出，共约 **60+ 文件**。

### 需要修改的现有文件
| 文件 | 操作 | 原因 |
|------|------|------|
| `prototype.html` | 保留，不删除 | 作为备份参考 |
| `docs/原型生成说明.md` | 无需修改 | 本文档即依据 |
| `docs/技术选型与依赖.md` | 无需修改 | 已遵循 |
| `backend/main.py` | 可能需微调 | CORS 允许前端 dev server |

---

## 十、验证标准

1. ✅ **功能完整性**: 所有 M01~M09 和 G0120~G0124 模块全部实现
2. ✅ **技术选型合规**: 所有文档要求的库全部引入并使用
3. ✅ **代码质量**: TypeScript 严格模式，无 `any` 类型
4. ✅ **UI还原度**: 与原型生成说明.md 描述一致（三栏布局、主题、通知）
5. ✅ **SSE 完整性**: 全部 10 种 SSE 事件类型均有处理
6. ✅ **E2E 测试**: Playwright 测试覆盖核心流程（创建项目→编辑→AI对话）
7. ✅ **性能**: 首屏加载 < 2s，编辑器响应 < 100ms
8. ✅ **构建产物**: gzip 后 < 500KB（代码分割）

---

## 十一、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| CodeMirror 6 配置复杂 | 开发进度延迟 | 先做基础功能，高级功能（代码折叠、括号匹配）后续迭代 |
| SSE 连接不稳定 | AI对话功能不可用 | 实现断线重连机制，错误提示 |
| 大文件性能问题 | 编辑器卡顿 | 虚拟滚动，分块加载，提示用户拆分文件 |
| 主题切换闪屏 | UX 差 | CSS 变量即时切换，无闪屏 |
| 构建产物过大 | 加载慢 | 代码分割，懒加载，CDN 引入大的库 |

---

*计划完成日期: 2026-05-11*  
*计划版本: v2.0（完整覆盖原型生成说明.md 所有模块）*
