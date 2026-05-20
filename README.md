# 墨韵 Moyun

墨韵是一个本地优先的 AI 小说创作助手，面向中文长篇小说创作。项目同时支持两种使用方式：

- **爽文模式**：给普通用户的轻量创作页，围绕开局卡、爽点卡、流式生成、候选稿、质量摘要和故事引擎推进。
- **专业模式**：给进阶作者和开发者的工作台，提供文件树、Prompt、管线、工作流、变量、快照、对比和可配置执行流程。

当前产品方向是 **人机协同创作**：AI 负责生成、总结、审稿和候选改写；作者通过聊天、选择、确认、编辑来控制方向；工作流把 Prompt、人工节点、文件节点、记忆节点和质量节点串起来。

## 快速开始

### 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn backend.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

启动后访问前端开发服务器地址。后端 API 文档可访问 `/docs` 或 `/redoc`。

## 配置 LLM

复制 `.env.example` 为 `.env`，填入自己的 API Key：

```env
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

也可以配置 DeepSeek、Ollama 等兼容 LiteLLM 的模型。

## 技术栈

- **后端**：FastAPI, LiteLLM, aiofiles, Pydantic, Jinja2
- **前端**：Vue 3, TypeScript, Vite, Pinia, Vue Router, Ant Design Vue, CodeMirror 6
- **存储**：本地文件系统，无数据库
- **AI 调用**：通过 LiteLLM 统一接入

## 核心目录

```text
backend/       FastAPI 后端
frontend/      Vue 3 前端
prompts/       系统 Prompt 模板
tests/         E2E 与辅助测试脚本
docs/          产品、架构、规范和设计文档
_misc/plans/   迁移计划和阶段方案
workspace/     用户项目数据，不提交 Git
```

## 文档入口

先读这些文件，能最快理解项目：

- [AGENTS.md](AGENTS.md)：AI 协作规则、禁区、GitNexus 要求。
- [CONTEXT.md](CONTEXT.md)：领域术语。
- [docs/文档索引.md](docs/文档索引.md)：文档导航。
- [docs/产品架构-人机协同工作流.md](docs/产品架构-人机协同工作流.md)：新版产品架构。
- [docs/专业版节点化改造计划.md](docs/专业版节点化改造计划.md)：专业版后续改造方向。
- [docs/功能清单.md](docs/功能清单.md)：功能定义和执行逻辑。
- [docs/features/README.md](docs/features/README.md)：功能规格后续拆分入口。
- [docs/技术选型速查.md](docs/技术选型速查.md)：技术栈和禁止清单。
- [docs/编码规范.md](docs/编码规范.md)：编码规范。
- [docs/文件系统设计.md](docs/文件系统设计.md)：项目文件结构。
- [docs/api/README.md](docs/api/README.md)：API 契约后续拆分入口。

## 开发命令

```bash
# 前端构建
cd frontend
npm run build

# 后端测试
python -m pytest backend/tests -q

# 后端语法检查示例
python -m py_compile backend/api/lite.py backend/schemas/lite.py
```

## 重要约束

- 不要提交 `.env`、`.config.json`、`workspace/`。
- 不要修改 `_misc/archive/`，它是历史归档。
- 修改 `backend/` 或 `frontend/` 前，先读对应 README 或上下文文档。
- 代码修改后检查 [docs/技术选型速查.md](docs/技术选型速查.md) 的禁止清单。
- 涉及函数、类、方法修改时，按 `AGENTS.md` 的 GitNexus 要求先做影响分析。

## License

MIT License
