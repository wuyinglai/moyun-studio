# Phase T4.5 — Story State / Materials / 文件系统验收

## 1. 背景

上一阶段 T4.4 已完成 Workflow / Pipeline / Prompt 模块静态验收。本阶段验收专业版依赖的 Story State / Materials / 文件系统基础能力。只做静态验收和文档，不新增功能。

---

## 2. Story State Findings

✅ **Story State 模块存在且完整**

### 后端
- ✅ `backend/api/story_state.py` — 故事状态 API
- ✅ 端点：
  - `GET /api/story-state/{project_id}` — 获取故事全局状态
  - `POST /api/story-state/{project_id}` — 更新故事全局状态
- ✅ Schema：
  - `StoryStateContent` — 故事状态内容（主角状态、势力关系、伏笔、主线进度等）
  - `UpdateStoryStateRequest` — 更新请求
- ✅ 默认模板完整
- ✅ **不会自动更新**：需要用户显式调用 POST 接口

### 前端
- ✅ `frontend/src/stores/storyState.ts` — Story State Store

### 边界
- ✅ 不会自动覆盖 story-state.md
- ✅ 需要用户确认
- ✅ 遵循 AGENTS.md 规则：story-state 变更走用户确认

---

## 3. Materials Findings

✅ **Materials 模块存在且完整**

### 后端
- ✅ `backend/api/materials.py` — 素材提取 API
- ✅ 端点：
  - `GET /api/materials/{type}` — 获取提取结果列表
  - `GET /api/materials/{type}/{id}` — 获取提取结果详情
  - `POST /api/materials/{type}` — 创建提取结果（手动录入）
  - `POST /api/extract` — 提交提取任务（LLM自动提取）
  - `DELETE /api/materials/{type}/{id}` — 删除提取结果
- ✅ Schema：
  - `PlotItem` — 情节项
  - `SceneItem` — 场景项
  - `SummaryItem` — 摘要项
  - `WorldbuildingItem` — 世界观项
- ✅ **不会自动入库**：需要用户调用 POST 接口

---

## 4. Core Writing Files Findings

✅ **核心写作文件结构完整**

### 文件位置
- `story-engine.md` — 故事引擎
- `story-state.md` — 故事状态
- `style-guide.md` — 文风指南
- `recent-context.md` — 最近上下文
- `selected-card.md` — 选中的卡片

### 读取位置
- PromptEngine 支持 `@{file_path}` 引用
- Pipeline YAML 中定义读取路径
- StoryState API 管理 story-state.md

---

## 5. FileService Findings

✅ **FileService 存在且安全**

### 后端
- ✅ `backend/core/file_ops.py` — 文件操作服务
- ✅ 异步文件读写（aiofiles）
- ✅ frontmatter 解析和写入
- ✅ 目录管理
- ✅ 文件树构建

### 路径安全检查
- ✅ **禁止的路径段**：
  - `.env`
  - `.config.json`
  - `.git`
  - `node_modules`
  - `__pycache__`
- ✅ **禁止的路径前缀**：`..`, `/`, `\`
- ✅ **禁止的写入后缀**：`.py`, `.pyc`, `.sh`, `.bat`, `.exe`
- ✅ **禁止 `..` 穿越**
- ✅ **禁止绝对路径**
- ✅ **workspace 范围限制**

### 并发控制
- ✅ **expected_mtime 检查**：文件修改时间冲突检测
- ✅ **expected_hash 检查**：文件内容哈希冲突检测
- ✅ **FileConflictError 异常**

### 大小限制
- ✅ **最大文件大小**：5MB（默认）

---

## 6. Conflict Protection Findings

✅ **冲突保护完整**

### FileService
- ✅ `expected_mtime` — 期望的文件修改时间
- ✅ `expected_hash` — 期望的文件内容哈希
- ✅ `FileConflictError` — 冲突时抛出异常

### Candidate 机制
- ✅ adopt 前检查 base_hash / base_mtime
- ✅ adopt 后写 revision log

### API 层
- ✅ 前端保存文件必须携带 `expected_mtime` / `expected_hash`
- ✅ 处理 `FILE_CONFLICT` 错误

---

## 7. file.updated / SSE Findings

✅ **SSE 事件完整**

### 事件类型
- ✅ `EventTypes.FILE_UPDATED_NEW = "file.updated"`
- ✅ `EventTypes.CANDIDATE_CREATED = "candidate.created"`
- ✅ `EventTypes.CANDIDATE_ADOPTED = "candidate.adopted"`

### file.updated 契约（来自 `backend/tests/contracts/test_sse_contract.py`）
- ✅ **不包含 content**：测试确认 `assert "content" not in sse_dict`
- ✅ **必须包含**：
  - `type` = "file.updated"
  - `project_id`
  - `timestamp`
  - `payload.path`
  - `payload.size`
  - `payload.mtime`

### 前端监听
- ✅ `frontend/src/composables/useSSE.ts` — SSE 监听
- ✅ 15 秒心跳，45 秒超时自动重连

---

## 8. Candidate / Official Write Boundary

✅ **边界清晰且安全**

### 自动写入（需用户触发）
- ✅ Candidate adopt 后写入正式文件
- ✅ 需要 base_hash / base_mtime 验证
- ✅ 写入 revision log

### 禁止自动写入
- ✅ 正式 scene 文件
- ✅ story-state.md
- ✅ style-guide.md
- ✅ materials/

### 安全机制
- ✅ `output_mode='candidate'` 默认
- ✅ 必须用户 adopt 才能覆盖正文
- ✅ 不静默覆盖

---

## 9. Lite Impact

✅ **Lite 完全独立，不受影响**

- ✅ Lite 使用独立 store
- ✅ Lite 不依赖 Professional FileService
- ✅ T4.5 验收不修改 Lite

---

## 10. Missing or Uncertain Areas

- ⚠️ Lite 的 recent-context / style-guide 读取机制未详细检查
- ⚠️ Materials API 的权限控制未详细验证

---

## 11. 验收结论

⚠️ **静态验收通过，核心能力完整且安全**

✅ 通过项：
- ✅ Story State 模块完整
- ✅ Materials 模块完整
- ✅ FileService 安全机制完整
- ✅ 路径安全检查完整
- ✅ 冲突保护完整
- ✅ SSE 事件契约清晰
- ✅ Candidate / Official Write Boundary 清晰
- ✅ 不自动覆盖正文
- ✅ 不自动入库
- ✅ Lite 不受影响

**文档完成日期：2026-06-05
