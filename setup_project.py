
import os
import json
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 目录结构定义
DIRECTORIES = [
    # 后端
    "backend/api",
    "backend/core",
    "backend/tests",
    # 前端
    "frontend/css",
    "frontend/js",
    "frontend/assets",
    # 工作区
    "workspace/projects",
    # Prompt 模板
    "workspace/prompts/_backup",
    "workspace/prompts/templates",
    # generate 类
    "workspace/prompts/generate/title",
    "workspace/prompts/generate/blueprint",
    "workspace/prompts/generate/outline",
    "workspace/prompts/generate/worldbuilding",
    "workspace/prompts/generate/character",
    "workspace/prompts/generate/chapter/blocks",
    "workspace/prompts/generate/continuation",
    "workspace/prompts/generate/rewrite",
    "workspace/prompts/generate/dialogue",
    "workspace/prompts/generate/scene",
    # extract 类
    "workspace/prompts/extract/character",
    "workspace/prompts/extract/plot",
    "workspace/prompts/extract/scene",
    "workspace/prompts/extract/summary",
    # transform 类
    "workspace/prompts/transform/polish",
    "workspace/prompts/transform/translate",
    "workspace/prompts/transform/expand",
    "workspace/prompts/transform/shorten",
    # 测试
    "tests",
]

# 模板文件目录内容
TEMPLATE_FILES = {
    "style-guide.md": """# 文风指南

> 本文件用于定义小说的文风要求，指导 AI 生成符合期望的文字风格。

## 一、文风定位

**整体风格**：`{{ style_type }}`

## 二、示范文字

> 用户可以在这里粘贴自己喜欢的文字片段，作为文风参考。

```

```

## 三、写作风格要点

- 句子节奏：
- 描写密度：
- 语言特点：

## 四、写作禁忌

以下内容或表达方式**不建议使用**：
1. ~~过度使用"他/她想"、"他/她觉得"等内心独白~~
2. ~~连续使用超过3个形容词修饰同一名词~~

## 五、更新记录

| 日期 | 更新内容 | 操作人 |
|------|---------|--------|
""",
    "story-state.md": """# 故事全局状态

> 本文件记录小说的全局状态，包括主角当前状态、势力变化、伏笔追踪等。
> **每次生成新章节后需要更新此文件。**

## 一、故事基本信息

| 字段 | 内容 |
|------|------|
| 章节范围 | 第1章 |
| 故事进度 | 0% |
| 更新时间 | |

## 二、主角状态

- 当前境界/能力：
- 社会地位：
- 主要资源/道具：

## 三、势力关系

- 主角所属势力：
- 相关势力：

## 四、伏笔追踪

### 已埋设但未回收的伏笔

| 伏笔编号 | 伏笔内容 | 埋设章节 | 状态 |
|---------|---------|---------|------|
| | | | 未回收 |

### 已回收的伏笔

| 伏笔编号 | 伏笔内容 | 埋设章节 | 回收章节 |
|---------|---------|---------|---------|
""",
    "recent-context.md": """# 近期上下文摘要

> 本文件存储最近N章的摘要，用于在生成章节时提供近期情节上下文。

## 章节范围

- **起始章节**：第1章
- **结束章节**：第0章
- **总章节数**：0章

---

## 摘要列表

暂无章节

---

## 更新记录

| 日期 | 更新章节 | 更新内容 |
|------|---------|---------|
""",
    "ch-meta.md": """# 章节元数据

> 本文件记录章节的基本信息，用于生成章节时的上下文参考。

## 章节基本信息

| 字段 | 内容 |
|------|------|
| 章节编号 | ch-001 |
| 章节名称 | |
| 章节顺序 | 1 |

## 章节内容

### 本章目标

```

```

### 本章摘要

```

```

## 上下文信息

### 章节记忆

```

```

### 前文背景

```

```

## 故事状态

### 本章故事状态

```

```

## 伏笔管理

### 本章埋设的伏笔

| 伏笔ID | 伏笔内容 | 建议回收章节 |
|--------|---------|-------------|
| | | |

## 元数据

| 字段 | 内容 |
|------|------|
| 创建日期 | |
| 最后修改 | |
| 版本 | 1.0 |
| 状态 | draft |
""",
    "ch-meta.json": """{
  "chapter_id": "ch-001",
  "chapter_title": "",
  "chapter_index": 1,
  "volume_name": "第一卷",
  "created_date": "",
  "last_modified": "",
  "version": "1.0",
  "status": "draft",
  "template_type": "generate/chapter",
  "variables": {
    "chapter_goal": {
      "type": "textarea",
      "label": "本章目标",
      "required": true
    },
    "chapter_summary": {
      "type": "textarea",
      "label": "本章摘要"
    },
    "chapter_memory": {
      "type": "textarea",
      "label": "章节记忆"
    },
    "previous_context": {
      "type": "textarea",
      "label": "前文背景"
    },
    "story_state": {
      "type": "textarea",
      "label": "故事状态"
    },
    "pending_foreshadowing": {
      "type": "array",
      "label": "待回收伏笔"
    },
    "active_quests": {
      "type": "array",
      "label": "进行中支线"
    },
    "style_notes": {
      "type": "textarea",
      "label": "风格备注"
    }
  }
}
""",
    "user-feedback.json": """{
  "feedback_id": "",
  "chapter_id": "",
  "template_type": "",
  "feedback_date": "",
  "satisfaction_level": "",
  "issues": "",
  "issue_categories": [],
  "feedback_summary": ""
}
""",
    "revision-log.json": """{
  "revision_id": "",
  "chapter_id": "",
  "revision_date": "",
  "revision_type": "",
  "before_content": "",
  "after_content": "",
  "revision_description": "",
  "word_count_change": "",
  "revision_reasons": [],
  "quality_score": {
    "plot": 0,
    "style": 0,
    "logic": 0,
    "total": 0
  }
}
"""
}

# 后端基础文件内容
BACKEND_FILES = {
    "backend/__init__.py": "",
    "backend/api/__init__.py": "",
    "backend/core/__init__.py": "",
    "backend/tests/__init__.py": "",
}

# 配置文件内容
CONFIG_FILES = {
    "requirements.txt": """fastapi==0.110.0
uvicorn==0.29.0
gunicorn==21.2.0
litellm==1.35.0
aiofiles==23.2.1
tiktoken==0.5.0
pydantic-settings==2.2.0
watchdog==4.0.0
python-frontmatter==1.1.0
tenacity==8.2.0
rich==13.7.0
jinja2==3.1.0
httpx==0.27.0
pytest==8.0.0
pytest-asyncio==0.23.0
playwright==1.45.0
""",
    ".env.example": """# 墨韵配置文件
# 复制此文件为 .env 并填入实际配置

# LLM 配置
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4
LLM_API_BASE=https://api.openai.com/v1

# 工作区配置
WORKSPACE_PATH=./workspace

# 其他配置
DEBUG=true
""",
    ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 配置文件（包含敏感信息）
.env

# 工作区（用户数据）
workspace/

# 日志
*.log
""",
    "workspace/.config.json": """{
  "version": "1.0",
  "default_llm": "gpt-4",
  "theme": "dark-purple"
}
"""
}

def create_directories():
    """创建所有目录"""
    for dir_path in DIRECTORIES:
        full_path = BASE_DIR / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")

def create_template_files():
    """创建模板文件目录下的所有文件"""
    templates_dir = BASE_DIR / "workspace/prompts/templates"
    for filename, content in TEMPLATE_FILES.items():
        file_path = templates_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ 创建模板文件: _templates/{filename}")

def create_backend_files():
    """创建后端基础文件"""
    for file_path, content in BACKEND_FILES.items():
        full_path = BASE_DIR / file_path
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ 创建后端文件: {file_path}")

def create_config_files():
    """创建配置文件"""
    for file_path, content in CONFIG_FILES.items():
        full_path = BASE_DIR / file_path
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ 创建配置文件: {file_path}")

def main():
    print("=" * 50)
    print("墨韵项目初始化")
    print("=" * 50)

    create_directories()
    create_template_files()
    create_backend_files()
    create_config_files()

    print("\n" + "=" * 50)
    print("✓ 项目初始化完成！")
    print("=" * 50)
    print("\n新增文件说明：")
    print("- _templates/style-guide.md - 文风指南模板")
    print("- _templates/story-state.md - 故事状态模板")
    print("- _templates/recent-context.md - 近期上下文模板")
    print("- _templates/ch-meta.md - 章节元数据模板")
    print("- _templates/ch-meta.json - 章节元数据结构")
    print("- _templates/user-feedback.json - 用户反馈模板")
    print("- _templates/revision-log.json - 修改日志模板")
    print("\n下一步：")
    print("1. 复制 .env.example 为 .env 并填入配置")
    print("2. 创建 Python 虚拟环境: python -m venv venv")
    print("3. 安装依赖: pip install -r requirements.txt")
    print("4. 开始开发！")

if __name__ == "__main__":
    main()
