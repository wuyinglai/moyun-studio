# T5.2: Scene Plan 生成 API 最小版本测试报告

**执行日期**: 2026-06-08
**执行人**: Solo Agent

## 概要

本报告记录了 `POST /api/scene-plan/generate` 接口的实现与测试，该接口提供了 Scene Plan 生成功能。

### 总进度

**总进度**: 约 75% (从 74% 推进)

---

## T5.2.2 回归补票

### 执行完整回归测试

所有要求的测试均已执行：

| 测试项 | 结果 | 数量 |
|--------|------|------|
| tests/test_scene_plan_generate_api.py | ✅ 通过 | 8 |
| tests/test_scene_plan_validate_api.py | ✅ 通过 | 7 |
| tests/test_scene_plan_validator.py | ✅ 通过 | 14 |
| tests/test_scene_plan_pipeline_integration.py | ✅ 通过 | 5 |
| tests/test_llm_reasoning_detection.py | ✅ 通过 | 7 |
| tests/test_professional_regression_smoke.py | ✅ 通过 | - |
| frontend build | ✅ 通过 | - |
| git diff --check | ✅ 通过 (仅有 CRLF 警告) | - |

### API Smoke 验证

验证了以下功能点：

1. ✅ raw_output 默认返回 null，保护用户内容安全
2. ✅ include_raw_output=true 时，raw_output 正常返回
3. ✅ 非法 JSON 不导致 500 错误，返回 valid=false 和 errors
4. ✅ validator 失败时正常返回 errors
5. ✅ 无副作用验证：
   - ✅ 正文文件没有被修改（hash 和 mtime 保持不变）
   - ✅ 没有创建任何 candidate
   - ✅ 没有执行 adopt

### 总结

- 所有要求的回归测试均通过
- 前端构建通过
- API smoke 验证通过
- 无副作用保证验证通过
- 可以安全进入 T5.3

---

## T5.2.1 收口修正

### 修正内容

1. **raw_output 安全修正**
   - 新增 `include_raw_output: bool = false` 字段到请求
   - 默认不返回 raw_output，保护用户内容安全
   - 仅在 `include_raw_output=true` 时返回 raw_output

2. **路径验证公开方法**
   - 在 `FileService` 中新增公开方法 `validate_path()`
   - API 层不再直接调用私有方法 `_resolve_path()`
   - 内部仍使用 `_resolve_path()`，但 API 层使用公开接口

### API 更新

#### 请求格式（更新）

```json
{
  "project_id": "demo-novel",
  "target_file": "chapters/vol-01/ch-001/sec-001.md",
  "instruction": "请为当前场景生成结构化 Scene Plan",
  "dry_run": true,
  "include_raw_output": false  // 新增：默认不返回 raw_output
}
```

#### 响应格式（更新）

```json
{
  "scene_plan": { /* ScenePlan 对象 */ },
  "valid": true,
  "errors": [],
  "warnings": [],
  "raw_output": null,  // 默认不返回
  "source_summary": {
    "target_file": "chapters/vol-01/ch-001/sec-001.md",
    "used_story_state": false,
    "used_style_guide": false,
    "used_recent_context": false
  }
}
```

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
  "dry_run": true,
  "include_raw_output": false
}
```

### 响应格式

```json
{
  "scene_plan": { /* ScenePlan 对象 */ },
  "valid": true,
  "errors": [],
  "warnings": [],
  "raw_output": null,  // 默认 null，include_raw_output=true 时返回
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

所有读取操作均通过 `FileService.validate_path()` 进行安全检查（公开方法），防止：
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
| raw_output 默认不返回 | ✅ |
| include_raw_output=true 时返回 raw_output | ✅ |
| LLM 返回无效 JSON 处理 | ✅ |
| 校验失败场景处理 | ✅ |
| 危险路径安全检查 | ✅ |
| 上下文文件加载 | ✅ |
| 无副作用验证（不写文件） | ✅ |

---

## 回归测试

执行以下现有测试，均通过：

```
tests/test_scene_plan_generate_api.py (8 tests)
tests/test_scene_plan_validate_api.py (7 tests)
tests/test_scene_plan_validator.py (14 tests)
```

---

## 安全性

### 已实现的安全措施

1. **路径安全**: 使用 `FileService.validate_path()` 公开方法检查所有输入路径
2. **raw_output 保护**: 默认不返回 raw_output，防止用户内容泄露
3. **强制 candidate 策略**: 即使 LLM 返回错误的策略，也会强制重写为安全配置
4. **无写操作**: 不执行任何文件写入
5. **异常处理**: LLM 调用和 JSON 解析失败都不会导致 500 错误

---

## 技术债

### 已解决

- ~~直接调用 `_resolve_path()` 私有方法~~ → 已通过新增 `validate_path()` 公开方法解决

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
| **是否可以把总进度从 74.7% 推进到 75%？** | **✅ 是** |

---

## T5.2.2 最终验收

| 问题 | 回答 |
|------|------|
| tests/test_scene_plan_generate_api.py 是否已实际运行？ | ✅ 是，8 tests all passed |
| tests/test_scene_plan_pipeline_integration.py 是否已通过？ | ✅ 是，5 tests all passed |
| tests/test_llm_reasoning_detection.py 是否已通过？ | ✅ 是，7 tests all passed |
| tests/test_professional_regression_smoke.py 是否已通过？ | ✅ 是，通过 |
| frontend build 是否已通过？ | ✅ 是，vue-tsc -b && vite build 通过 |
| git diff --check 是否已通过？ | ✅ 是，仅有 CRLF 警告 |
| generate API 是否默认不返回 raw_output？ | ✅ 是，默认 null |
| generate API 是否不写正文、不创建 candidate、不 adopt？ | ✅ 是，无副作用 |
| **是否可以进入 T5.3？** | **✅ 是** |

---

## T5.2.1 最终验收

| 问题 | 回答 |
|------|------|
| tests/test_scene_plan_generate_api.py 是否已实际运行？ | ✅ 是，8 tests all passed |
| raw_output 是否默认不返回？ | ✅ 是，默认返回 null |
| include_raw_output=true 是否可以返回 raw_output？ | ✅ 是 |
| generate API 是否仍然不写正文？ | ✅ 是 |
| generate API 是否仍然不创建 candidate？ | ✅ 是 |
| generate API 是否仍然不执行 adopt？ | ✅ 是 |
| 是否处理了 _resolve_path() 私有调用问题？ | ✅ 是，新增 validate_path() 公开方法 |
| **是否可以把总进度从 74.7% 推进到 75%？** | **✅ 是** |

---

## 文件变更

| 变更 | 文件 |
|------|------|
| 修改 | backend/api/scene_plan.py |
| 修改 | backend/core/file_ops.py (新增 validate_path) |
| 修改 | tests/test_scene_plan_generate_api.py |
| 修改 | docs/testing/t5-scene-plan-generate-api-2026-06.md |

---

**报告结论**: ✅ T5.2.2 回归补票完成，T5.2 整体完成，可以进入 T5.3，总进度约 75%

