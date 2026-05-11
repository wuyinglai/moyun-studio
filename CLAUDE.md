# 墨韵 (Moyun) - AI小说创作助手

墨韵是一个AI辅助小说创作平台，帮助作者管理小说项目的结构、角色、情节，并使用AI生成高质量的小说内容。

## 项目结构

- `backend/` - Python后端（FastAPI）
- `docs/` - 项目文档
- `workspace/` - 用户工作区（包含prompts模板）
- `setup_project.py` - 项目初始化脚本

## 技术栈

- **后端**: Python 3.10+, FastAPI, LiteLLM, aiofiles
- **前端**: HTML/CSS/JavaScript (CDN引入)
- **AI**: OpenAI GPT-4 / Claude / Ollama (通过LiteLLM统一调用)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动开发服务器
uvicorn backend.main:app --reload
```

## Agent skills

### Issue tracker

本地 markdown 文件追踪，位于 `.scratch/` 目录。见 `docs/agents/issue-tracker.md`。

### Triage labels

使用标准的5种状态标签：needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix。见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文布局，CONTEXT.md 在根目录，ADR 在 `docs/adr/`。见 `docs/agents/domain.md`。
