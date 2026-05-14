# 墨韵 AI Prompt 模板说明文档

> 本文档用于 AI 读取并理解所有 Prompt 模板的结构，以便进行编程开发。
> **版本：2.1 | 更新日期：2026-05-14**

---

## 一、模板系统概述

墨韵有两套 Prompt 模板系统：

1. **管线系统（pipeline/）** — 当前主要 LLM 生成路径，YAML 定义多步骤流程
2. **旧模板系统（generate/extract/transform/）** — 直接调用 LLM 的回退模式

---

### 1.1 管线模板目录结构

```
workspace/prompts/pipeline/
├── generate.yaml           ← 续写管线定义（6步：context → outline → draft → depai → logic → rhythm）
├── rewrite.yaml            ← 重写管线定义（5步：diagnose → draft → depai → logic → rhythm）
├── chat.yaml               ← 聊天管线定义（3步：understand → draft → validate）
├── extract.yaml            ← 提取管线定义（4步：世界观/角色/情节/摘要）
├── polish.yaml             ← 润色管线定义（4步：去AI味/文笔/逻辑/节奏）
├── generate/               ← 续写管线步骤 prompt
│   ├── context.md
│   ├── outline.md
│   ├── draft.md
│   ├── depai.md
│   ├── logic.md
│   └── rhythm.md
├── rewrite/
│   ├── diagnose.md
│   ├── draft.md
│   ├── depai.md
│   ├── logic.md
│   └── rhythm.md
├── chat/
│   ├── understand.md
│   ├── draft.md
│   └── validate.md
├── extract/
│   ├── worldbuilding.md
│   ├── characters.md
│   ├── plots.md
│   └── summary.md
├── polish/
│   ├── depai.md
│   ├── prose.md
│   ├── logic.md
│   └── rhythm.md
```

**管线 YAML 定义示例**（generate.yaml）：
```yaml
name: generate
label: 续写
steps:
  - id: analysis
    label: 分析现状
    prompt: pipeline/generate/analysis
  - id: style
    label: 风格对齐
    prompt: pipeline/generate/style
    fallback: analysis
  - id: write
    label: 续写
    prompt: pipeline/generate/write
    fallback: style
```

### 1.2 旧模板目录结构（回退模式）

```
workspace/prompts/
├── generate/           # 生成类模板
│   ├── title/          # 书名+创意生成
│   ├── blueprint/      # 整体蓝图生成
│   ├── outline/        # 大纲生成
│   ├── worldbuilding/  # 世界观设定
│   ├── character/      # 角色设定
│   ├── chapter/        # 章节撰写
│   ├── continuation/   # 续写
│   ├── rewrite/        # 重写
│   ├── dialogue/       # 对话生成
│   └── scene/          # 场景描写
├── extract/           # 提取类模板
│   ├── character/     # 角色提取
│   ├── plot/          # 情节提取
│   ├── scene/         # 场景提取
│   └── summary/       # 摘要提取
└── transform/         # 转换类模板
    ├── polish/        # 润色
    ├── translate/     # 翻译
    ├── expand/        # 扩写
    └── shorten/       # 缩写
```

### 1.3 每个模板的文件结构

旧模板每个包含两个文件：
- `meta.json` — 变量定义（供前端UI使用）
- `main.md` — Prompt 内容（Jinja2 模板）

---

## 二、数据来源

### 2.1 文件系统来源

| 数据类型 | 文件路径 | 说明 |
|---------|---------|------|
| 项目设置 | `projects/{project_name}/meta.json` | genre, theme, tone, scale, pov 等 |
| 文风指南 | `projects/{project_name}/style-guide.md` | 文风定义 |
| 故事状态 | `projects/{project_name}/story-state.md` | 全局状态 |
| 近期上下文 | `projects/{project_name}/recent-context.md` | 最近5章摘要 |
| 世界观设定 | `projects/{project_name}/materials/extracted/worldbuilding.md` | 世界观 |
| 角色设定 | `projects/{project_name}/characters/*.json` | 角色档案 |
| 章节元数据 | `projects/{project_name}/chapters/{vol}/ch-{xxx}/ch-meta.json` | goal, memory 等 |
| 节正文 | `projects/{project_name}/chapters/{vol}/ch-{xxx}/sec-{序号}.md` | 实际写作内容 |
| 章节摘要 | `projects/{project_name}/materials/extracted/summaries/*.md` | 摘要 |
| 用户反馈 | `projects/{project_name}/chapters/{vol}/ch-{xxx}/feedback/*.json` | 反馈记录 |
| 修改日志 | `projects/{project_name}/chapters/{vol}/ch-{xxx}/revision-log/*.json` | 修改记录 |

### 2.2 管线系统变量

PipelineRunner 自动加载以下变量：

| 模板变量 | 数据来源 | 类型 |
|---------|---------|------|
| `{{ style_guide }}` | style-guide.md | 文本 |
| `{{ story_state }}` | story-state.md | 文本 |
| `{{ recent_context }}` | recent-context.md | 文本 |
| `{{ outline }}` | outline.md | 文本 |
| `{{ pending_foreshadowing }}` | ch-meta.json（pending_foreshadowing 字段） | JSON数组 |
| `{{ active_quests }}` | ch-meta.json（active_quests 字段） | JSON数组 |
| `{{ file_content }}` | 目标文件内容 | 文本 |
| `{{ file_path }}` | 目标文件路径 | 字符串 |
| `{{ project_id }}` | 项目ID | 字符串 |
| `{{ user_input }}` | 用户输入 | 文本 |
| `{{ previous_output }}` | 前序步骤输出（仅 fallback 启用时可用） | 文本 |

---

## 三、新增文件说明

### 3.1 文风指南 (style-guide.md)

**位置**：`projects/{project_name}/style-guide.md`

**用途**：定义小说的文风要求

**内容**：
- 文风定位（简洁/华丽/古风等）
- 示范文字（用户上传）
- 写作风格要点
- 写作禁忌
- 题材特点
- 角色说话风格

**更新**：用户可随时编辑

---

### 3.2 故事全局状态 (story-state.md)

**位置**：`projects/{project_name}/story-state.md`

**用途**：记录小说全局状态

**内容**：
- 主角当前状态（能力/境界/资源）
- 势力关系
- 伏笔追踪（已埋设/已回收）
- 主线/支线进度
- 关键人物关系
- 待处理事项
- 最近5章摘要

**更新**：每次生成章节后自动更新

---

### 3.3 近期上下文 (recent-context.md)

**位置**：`projects/{project_name}/recent-context.md`

**用途**：存储最近5章摘要

**内容**：
- 最近5章的详细摘要
- 人物状态速查
- 伏笔状态速查
- 势力关系速查

**更新**：每次生成章节后自动追加/更新

---

### 3.4 用户反馈 (feedback/)

**位置**：`projects/{project_name}/chapters/{vol}/ch-{xxx}/feedback/`

**文件结构**：
```json
{
  "id": "fb-001",
  "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
  "type": "suggestion",
  "content": "反馈内容",
  "location": "第3段",
  "satisfaction_level": 3,
  "resolved": false,
  "created_at": "2026-05-11T10:00:00",
  "resolved_at": null
}
```

---

### 3.5 修改日志 (revision-log/)

**位置**：`projects/{project_name}/chapters/{vol}/ch-{xxx}/revision-log/`

**文件结构**：
```json
{
  "id": "rev-001",
  "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
  "revision_type": "ai_rewrite",
  "description": "管线生成: sec-001.md",
  "word_count_before": 1500,
  "word_count_after": 1800,
  "diff": "@@ -1,5 +1,5 @@...",
  "created_at": "2026-05-11T10:00:00"
}
```

---

## 四、ch-meta.json 字段说明

### 完整字段列表

```json
{
  "chapter_number": 1,
  "title": "第一章：意外觉醒",
  "section_count": 4,
  "word_count": 0,
  "status": "draft",
  "memory": "",
  "story_state": "",
  "pending_foreshadowing": [],
  "active_quests": [],
  "created_at": "2026-05-11T10:00:00"
}
```

### 字段说明

| 字段 | 类型 | 说明 | 更新时机 |
|------|------|------|---------|
| `chapter_number` | int | 章节序号（全局连续） | 创建时 |
| `title` | string | 章节标题 | 创建时 |
| `section_count` | int | 本章节数 | 创建时 |
| `word_count` | int | 字数 | 动态更新 |
| `status` | string | draft/editing/completed/discarded | 创建时 |
| `memory` | string | 章节记忆 | 初始为空 |
| `story_state` | string | 本章时的故事状态 | 创建时 |
| `pending_foreshadowing` | array | 待回收伏笔 | 创建时 |
| `active_quests` | array | 进行中支线 | 创建时 |
| `created_at` | string | 创建时间 | 创建时 |

---

## 五、管线渲染流程

### 5.1 渲染步骤

1. **加载管线 YAML** — 读取 `pipeline/{name}.yaml` 获取步骤定义
2. **加载系统变量** — 读取 style-guide.md、story-state.md、recent-context.md、outline.md
3. **加载章节变量** — 读取 ch-meta.json 的 pending_foreshadowing、active_quests
4. **对每步**：
   a. 渲染步骤 prompt 模板（Jinja2）
   b. 解析 `@{path}` 引用为文件内容（见 §5.3）
   c. 调用 LLM
   d. 失败时自动 fallback
5. **保存输出** — 根据 output_mode 写入目标文件
6. **自动更新** — 更新 story-state.md、recent-context.md，创建 revision-log

### 5.2 变量加载顺序

PipelineRunner 在执行管线时按以下顺序加载变量（后者覆盖前者）：

1. **系统变量**：style_guide / story_state / recent_context / outline
2. **章节变量**：pending_foreshadowing / active_quests（来自 ch-meta.json）
3. **步骤变量**：file_content / file_path / project_id / user_input
4. **额外变量**：extra_vars（来自 API 请求）
5. **前序步骤输出**：previous_output（当 fallback 启用时）

### 5.3 @{path} 引用机制

PromptEngine 支持 `@{path}` 语法在渲染后的 prompt 中引用项目文件内容。

**语法**：
- `@{path/to/file.md}` — 将目标文件内容嵌入 prompt
- 相对路径相对于项目根目录（`projects/{project_id}/`）

**解析流程**：
1. Jinja2 模板渲染完成后，PipelineRunner._resolve_references() 扫描全文匹配 @{...} 模式
2. 对每个匹配的路径，通过 FileService 异步读取文件内容
3. 将 `@{path}` 替换为实际文件内容
4. 若文件不存在，替换为空字符串并记录警告事件

**示例**：
```
请参考以下设定进行写作：
@{materials/extracted/worldbuilding.md}
```

### 5.4 渲染示例

```python
# PipelineRunner 伪代码
async def run(pipeline_name, project_id, target_file, user_input):
    # 1. 加载管线定义
    pipeline = load_pipeline(pipeline_name)

    # 2. 收集变量
    system_vars = await load_system_variables(project_id)
    chapter_vars = await load_chapter_vars(project_id, target_file)

    for step in pipeline.steps:
        # 3. 渲染模板
        prompt = render_prompt(step.prompt, {
            **system_vars,
            **chapter_vars,
            "file_content": file_content,
            "user_input": user_input,
        })

        # 4. 解析 @{path} 引用
        prompt = await resolve_references(prompt, project_id)

        # 5. 调用 LLM
        output = await llm.complete(prompt)

        # 6. 失败回退
        if error and step.fallback:
            output = step_outputs[step.fallback]
```

---

## 六、模板变量类型

### 6.1 meta.json 变量类型定义

```json
{
  "variables": {
    "variable_name": {
      "type": "text|textarea|select",
      "label": "显示名称",
      "source": "数据来源",
      "placeholder": "占位提示",
      "options": ["选项1", "选项2"],
      "default": "默认值",
      "required": true|false
    }
  }
}
```

### 6.2 变量类型说明

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `text` | 单行文本 | 名称、标题等简短内容 |
| `textarea` | 多行文本 | 长文本输入或引用 |
| `select` | 下拉选择 | 固定选项（如视角、语言等） |
| `number` | 数字 | 字数、章节数 |
| `switch` | 开关 | 是否开启某功能 |
| `file` | 文件引用 | 关联已有文件 |

---

## 七、字数限制汇总

### 7.1 各文件类型字数限制

| 文件类型 | 输入限制 | 输出限制 | 备注 |
|---------|---------|---------|------|
| 章节正文 | - | 1800-2500字（≤2000） | 核心基准 |
| 续写 | 前文≤2000字 | 1500-2000字 | 与章节相当 |
| 重写 | ≤5000字 | 与原文相近 | 过长分段处理 |
| 润色 | ≤5000字 | 与原文相近 | 改动适度 |
| 翻译 | ≤5000字 | 原文±10% | 允许语言差异 |
| 扩写 | ≤2000字 | ≤原文3倍 | 选核心段落 |
| 缩写 | ≤3000字 | 30%-70% | 根据类型调整 |
| 摘要 | ≤5000字 | 150-300字 | 分段摘要合并 |
| 角色提取 | ≤5000字 | ≤500字 | 精炼摘要 |
| 情节提取 | ≤5000字 | ≤800字 | 脉络清晰 |
| 场景提取 | ≤5000字 | ≤500字 | 精炼摘要 |

### 7.2 LLM 上下文限制

- **Prompt 上限**：120K tokens（自动检测，超限时发出警告事件）
- **超出处理**：系统发出 warning 事件，但继续执行
- **建议**：单个模板的输入内容应尽量精简

---

## 八、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-05-11 | 初始版本 |
| v1.1 | 2026-05-11 | 优化写作指导，增加灵活引导 |
| v1.2 | 2026-05-11 | 添加引用来源标注，完善字数限制 |
| v1.3 | 2026-05-11 | 新增 style-guide、story-state、recent-context |
| v2.0 | 2026-05-14 | 新增管线系统说明，修正 ch-meta 字段和变量来源 |
| v2.1 | 2026-05-14 | 新增变量加载顺序、@{path}引用机制，修正章节编号 |
| v2.2 | 2026-05-14 | 补全 extract/polish 管线（共5管线），修正 @{path} 引用解析方法名 |
| v2.3 | 2026-05-14 | 工作流引擎的变量解析语法见 [工作流引擎设计.md](工作流引擎设计.md#三变量解析) |
