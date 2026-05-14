# Prompt 体系重构 + 管线引擎 实施计划

**Goal:** 将墨韵从单个 Prompt 升级为管线驱动的多步骤生成系统，并重构前端工具栏和右侧面板

**Architecture:** 新增 `core/pipeline.py` 管线引擎，YAML 定义管线步骤，每步独立 Prompt 模板。前端工具栏按钮映射为管线，右侧面板新增「快捷」「管线编辑」Tab。中间步骤静默运行，最终结果流式输出。

**Tech Stack:** Python 3.10+, FastAPI, YAML, Vue 3, TypeScript, Pinia

## 阶段摘要

| 阶段 | 内容 | 关键产出 |
|------|------|----------|
| Stage 1 | 管线引擎核心 | PipelineRunner + PipelineDef 数据模型 |
| Stage 2 | YAML 定义 + Prompt 模板 | 5 条管线 (polish/generate/rewrite/chat/extract) + 24+ 步骤模板 |
| Stage 3 | 管线 API | POST run(SSE) / GET list / GET detail / PUT save / POST custom |
| Stage 4 | 前端状态层 | pipeline store + rightPanel store 更新 |
| Stage 5 | 右侧面板改造 | 快捷 Tab ⚡ + 管线编辑 Tab 🔧 |
| Stage 6 | 工具栏精简 | 5 按钮：润色/生成/重写/提取/自定义 |
| Stage 7 | 集成与清理 | generate/chat 端点改用 pipeline + 清理旧代码 |

## Stage 1: Pipeline 数据模型 + Runner 引擎

1. `backend/schemas/pipeline.py` — PipelineDef/PipelineStepDef/RunRequest
2. `backend/core/pipeline.py` — PipelineRunner 类 (load/run/list/detail/save)
3. 执行流程：load YAML → 逐步骤渲染 prompt → LLM 调用 → fallback → 写文件 → SSE 事件

## Stage 2: 管线定义

五条 YAML 管线定义在 `workspace/prompts/pipeline/`：
- polish: depai → prose → logic → rhythm
- generate: context → outline → draft → depai → logic → rhythm  
- rewrite: diagnose → draft → depai → logic → rhythm
- chat: understand → draft → validate
- extract: worldbuilding → characters → plots → summary

每步骤对应一个 `{step_id}.md` Prompt 模板文件，使用 Jinja2 + @{} 引用。

## Stage 3: 前端

- pipeline store: 加载管线列表/详情，管理选中状态和步骤索引
- 快捷面板: 管线下拉 + 步骤选择 + Prompt 编辑 + 运行
- 管线编辑面板: 步骤管理 + Prompt 编辑器 + 新建/保存
- 工具栏: 精简为 5 个按钮直接映射管线
