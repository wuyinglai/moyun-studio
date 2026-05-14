# Prompt 体系重构 + 管线引擎设计

> 版本：v1（2026-05-14）
> 状态：设计定稿，待实现

---

## 一、设计目标

将墨韵从"一个 Prompt 用到底"升级为"多管线可编排、每步 Prompt 可编辑、用户可自定义"的系统。

### 核心原则

1. **前端零感知** — 管线多步迭代对用户透明，点一下等结果
2. **质量优先** — 每步有具体的质量目标，不是泛泛的生成→检查→修复
3. **可编排** — 用户可添加/删除/排序步骤，编辑每步的 Prompt
4. **统一入口** — 工具栏按钮直接映射到管线，右侧面板统一管理

---

## 二、管线引擎（后端）

### 2.1 架构

```
新增: backend/core/pipeline.py — PipelineRunner 引擎
新增: backend/schemas/pipeline.py — 管线相关 Pydantic 模型
新增: backend/api/pipeline.py — 管线运行/编辑 API
新增: workspace/prompts/pipeline/ — 每步的 Prompt 模板目录

修改: backend/api/generate.py — 接入管线引擎
修改: backend/schemas/llm.py — 新增请求/响应类型
```

### 2.2 Pipeline 定义格式

每条管线一个 YAML 文件，存储在 `workspace/prompts/pipeline/`：

```yaml
# workspace/prompts/pipeline/polish.yaml
name: polish
label: 润色
steps:
  - id: depai
    label: 去AI味
    prompt: pipeline/polish/depai
    fallback: null

  - id: prose
    label: 提升文笔
    prompt: pipeline/polish/prose
    fallback: depai

  - id: logic
    label: 修正逻辑
    prompt: pipeline/polish/logic
    fallback: prose

  - id: rhythm
    label: 优化节奏
    prompt: pipeline/polish/rhythm
    fallback: logic
```

### 2.3 PipelineRunner 接口

```python
class PipelineRunner:
    async def run(
        pipeline_name: str,
        project_id: str,
        target_file: str | None,
        user_input: str | None,       # 对话/自定义指令
        output_mode: "overwrite" | "append" | "dimension_file",
    ) -> AsyncGenerator[dict, None]:
        # 1. 加载 pipeline YAML
        # 2. 按步骤顺序执行
        # 3. 每步：渲染 prompt → 调用 LLM → 输出传给下一步
        # 4. 流式输出: thinking 事件(中间步骤) / generation 事件(最终输出)
```

### 2.4 流式策略

| SSE 事件 | 触发时机 | 前端处理 |
|----------|----------|---------|
| `thinking` | 每步开始时 | 显示"正在去AI味..."等状态文字 |
| `generation` | 最终步骤输出时 | 流式写入编辑器 |
| `step_done` | 单步完成 | 更新步骤进度 |
| `prompt` | prompt 渲染完成后 | 更新右侧面板显示 |
| `done` | 全部完成 | 完成提示 |

中间步骤的输出**不发** `generation` 事件，只发 `thinking` 告知状态。

### 2.5 失败处理

- 每步配置 `fallback` 字段，指向某步的输出变量名
- 当前步骤失败时，使用 fallback 步骤的结果继续
- 无 fallback → 抛出异常，终止管线

### 2.6 五条初始管线

#### ✏️ polish（润色）

| 步骤 | ID | 目标 | 输出 |
|------|----|------|------|
| 去AI味 | depai | 删除「突然」「不禁」「心中一震」等 AI 高频套路词 | 覆盖当前文件 |
| 提升文笔 | prose | 优化句式、用词、描写密度 | ↑ |
| 修正逻辑 | logic | 情节矛盾、时间线冲突、角色行为不一致 | ↑ |
| 优化节奏 | rhythm | 张弛有度、长短句交替、段落节奏 | ↑ 最终输出 |

#### 📝 generate（生成新章节）

| 步骤 | ID | 目标 |
|------|----|------|
| 整合上下文 | context | 收集角色/设定/前情/故事状态 |
| 大纲对齐 | outline | 确认本节覆盖大纲哪些要点 |
| 写作初稿 | draft | 按大纲写作 |
| 去AI味 | depai | 同上 |
| 逻辑修正 | logic | 同上 |
| 优化节奏 | rhythm | 同上 |

输出模式：append（追加到当前文件）

#### 📦 rewrite（重写）

| 步骤 | ID | 目标 |
|------|----|------|
| 诊断问题 | diagnose | 分析原文的核心问题（结构/文笔/逻辑） |
| 重写初稿 | draft | 基于诊断重写 |
| 去AI味 | depai | 同上 |
| 逻辑修正 | logic | 同上 |
| 节奏调整 | rhythm | 同上 |

输出模式：overwrite（覆盖当前文件）

#### 💬 chat（对话）

| 步骤 | ID | 目标 |
|------|----|------|
| 意图理解 | understand | 解析用户自然语言指令，提取操作意图 |
| 生成 | draft | 执行修改 |
| 校验 | validate | 检查是否符合用户指令 |

输入：用户自然语言 + 当前文件内容
输出模式：overwrite 或 append，取决于用户意图

#### 🌟 extract（信息提取）

按维度逐轮提取，每轮一个维度，按顺序执行：

| 轮次 | 维度 | 目标文件 |
|------|------|---------|
| 1 | 世界观 | `materials/extracted/worldbuilding.md` |
| 2 | 角色 + 关系 | `materials/extracted/characters.md` |
| 3 | 情节 + 场景 | `materials/extracted/plots.md` |
| 4 | 摘要 | `materials/extracted/summaries.md` |

每轮独立调用，结果写入对应文件。

---

## 三、前端改造

### 3.1 顶部工具栏

11 个按钮 → 4 个核心按钮 + 1 个自定义入口：

```
[✏️ 润色] [📝 生成] [📦 重写] [🌟 提取] [➕ 自定义]
```

- 前 4 个 = 4 条预置管线，点击直接运行
- 「自定义」= 用户创建的管线，点击展开菜单选择
- 对话管线由编辑器底部的聊天输入框触发（见 3.7）
- 原有批量生成/质量审查/Token 等功能移到菜单或设置中

### 3.2 右侧面板 Tab

当前 5 个 Tab → 优化为 5 个：

| Tab | 图标 | 用途 |
|-----|------|------|
| **快捷** | ⚡ | 管线选择 + prompt 编辑 + 一键运行（日常使用） |
| **管线编辑** | 🔧 | 步骤编排 + prompt 深度编辑 + 新建管线 |
| **故事状态** | 📖 | 已有，不变 |
| **文风指南** | 🪶 | 已有，不变 |
| **执行** | 📋 | 已有，不变 |

删除「上下文」Tab（故事状态已覆盖）。

### 3.3 「快捷」Tab 布局

```
┌────────────────────────────────┐
│ 当前管线: [润色 ▼]  [▶ 运行]   │
├────────────────────────────────┤
│ 当前步骤: [去AI味] [文笔] [逻辑]│    ← 点步骤标签可切换查看/编辑
├────────────────────────────────┤
│ Prompt 编辑区                   │
│ (可直接编辑，改完即生效)         │
│                                │
│ 可以使用 [文件引用.md]           │
│ 和 {{系统变量}}                 │
├────────────────────────────────┤
│ 提示: 拖拽文件树文件到此处生成引用│
└────────────────────────────────┘
```

### 3.4 「管线编辑」Tab 布局

```
┌────────────────────────────────┐
│ 管线: [润色 ▼]  [+ 新建管线]   │
├────────────────────────────────┤
│ 步骤列表 (可拖拽排序)            │
│ ⠿ 去AI味        ✕              │
│ ⠿ 提升文笔      ✕              │
│ ⠿ 修正逻辑      ✕              │
│ ⠿ 优化节奏      ✕              │
│ [+ 添加步骤]                   │
├────────────────────────────────┤
│ 选中步骤的 Prompt 编辑区        │
│ (完整编辑体验)                  │
├────────────────────────────────┤
│ [保存]                         │
└────────────────────────────────┘
```

### 3.5 引用机制

用户在 Prompt 编辑区可使用：

| 语法 | 说明 | 示例 |
|------|------|------|
| `[文件名.md]` | 引用项目文件，自动注入内容 | 参考 `[style-guide.md]` 的文风 |
| `{{变量名}}` | 系统变量，自动填充 | `{{current_file}}` |
| 拖拽 | 从文件树拖入生成引用 | 拖拽文件 → `[文件名.md]` |

系统变量预置（初期）：

| 变量 | 说明 |
|------|------|
| `{{current_file}}` | 当前编辑文件内容 |
| `{{outline}}` | 项目大纲 |
| `{{style_guide}}` | 文风指南 |
| `{{story_state}}` | 故事全局状态 |
| `{{recent_context}}` | 近期上下文 |
| `{{characters}}` | 所有角色档案 |

### 3.6 prompt 保存

每次编辑 prompt 后：

- 用户编辑系统预置管线的 prompt → 保存到工作区 `workspace/prompts/pipeline/` 对应文件
- 用户新建自定义管线 → 保存到 `.moyun/custom-pipelines/` 目录
- 保存即生效，下次运行即为新版本

### 3.7 触发链路

工具栏按钮触发管线：

```
用户在快捷标签选管线 → 编辑 prompt → 点运行
  → 前端调用 POST /api/pipeline/run
  → 后端 PipelineRunner 逐步执行
  → SSE 流式返回事件
  → 前端显示 thinking 状态 → 流式写入编辑器
  → 完成后提示用户
```

聊天输入框触发对话管线：

```
用户在编辑器底部聊天输入框输入 → 发送
  → 前端调用 POST /api/pipeline/run { pipeline: "chat" }
  → 后端意图理解 → 生成 → 校验
  → SSE 流式写入编辑器 + 聊天区同步显示
  → 输出覆盖/追加到当前文件
```

---

## 四、管线配置编辑与 Prompt 模板的关系

每条管线有两层配置，分别在不同位置：

```
管线定义:  workspace/prompts/pipeline/{name}.yaml
  └── 步骤定义（名称、顺序、fallback）

Prompt 模板: workspace/prompts/pipeline/{name}/{step_id}.md
  └── 每一步的完整 Prompt 文本
```

用户在前端编辑 prompt 时，直接修改对应步骤的 `.md` 文件。修改后立即生效，不需要重启后端。

自定义管线存储在 `.moyun/custom-pipelines/{name}/`，结构与系统预置相同。

---

## 五、API 设计

### POST /api/pipeline/run

运行一条管线：

```json
{
  "pipeline": "polish",
  "project_id": "my-novel",
  "target_file": "chapters/vol-01/ch-001/sec-002.md",
  "user_input": null,
  "output_mode": "overwrite"
}
```

响应：SSE 事件流（同现有 `/api/generate` 格式）

### GET /api/pipeline/list

获取所有可用管线列表（系统预置 + 用户自定义）：

```json
{
  "pipelines": [
    {"name": "polish", "label": "润色", "steps": ["depai", "prose", "logic", "rhythm"]},
    {"name": "generate", "label": "生成", "steps": ["context", "outline", "draft", "depai", "logic", "rhythm"]}
  ]
}
```

### GET /api/pipeline/{name}

获取管线详情（定义 + 每步的 prompt 内容）：

```json
{
  "name": "polish",
  "label": "润色",
  "steps": [
    {"id": "depai", "label": "去AI味", "prompt_content": "请删除以下AI高频词...", "fallback": null},
    ...
  ]
}
```

### PUT /api/pipeline/{name}

保存管线定义或某步的 prompt 内容。

### POST /api/pipeline/{name}/step

在管线中新增一个步骤。

### DELETE /api/pipeline/{name}/step/{step_id}

删除管线中的某个步骤。

### POST /api/pipeline/custom

创建自定义管线（用户定义名称和步骤）。

---

## 六、文件变动清单

### 新增

| 文件 | 说明 |
|------|------|
| `backend/core/pipeline.py` | PipelineRunner 引擎 |
| `backend/schemas/pipeline.py` | 管线相关的 Pydantic 模型 |
| `backend/api/pipeline.py` | 管线运行/编辑 API |
| `workspace/prompts/pipeline/polish.yaml` | 润色管线定义 |
| `workspace/prompts/pipeline/generate.yaml` | 生成管线定义 |
| `workspace/prompts/pipeline/rewrite.yaml` | 重写管线定义 |
| `workspace/prompts/pipeline/chat.yaml` | 对话管线定义 |
| `workspace/prompts/pipeline/extract.yaml` | 提取管线定义 |
| `workspace/prompts/pipeline/polish/depai.md` | 去AI味 prompt 模板 |
| `workspace/prompts/pipeline/polish/prose.md` | 提升文笔 prompt 模板 |
| ... (各步骤的 prompt 模板) | |
| `.moyun/custom-pipelines/` | 用户自定义管线目录 |
| `frontend/src/components/right-panel/PipelineEditor.vue` | 管线编辑标签页 |
| `frontend/src/composables/usePipeline.ts` | 管线管理 composable |
| `frontend/src/stores/pipeline.ts` | 管线状态管理 |

### 修改

| 文件 | 改动 |
|------|------|
| `frontend/src/components/layout/AppHeader.vue` | 工具栏精简为 5 按钮 |
| `frontend/src/components/right-panel/RightPanel.vue` | 新增「快捷」「管线编辑」Tab |
| `frontend/src/components/right-panel/PromptPanel.vue` | 改为「快捷」标签内容 |
| `frontend/src/components/editor/EditorToolbar.vue` | 移除多余按钮 |
| `backend/api/generate.py` | 接入 PipelineRunner |
| `backend/main.py` | 注册 pipeline 路由 |
| `frontend/src/router/index.ts` | 可能的路由更新 |
| `frontend/src/composables/useFileGeneration.ts` | 适配管线 SSE 事件 |
