# T5.2: Scene Plan 生成 API 最小版本测试报告

**执行日期**: 2026-06-08
**执行人**: Solo Agent

## 概要

本报告记录了 `POST /api/scene-plan/generate` 接口的实现与测试，该接口提供了 Scene Plan 生成功能。

### 总进度

**总进度**: 约 75% (从 74% 推进)

---

## API 设计

### 接口路径

`POST /api/scene-plan/generate`

### 请求格式

```json
{
  "project_id": "demo-novel",
  "target_file": "chapters/vol-01/ch-001/sec-001.md",
  "instruction": "请为当前场景生成结构化 Scene Plan",
  "dry_run": true
}
```

### 响应格式

```json
{
  "scene_plan": { /* ScenePlan 对象 */ },
  "valid": true,
  "errors": [],
  "warnings": [],
  "raw_output": "...",
  "source_summary": {
    "target_file": "chapters/vol-01/ch-001/sec-001.md",
    "used_story_state": false,
    "used_style_guide": false,
    "used_recent_context": false
  }
}
```

---

## 功能实现

### 1. 上下文读取

成功实现了以下上下文文件的安全读取：

| 文件 | 说明 | 可选 |
|------|------|------|
| target_file | 目标场景正文 | 否 |
| story_state.md | 故事状态 | 是 |
| style_guide.md | 风格指南 | 是 |
| recent_context.md | 最近上下文 | 是 |

所有读取操作均通过 `FileService._resolve_path` 进行安全检查，防止：
- 父目录遍历 (`../`)
- 敏感文件访问 (`.env`, `.git`)
- 绝对路径使用

### 2. LLM 生成

- 构建结构化 Prompt 要求只输出 JSON
- 支持从输出中提取 JSON（`json` 代码块或第一个 `{...}`）
- 强制设置安全字段：
  - `candidate_policy.require_candidate = true`
  - `candidate_policy.allow_direct_write = false`
  - `metadata.created_by = "llm"`

### 3. 校验集成

生成完成后自动调用 `validate_scene_plan()` 进行完整性检查。

### 4. 无副作用保证

- ❌ 不写正式正文文件
- ❌ 不创建 candidate
- ❌ 不执行 adopt
- ✅ 只做只读操作

---

## 测试覆盖

新增 `tests/test_scene_plan_generate_api.py`，包含：

| 测试项 | 状态 |
|--------|------|
| 成功生成有效 Scene Plan | ✅ |
| LLM 返回无效 JSON 处理 | ✅ |
| 校验失败场景处理 | ✅ |
| 危险路径安全检查 | ✅ |
| 上下文文件加载 (story_state, style_guide, recent_context) | ✅ |
| 无副作用验证（不写文件） | ✅ |

---

## 回归测试

执行以下现有测试，均通过：

```
tests/test_scene_plan_validate_api.py (7 tests)
tests/test_scene_plan_validator.py (14 tests)
```

---

## 安全性

### 已实现的安全措施

1. **路径安全**: 使用 `FileService._resolve_path` 检查所有输入路径
2. **强制 candidate 策略**: 即使 LLM 返回错误的策略，也会强制重写为安全配置
3. **无写操作**: 不执行任何文件写入
4. **异常处理**: LLM 调用和 JSON 解析失败都不会导致 500 错误

---

## 剩余问题与下一步

### 已知问题

- 暂时没有前端 UI
- 暂时没有将 Scene Plan 持久化的功能
- 未正式集成到 Professional dry-run 流程

### 下一步建议

1. 开发前端 Scene Plan 编辑器
2. 实现 Scene Plan 持久化
3. 集成到 Professional dry-run 流程作为可选步骤

---

## 验收问答

| 问题 | 回答 |
|------|------|
| 是否新增了 POST /api/scene-plan/generate？ | ✅ 是 |
| 是否读取 target_file/story_state/style_guide/recent_context？ | ✅ 是 |
| LLM 是否只生成 Scene Plan JSON，不写正文？ | ✅ 是 |
| 是否调用 validate_scene_plan？ | ✅ 是 |
| 非法 JSON 是否不会导致 500？ | ✅ 是 |
| validator 失败是否能返回 errors？ | ✅ 是 |
| 调用 generate API 后正文是否不变？ | ✅ 是 |
| 是否没有创建 candidate？ | ✅ 是 |
| 是否没有执行 adopt？ | ✅ 是 |
| 是否更新了 T5 报告？ | ✅ 是 |
| **是否可以把总进度从 74% 推进到约 75%？** | **✅ 是** |

---

## 文件变更

| 变更 | 文件 |
|------|------|
| 修改 | backend/api/scene_plan.py |
| 新增 | tests/test_scene_plan_generate_api.py |
| 新增 | docs/testing/t5-scene-plan-generate-api-2026-06.md |

---

**报告结论**: ✅ T5.2 已实现并测试通过，总进度约 75%
