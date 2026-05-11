# 墨韵 AI Prompt 模板说明文档

> 本文档用于 AI 读取并理解所有 Prompt 模板的结构，以便进行编程开发。
> **版本：1.3 | 更新日期：2026-05-11**

---

## 一、模板概述

### 1.1 模板目录结构

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
│   └── scene/           # 场景描写
├── extract/           # 提取类模板
│   ├── character/      # 角色提取
│   ├── plot/           # 情节提取
│   ├── scene/          # 场景提取
│   └── summary/        # 摘要提取
└── transform/          # 转换类模板
    ├── polish/         # 润色
    ├── translate/      # 翻译
    ├── expand/         # 扩写
    └── shorten/        # 缩写
```

### 1.2 每个模板的文件结构

每个模板包含两个文件：
- `meta.json` - 变量定义（供前端UI使用，含 source 字段）
- `main.md` - Prompt 内容（Jinja2 模板）

---

## 二、数据来源

### 2.1 文件系统来源

| 数据类型 | 文件路径 | 说明 |
|---------|---------|------|
| 项目设置 | `projects/{project_name}/meta.json` | genre, theme, tone, scale, pov 等 |
| 文风指南 | `projects/{project_name}/style-guide.md` | 文风定义（新增） |
| 故事状态 | `projects/{project_name}/story-state.md` | 全局状态（新增） |
| 近期上下文 | `projects/{project_name}/recent-context.md` | 最近5章摘要（新增） |
| 世界观设定 | `projects/{project_name}/materials/extracted/worldbuilding.md` | generate/worldbuilding 的输出 |
| 角色设定 | `projects/{project_name}/characters/*.json` | generate/character 的输出 |
| 章节元数据 | `projects/{project_name}/chapters/{vol}/ch-XXX/ch-meta.json` | goal, memory 等 |
| 章节正文 | `projects/{project_name}/chapters/{vol}/ch-XXX/ch-XXX.md` | 实际写作内容 |
| 章节摘要 | `projects/{project_name}/materials/extracted/summaries/*.md` | extract/summary 的输出 |
| 用户反馈 | `projects/{project_name}/chapters/{vol}/ch-XXX/feedback/*.json` | 反馈记录（新增） |
| 修改日志 | `projects/{project_name}/chapters/{vol}/ch-XXX/revision-log/*.json` | 修改记录（新增） |

### 2.2 模板引用映射（完整版）

| 模板变量 | 数据来源 | 类型 |
|---------|---------|------|
| `{{ genre }}` | project-meta.json | 字符串 |
| `{{ theme }}` | project-meta.json | 字符串 |
| `{{ tone }}` | project-meta.json | 字符串 |
| `{{ scale }}` | project-meta.json | 字符串 |
| `{{ pov }}` | project-meta.json | 字符串 |
| `{{ setting }}` | project-meta.json | 字符串（可选） |
| `{{ style_guide }}` | style-guide.md | 文本（新增） |
| `{{ story_state }}` | story-state.md | 文本（新增） |
| `{{ recent_context }}` | recent-context.md | 文本（新增） |
| `{{ worldbuilding }}` | extracted/worldbuilding.md | 文本 |
| `{{ characters }}` | characters/*.json | 文本 |
| `{{ chapter_name }}` | 章节文件名 | 字符串 |
| `{{ goal }}` | ch-meta.json | 字符串 |
| `{{ chapter_memory }}` | ch-meta.json | 字符串 |
| `{{ context }}` | 前一章节摘要 | 文本 |
| `{{ pending_foreshadowing }}` | story-state.md | 文本（新增） |
| `{{ text }}` | 章节正文 | 文本 |
| `{{ original_content }}` | 章节正文 | 文本 |
| `{{ current_content }}` | 章节正文 | 文本 |

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

**位置**：`projects/{project_name}/chapters/{vol}/ch-XXX/feedback/`

**用途**：记录用户对生成内容的反馈

**文件**：`{feedback_id}.json`

**内容**：
- 满意度评价
- 具体问题
- 问题分类
- 改进方向

---

### 3.5 修改日志 (revision-log/)

**位置**：`projects/{project_name}/chapters/{vol}/ch-XXX/revision-log/`

**用途**：记录每次修改详情

**文件**：`{revision_id}.json`

**内容**：
- 修改前/后内容
- 修改原因
- 质量评估

---

## 四、模板详细说明

### 4.1 generate/title - 书名+创意生成

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ genre }}` | project-meta.json | 题材 |
| `{{ theme }}` | project-meta.json | 核心主题 |
| `{{ tone }}` | project-meta.json | 作品基调 |
| `{{ setting }}` | project-meta.json | 故事背景（可选） |

**输出**：书名推荐（5个）+ 核心创意 + 作品定位

---

### 4.2 generate/blueprint - 整体蓝图生成

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ genre }}` | project-meta.json | 题材 |
| `{{ theme }}` | project-meta.json | 核心主题 |
| `{{ scale }}` | project-meta.json | 目标字数 |

**输出**：核心概念 + 世界观框架 + 人物 + 主线 + 主题 + 分卷 + 亮点

---

### 4.3 generate/outline - 大纲生成

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ genre }}` | project-meta.json | 题材 |
| `{{ theme }}` | project-meta.json | 核心主题 |
| `{{ protagonist }}` | extracted/characters/main.md | 主角设定 |
| `{{ scale }}` | project-meta.json | 目标规模 |

**输出**：三幕结构 + 人物弧光 + 高潮设计 + 伏笔 + 章节规划

---

### 4.4 generate/worldbuilding - 世界观设定

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ genre }}` | project-meta.json | 题材 |
| `{{ theme }}` | project-meta.json | 核心主题 |
| `{{ genre_type }}` | project-meta.json | 题材类型 |

**输出**：核心规则 + 力量体系/社会规则 + 地理/空间 + 文化设定

---

### 4.5 generate/character - 角色设定

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ genre }}` | project-meta.json | 题材 |
| `{{ theme }}` | project-meta.json | 核心主题 |
| `{{ character_info }}` | 用户输入或 ch-meta.json | 角色基本信息 |

**输出**：外在身份 + 性格内心 + 角色弧光 + 行为模式 + 关系 + 记忆点

---

### 4.6 generate/chapter - 章节撰写

**变量引用**（完整版）：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ chapter_name }}` | 章节文件名 | 章节名称 |
| `{{ goal }}` | ch-meta.json | 本章目标 |
| `{{ pov }}` | project-meta.json | 叙事视角 |
| `{{ chapter_memory }}` | ch-meta.json | 章节记忆（可选） |
| `{{ context }}` | 前一章节摘要 | 前文背景（可选） |
| `{{ worldbuilding }}` | extracted/worldbuilding.md | 世界观设定（可选） |
| `{{ characters }}` | characters/*.json | 角色设定（可选） |
| `{{ story_state }}` | story-state.md | 当前故事状态（新增） |
| `{{ style_guide }}` | style-guide.md | 文风指南（新增） |
| `{{ recent_context }}` | recent-context.md | 近期上下文（新增） |
| `{{ pending_foreshadowing }}` | story-state.md | 待回收伏笔（新增） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 章节正文 | 1800-2500字（不超过2000字） |
| 前文背景 | 不超过500字 |

**输出**：章节正文

---

### 4.7 generate/continuation - 续写

**变量引用**（完整版）：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ current_content }}` | 章节正文 | 当前内容 |
| `{{ chapter_memory }}` | ch-meta.json | 章节记忆（可选） |
| `{{ continuation_goal }}` | ch-meta.json | 续写目标（可选） |
| `{{ story_state }}` | story-state.md | 当前故事状态（新增） |
| `{{ style_guide }}` | style-guide.md | 文风指南（新增） |
| `{{ recent_context }}` | recent-context.md | 近期上下文（新增） |
| `{{ pending_foreshadowing }}` | story-state.md | 待回收伏笔（新增） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 前文章节 | 不超过2000字 |
| 续写 | 1500-2000字 |

**输出**：续写内容

---

### 4.8 generate/rewrite - 重写

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ original_content }}` | 章节正文 | 原始内容 |
| `{{ rewrite_goal }}` | ch-meta.json | 重写目标（可选） |
| `{{ keep_elements }}` | ch-meta.json | 需要保留的元素（可选） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 重写后 | 与原文相近 |

**输出**：重写后的完整内容

---

### 4.9 generate/dialogue - 对话生成

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ scene_context }}` | 用户输入或 ch-meta.json | 场景背景 |
| `{{ characters }}` | characters/*.json | 参与人物 |
| `{{ dialogue_goal }}` | ch-meta.json | 对话目标 |
| `{{ emotion_tone }}` | ch-meta.json | 情感基调 |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 对话 | 800-1500字 |

**输出**：对话内容

---

### 4.10 generate/scene - 场景描写

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ location }}` | 用户输入 | 场景地点 |
| `{{ time_period }}` | 用户输入 | 时间背景 |
| `{{ atmosphere }}` | 用户输入 | 氛围类型 |
| `{{ purpose }}` | ch-meta.json | 场景目的 |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 场景描写 | 500-1000字 |

**输出**：场景描写内容

---

### 4.11 extract/character - 角色提取

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ text }}` | 章节正文 | 原文 |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 提取结果 | 不超过500字 |

**输出**：角色基础信息 + 外貌 + 性格 + 关系 + 功能

---

### 4.12 extract/plot - 情节提取

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ text }}` | 章节正文 | 原文 |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 提取结果 | 不超过800字 |

**输出**：情节脉络 + 情节类型 + 发展线 + 关键转折

---

### 4.13 extract/scene - 场景提取

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ text }}` | 章节正文 | 原文 |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 提取结果 | 不超过500字 |

**输出**：场景基础信息 + 空间环境 + 场景元素 + 场景功能

---

### 4.14 extract/summary - 摘要提取

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ text }}` | 章节正文 | 原文 |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 摘要 | 150-300字 |

**输出**：一句话概述 + 详细摘要 + 关键信息 + 价值分析

---

### 4.15 transform/polish - 润色

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ text }}` | 章节正文 | 原文 |
| `{{ style }}` | ch-meta.json | 润色风格（可选） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 润色后 | 与原文相近 |

**输出**：润色后的内容

---

### 4.16 transform/translate - 翻译

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ text }}` | 章节正文 | 原文 |
| `{{ target_lang }}` | ch-meta.json | 目标语言 |
| `{{ context }}` | ch-meta.json | 翻译背景（可选） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过5000字 |
| 翻译后 | 与原文相近（允许10%浮动） |

**输出**：翻译后的内容

---

### 4.17 transform/expand - 扩写

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ content }}` | 章节正文 | 原文 |
| `{{ expand_type }}` | ch-meta.json | 扩写类型（可选） |
| `{{ target_length }}` | ch-meta.json | 目标长度（可选） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过2000字 |
| 扩写后 | 不超过原文的3倍 |

**输出**：扩写后的内容

---

### 4.18 transform/shorten - 缩写

**变量引用**：
| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ content }}` | 章节正文 | 原文 |
| `{{ shorten_type }}` | ch-meta.json | 缩写类型（可选） |
| `{{ target_length }}` | ch-meta.json | 目标长度（可选） |

**字数限制**：
| 项目 | 限制 |
|------|------|
| 原文 | 不超过3000字 |
| 缩写后 | 30%-70% |

**输出**：缩写后的内容

---

## 五、ch-meta.json 新增字段

### 完整字段列表

```json
{
  "chapter_id": "ch-001",
  "chapter_title": "章节标题",
  "chapter_index": 1,
  "volume_name": "第一卷",
  "created_date": "2026-05-11",
  "last_modified": "2026-05-11",
  "version": "1.0",
  "status": "draft",
  "template_type": "generate/chapter",
  "variables": {
    "chapter_goal": { "type": "textarea", "label": "本章目标" },
    "chapter_summary": { "type": "textarea", "label": "本章摘要" },
    "chapter_memory": { "type": "textarea", "label": "章节记忆" },
    "previous_context": { "type": "textarea", "label": "前文背景" },
    "story_state": { "type": "textarea", "label": "故事状态" },
    "foreshadowing": { "type": "array", "label": "埋设伏笔" },
    "pending_foreshadowing": { "type": "array", "label": "待回收伏笔" },
    "active_quests": { "type": "array", "label": "进行中支线" },
    "style_notes": { "type": "textarea", "label": "风格备注" }
  }
}
```

### 新增字段说明

| 字段 | 类型 | 说明 | 更新时机 |
|------|------|------|---------|
| `story_state` | string | 本章时的故事状态 | 章节创建时 |
| `pending_foreshadowing` | array | 待回收伏笔 | AI生成后自动添加 |
| `active_quests` | array | 进行中支线 | 章节创建时 |
| `style_notes` | string | 本章风格备注 | 用户编辑时 |

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

### 7.2 新增文件字数限制

| 文件类型 | 限制 | 备注 |
|---------|------|------|
| style-guide.md 示范文字 | ≤5000字 | 建议值 |
| story-state.md 伏笔列表 | ≤100条 | 建议值 |
| recent-context.md 章节数 | 最近5章 | 固定值 |

### 7.3 LLM 上下文限制

- **总字数限制**：1万字以内
- **超出处理**：系统自动截取最新部分
- **建议**：单个模板的输入内容应尽量精简

---

## 八、模板渲染流程

### 8.1 渲染步骤

1. **读取模板文件** - 加载 `main.md` 内容
2. **收集变量值** - 根据变量 source 从文件系统读取数据
3. **Jinja2 渲染** - 将变量值注入模板
4. **输出 Prompt** - 将渲染后的内容发送给 LLM

### 8.2 渲染示例

```python
# 伪代码示例
def render_prompt(template_name, context):
    # 1. 加载模板
    template = load_template(f"{template_name}/main.md")

    # 2. 收集变量（包含新增变量）
    variables = {
        "chapter_name": read_filename(context.chapter_id),
        "goal": read_ch_meta(context.chapter_id)["goal"],
        "pov": read_project_meta()["pov"],
        "style_guide": read_style_guide(context.project_id),
        "story_state": read_story_state(context.project_id),
        "recent_context": read_recent_context(context.project_id),
        "pending_foreshadowing": read_story_state(context.project_id)["pending_foreshadowing"],
        # ...
    }

    # 3. Jinja2 渲染
    prompt = template.render(**variables)

    # 4. 返回
    return prompt
```

---

## 九、注意事项

1. **变量 source 必须准确** - 确保数据来源文件存在
2. **字数限制要严格遵守** - 防止 LLM 上下文溢出
3. **可选变量要判断** - 使用 `{% if variable %}...{% endif %}`
4. **模板要保持简洁** - 避免过度复杂的 Jinja2 语法
5. **输出格式要统一** - 方便前端解析处理
6. **新增文件要及时更新** - style-guide.md、story-state.md 等需要维护

---

## 十、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0 | 2026-05-11 | 初始版本 |
| 1.1 | 2026-05-11 | 优化写作指导，增加灵活引导 |
| 1.2 | 2026-05-11 | 添加引用来源标注，完善字数限制 |
| 1.3 | 2026-05-11 | 新增 style-guide、story-state、recent-context 等质量保障文件 |
