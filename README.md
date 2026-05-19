# 墨韵 Moyun

AI 小说创作助手，支持爽文模式和专业工作台。

## 功能特点

- **爽文模式**：开局卡、爽点卡、自动写下一节、质量摘要、故事引擎
- **专业模式**：文件树、Prompt、管线、工作流、快照、对比、备份、回收站
- **本地文件系统存储**：数据完全本地化，隐私安全
- **多模型支持**：支持 OpenAI / DeepSeek / Ollama 等模型

## 技术栈

- **Backend**: FastAPI, LiteLLM, Pydantic, Jinja2
- **Frontend**: Vue 3, TypeScript, Vite, Pinia, Ant Design Vue, CodeMirror 6

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

## 配置 LLM

复制 `.env.example` 为 `.env`，填入自己的 API Key：

```env
# OpenAI
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 或 DeepSeek
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

## 数据目录

- `prompts/`：系统 Prompt 模板（Git 追踪）
- `workspace/projects/`：用户项目数据（不追踪）
- `workspace/prompts/`：用户自定义 Prompt（不追踪）

## 开发命令

```bash
# 前端构建
cd frontend && npm run build

# 后端测试
python -m pytest backend/tests -q
```

## 项目结构

```
├── backend/          # FastAPI 后端
│   ├── api/          # REST API 端点
│   ├── core/         # 核心服务
│   ├── schemas/      # Pydantic 模型
│   └── tests/        # 单元测试
├── frontend/         # Vue 3 前端
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── composables/  # 组合式函数
│   │   ├── stores/       # Pinia 状态管理
│   │   └── views/        # 页面视图
│   └── tests/        # 端到端测试
├── prompts/          # 系统 Prompt 模板
└── workspace/        # 用户数据（gitignore）
```

## 注意事项

- **请勿提交** `.env`、`.config.json`、`workspace/` 到版本控制
- 首次启动会自动创建 `workspace/` 目录
- 未配置 LLM 时，生成功能会提示前往设置

## License

MIT License