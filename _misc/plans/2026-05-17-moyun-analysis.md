# 墨韵项目分析报告

> 分析日期：2026-05-17
> 基于：代码结构审查、文档查阅、Git 历史分析、测试覆盖评估

---

## 一、项目健康总览

墨韵是一个**架构设计优秀、功能实现接近完整**的项目。自 2026-05-10 启动以来，经历了 156 次提交的高强度开发，后端（~10,100 行 Python）和前端（85 个 Vue/TS 源文件）均已实现。目前的开发处于**从"功能交付"向"工程化"过渡**的阶段。

**整体评分：**

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ★★★★★ | Pipeline + Workflow 双层引擎、EventBus + SSE、分层清晰 |
| 功能完整度 | ★★★★☆ | 核心功能齐全，少量细节打磨中 |
| 测试覆盖 | ★★☆☆☆ | 后端单测良好，API 层和前端零测试 |
| 代码质量 | ★★★☆☆ | 类型系统好但存在泛化异常捕获、any 类型等问题 |
| 工程化 | ★★☆☆☆ | 缺乏 linting、CI/CD、提交规范执行不一致 |

---

## 二、已完成的核心能力

### 后端（22 个 API 路由 + 15 个核心服务）

- **Pipeline 引擎**（687 行）— YAML 定义的多步骤 LLM 调用链，支持 fallback、变量解析、SSE 流式输出
- **Workflow 引擎**（575 行）— 多 Pipeline 编排，支持 loop 循环、文件操作、条件分支
- **Prompt 系统**（模板引擎 + 版本管理 + 18 个模板文件）
- **LLM 服务**（LiteLLM 封装，流式 + 重试 + 并发限制）
- **文件服务**（异步 I/O，frontmatter 支持，目录树构建）
- **项目服务**（CRUD + 统计 + 向导流程）
- **质量审查**（评分 + 问题识别）
- **版本管理**（快照 + 对比 + 恢复）
- **事件系统**（EventBus + FileWatcher + SSE 桥接）
- **任务队列**（持久化到文件系统，支持恢复）
- **异常体系**（20+ 自定义异常类型）

### 前端（18 个 Store + 35 个组件 + 14 个 Composables）

- **AppHeader** — Logo、项目名编辑、LLM 状态、Thinking 开关、操作按钮
- **FileTree** — 递归文件树，支持拖拽到 Prompt 面板
- **MarkdownEditor** — CodeMirror 6，实时预览、语义高亮
- **ChatPanel** — 聊天消息、SSE 流式接收
- **RightPanel** — Prompt 编辑、Pipeline 编辑器、Workflow 面板、执行日志
- **12 个模态框** — 新建/打开项目、设置、搜索、对比、反馈、修订日志、批量生成、提取、质量审查、Token 计数、快速打开
- **Workflow Guide** — 全本小说创作向导，L1（半自动）/ L2（全自动）模式

### 文档体系

- `功能清单.md` — 完整的 M01-M09 + G01 模块定义（1184 行）
- `前端功能清单_完整版V2.md` — 逐功能 UI → Store → API 数据流
- `编码规范.md` — 1100+ 行编码规范
- `技术选型速查.md` — 技术栈 + 禁止引入清单
- `开发步骤.md` — 迭代循环开发模型 + 验收钩子
- `CONTEXT.md` — 领域术语定义
- `API契约.md`、`文件系统设计.md`、`后端架构设计.md`、`Prompt模板说明.md`

---

## 三、需要优先解决的问题

### P0 — 必须立即处理

**1. 103 个文件未提交**

自上次提交以来有 32,694 行新增 + 32,367 行删除的变更未提交。这是巨大的工作丢失风险。建议拆分为多个语义化提交（按功能模块或修改类型）。

**2. API 层零测试覆盖**

22 个路由模块没有任何 API 测试。虽然 `conftest.py` 已经提供了 TestClient fixture，但从未被使用。这是最关键的测试缺口 — API 是后端最"用户可见"的接口层。

**3. 根 tests/ 目录的测试不可用**

15 个 E2E 测试文件是 adhoc 脚本（不是 pytest），包含硬编码的 API Key、平台特定路径、240 秒轮询循环。需要通过 `pytest-playwright` 重写为可运行、可重复的测试。

### P1 — 应在本轮迭代完成

**4. SSE 双通道问题**

前端存在两套平行的 SSE 通信机制（EventSource + fetch ReadableStream），导致事件路由混乱、状态管理分散。建议统一为单一通路。

**5. 未引入 linting/格式化工具**

后端无 pylint/ruff，前端无 ESLint/Prettier。这会使代码风格随开发时间漂移。

**6. 6 个损坏目录需清理**

根目录下存在类似 `D:newmoyunworkspacepromptspipelinechat` 的伪路径目录，是之前 shell 操作失误产生的。

**7. 不安全的 API Key 存储**

测试文件中有明文 API Key（`sk-4ea45b...`），需要移到 `.env` 并加入 `.gitignore`。

### P2 — 应在下个迭代处理

**8. `except Exception` 泛化捕获**

`pipeline.py`、`quality_service.py` 等核心文件中使用了过于宽泛的异常捕获，会吞掉编程错误。

**9. 前端 `any` 类型**

多个关键接口中存在 `any` 类型标注，降低了 TypeScript 的价值。

**10. 任务队列持久化的可靠性**

虽然已有 `.task-queue/` 文件持久化，但需验证异常场景（磁盘满、并发写入）下的表现。

---

## 四、下一步工作建议（优先级排序）

### 🔴 第一步：稳定化基础（本周）

1. **提交当前所有变更** — 拆分为 3-5 个语义化提交
2. **清理损坏目录** — 删除 6 个伪路径目录
3. **移除硬编码 API Key** — 将 test 文件中的 key 移到 `.env`
4. **引入 linting 配置**：
   - 后端：添加 `.ruff.toml` 到 `backend/`
   - 前端：添加 `eslint.config.mjs` 到 `frontend/`
5. **清理前端 `console.log`** — 替换为条件化 debug 日志

### 🟡 第二步：测试体系建设（下周）

6. **API 层测试（最高回报）**：
   - 先覆盖 3 个核心路由：`projects.py`、`files.py`、`generate.py`
   - 使用已有的 `conftest.py` TestClient fixture
   - 每个路由至少测试正常路径、空状态、错误路径
7. **重写 E2E 测试**：
   - 将 `tests/` 下的 adhoc 脚本迁移到 `pytest-playwright`
   - 消除所有硬编码 sleep/poll，改用 Playwright 的 `waitFor` API
   - 添加 CI 可运行的 headless 模式

### 🟢 第三步：架构优化（两周内）

8. **统一 SSE 通路** — 选择并实施单一天地通信机制
9. **TypeScript strict mode** — 在 `tsconfig.json` 中逐步启用 `strict: true`
10. **前后端 conftest 增强** — 为 API 测试添加常用 fixture
11. **Pipeline 与 TaskExecutor 去重** — 统一为 PipelineRunner 作为唯一 LLM 执行入口

### 🔵 第四步：功能增强（迭代进行）

12. **增量提取模式完善** — 已有概念但实现不完整
13. **修改摘要（Diff Summary）UI 增强** — 当前实现是管线步骤，可提供更好的可视化
14. **离线模式** — 检测前端无法连接后端时的降级体验
15. **暗色/亮色主题扩展** — 现有 3 个主题可增加"水墨浅色"模式

---

## 五、建议的本轮工作清单

| # | 任务 | 优先级 | 预估时间 |
|---|------|--------|----------|
| 1 | 提交所有未提交变更（拆分提交） | P0 | 30 min |
| 2 | 清除损坏目录 + 移除明文 Key | P0 | 15 min |
| 3 | 配置后端 ruff + 前端 ESLint | P1 | 30 min |
| 4 | 为 projects.py / files.py / generate.py 写 API 测试 | P0 | 2 hr |
| 5 | 清理 console.log / print 语句 | P1 | 15 min |
| 6 | 启用 TypeScript `strict: true` | P2 | 1 hr |
| 7 | 统一 SSE 通路方案设计 | P1 | 1 hr |
| 8 | 更新 `frontend/README.md` 为项目特定说明 | P2 | 15 min |

---

## 六、项目预测

如果按照上述优先级执行：
- **1 周内**：项目工程化基础就绪，API 测试覆盖核心路由
- **2 周内**：SSE 架构统一，E2E 测试可运行
- **1 月内**：TypeScript strict 模式全开，linting 零告警，具备 CI 条件
- **持续迭代**：增量提取、离线模式等功能增强

项目目前处于"功能完备但需要工程化"的阶段，投入 1-2 周的系统性质量改进，将大幅提升后续开发效率和可维护性。
