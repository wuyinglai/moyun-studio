# 墨韵 (Moyun) - AI 小说创作助手

墨韵是一个 AI 辅助小说创作平台，提供从项目创建、大纲生成、章节写作到内容润色的全流程工具。

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env   # 填入 API Key
uvicorn backend.main:app --reload   # http://localhost:8000

# 前端
cd frontend
npm install
npm run dev            # http://localhost:5173
```

API 文档：启动后端后访问 http://localhost:8000/docs

## 项目结构

```
├── backend/          FastAPI 后端（api/ 路由层 + core/ 业务层）
├── frontend/         Vue 3 + TypeScript 前端
├── workspace/        用户数据目录（项目文件 + Prompt 模板）
│   ├── projects/     项目文件（每个项目一个文件夹）
│   └── prompts/      Prompt 模板（Jinja2 格式）
├── docs/             项目文档
├── _misc/            杂项（归档、脚本、技术方案）
└── tests/            测试
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | Python 3.10+ / FastAPI |
| LLM 调用 | LiteLLM（支持 OpenAI / Claude / DeepSeek / Ollama） |
| 前端框架 | Vue 3 + TypeScript + Vite + Pinia |
| UI 组件 | Ant Design Vue + CodeMirror 6 |
| 存储 | 本地文件系统（无数据库） |

## 核心概念

- **管线（Pipeline）**：多步骤 LLM 调用链，支持步骤级 fallback
- **工作流（Workflow）**：管线的编排层，支持 loop、变量传递、断点续跑
- **Prompt 模板**：Jinja2 格式的 LLM 提示词模板，支持 `@{path}` 文件引用
- **SSE 事件**：基于 EventSource 的实时通信，推送生成进度和状态变更

## 关键文档

- [功能清单](docs/功能清单.md) — 功能定义和执行逻辑
- [Prompt 模板说明](docs/Prompt模板说明.md) — 模板系统规范
- [后端架构设计](docs/后端架构设计.md) — 后端架构概览
- [文件系统设计](docs/文件系统设计.md) — 文件存储结构和命名规则
- [技术选型速查](docs/技术选型速查.md) — 技术栈和禁止清单
- [编码规范](docs/编码规范.md) — 代码编写规范
- [开发步骤](docs/开发步骤.md) — 迭代开发流程
