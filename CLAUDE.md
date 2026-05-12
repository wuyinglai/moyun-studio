# 墨韵 (Moyun) - AI小说创作助手

墨韵是一个AI辅助小说创作平台，帮助作者管理小说项目的结构、角色、情节，并使用AI生成高质量的小说内容。

## 核心目录（AI 主要工作区）

- `backend/` — FastAPI 后端（核心，频繁修改）
- `frontend/` — Vue3 + TypeScript 前端（核心，频繁修改）
- `tests/` — 测试脚本（AI 写测试时用到）

## 辅助目录（AI 一般不需修改）

- `docs/` — 项目文档，参考用，非代码
- `_misc/` — 杂项归档和工具脚本，见下方说明

`_misc/` 子目录说明：
- `_misc/archive/` — 历史归档文件（截图、原型、备份），**禁止修改**
- `_misc/scripts/` — 工具脚本（初始化、文档生成等），按需使用

## 禁止规则

- **禁止修改 `workspace/` 目录**（用户数据）
- **禁止修改 `_misc/archive/` 目录**（归档文件）
- **禁止修改 `.env` 文件**（敏感配置，除非用户明确要求）
- **修改 `backend/` 或 `frontend/` 前，必须先读对应目录下的 README 或上下文**
- **不要猜测文件路径，所有路径必须基于本文件声明的目录结构**

## 技术栈

- **后端**: Python 3.10+, FastAPI, LiteLLM, aiofiles, Pydantic
- **前端**: Vue 3, TypeScript, Vite, Pinia, Vue Router
- **AI**: OpenAI GPT-4 / Claude / 本地模型（通过 LiteLLM 统一调用）

## 快速开始

```bash
# 后端启动
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # 填入 API Key
uvicorn backend.main:app --reload

# 前端启动
cd frontend
npm install
npm run dev
```

## Agent skills

### Issue tracker

本地 markdown 文件追踪，位于 `_misc/archive/scratch/` 目录。见 `docs/agents/issue-tracker.md`。

### Triage labels

使用标准的5种状态标签：needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix。见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文布局，CONTEXT.md 在根目录，ADR 在 `docs/adr/`。见 `docs/agents/domain.md`。
