# T5.3：Scene Plan 持久化 API 测试报告

**执行日期**: 2026-06-08
**执行人**: Solo Agent
**当前进度**: 约 76%

---

## 1. API 概览

### 1.1 Save API

**路径**: `POST /api/scene-plan/save`

**请求 Schema**:
```python
class ScenePlanSaveRequest(BaseModel):
    project_id: str                              # 项目 ID
    target_file: str                             # 目标场景文件路径
    scene_plan: ScenePlan | dict[str, Any]       # 要保存的 Scene Plan
    overwrite: bool = False                      # 是否覆盖已存在文件
    expected_mtime: float | None = None          # 期望的文件修改时间（冲突检测）
```

**响应 Schema**:
```python
class ScenePlanSaveResponse(BaseModel):
    saved: bool                                  # 是否保存成功
    path: str | None                             # 保存的文件路径
    valid: bool                                  # 是否通过校验
    errors: list[ScenePlanValidationErrorDetail] # 校验错误
    warnings: list[ScenePlanValidationWarningDetail] # 校验警告
    conflict: bool                               # 是否因为文件已存在而冲突
    message: str | None                          # 附加消息
```

### 1.2 Load API

**路径**: `GET /api/scene-plan/load`

**Query 参数**:
- `project_id`: 项目 ID
- `target_file`: 目标场景文件路径

**响应 Schema**:
```python
class ScenePlanLoadResponse(BaseModel):
    exists: bool                     # 文件是否存在
    path: str | None                 # 文件路径
    scene_plan: ScenePlan | None     # 加载的 Scene Plan
    mtime: float | None              # 文件修改时间
    errors: list[ScenePlanValidationErrorDetail]  # 错误信息
```

---

## 2. 路径规则

### 2.1 保存路径

**固定目录**: `materials/scene_plans/`

**文件名映射规则**:
1. 将 `/` 和 `\` 替换为 `__`
2. 去掉 `.md` 后缀（如果有）
3. 危险字符 `..` 和 `.` 替换为 `_`
4. 固定后缀: `.scene-plan.json`

**示例**:
| target_file | 映射结果 |
|------------|---------|
| `chapters/vol-01/ch-001/sec-001.md` | `materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json` |
| `chapters/vol-01/ch-001/sec-001` | `materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json` |
| `chapters/../.env` | `materials/scene_plans/chapters______env.scene-plan.json` |

### 2.2 危险路径拒绝

以下路径被拒绝：
- `../` 路径遍历
- `.env` 敏感文件
- `.git` 目录
- 绝对路径
- 正文目录 (`chapters/`)

---

## 3. 保存逻辑

### 3.1 保存前校验

1. 校验 `target_file` 路径安全（无 `../`、`.env`、`.git`、绝对路径）
2. 调用 `validate_scene_plan(scene_plan)` 校验内容
3. 如果 valid=false，默认不保存（除非显式 `save_invalid=true`，本阶段不支持）
4. 检查目标文件是否已存在

### 3.2 覆盖规则

- `overwrite=false`（默认）：如果文件已存在，返回 `conflict=true`，不覆盖
- `overwrite=true`：如果文件已存在，执行安全覆盖

### 3.3 写入安全

- 写入前检查目录存在，不存在则创建
- 使用 `FileService.write_file()` 安全写入
- 写入失败时不留半成品

---

## 4. 无副作用边界

✅ **保证不执行**:
- ❌ 不修改 target_file 正文
- ❌ 不创建 candidate
- ❌ 不执行 adopt
- ❌ 不触发 LLM
- ❌ 不写 `.candidates/` 目录

✅ **只写**:
- ✅ `materials/scene_plans/*.scene-plan.json`

---

## 5. 测试结果

### 5.1 持久化 API 测试 (10 tests)

```
tests/test_scene_plan_persistence_api.py::test_save_scene_plan_success PASSED
tests/test_scene_plan_persistence_api.py::test_save_scene_plan_conflict_when_exists PASSED
tests/test_scene_plan_persistence_api.py::test_save_scene_plan_overwrite_allowed PASSED
tests/test_scene_plan_persistence_api.py::test_save_invalid_scene_plan_rejected PASSED
tests/test_scene_plan_persistence_api.py::test_save_dangerous_path PASSED
tests/test_scene_plan_persistence_api.py::test_load_scene_plan_success PASSED
tests/test_scene_plan_persistence_api.py::test_load_scene_plan_not_exists PASSED
tests/test_scene_plan_persistence_api.py::test_load_dangerous_path PASSED
tests/test_scene_plan_persistence_api.py::test_no_side_effects PASSED
tests/test_scene_plan_persistence_api.py::test_path_mapping PASSED

10 passed
```

### 5.2 回归测试 (41 tests)

| 测试文件 | 结果 |
|---------|------|
| test_scene_plan_generate_api.py | 8 passed |
| test_scene_plan_validate_api.py | 7 passed |
| test_scene_plan_validator.py | 14 passed |
| test_scene_plan_pipeline_integration.py | 5 passed |
| test_llm_reasoning_detection.py | 7 passed |

**Professional Regression Smoke**: PASSED

**Frontend Build**: PASSED

---

## 6. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/api/scene_plan.py` | 修改 | 新增 save/load API 端点 |
| `tests/test_scene_plan_persistence_api.py` | 新增 | 持久化 API 测试（10 tests） |

---

## 7. 剩余问题

1. ❌ **前端 UI 未实现** - 只完成后端 API，前端无法调用
2. ❌ **未强制接入 Professional dry-run** - Scene Plan 可独立保存，但 dry-run 不会自动引用
3. ❌ **Scene Plan 编辑器未实现** - 无法在 UI 中编辑已保存的 Scene Plan
4. ❌ **未实现 save_invalid 选项** - invalid Scene Plan 会被拒绝保存，无法存为 draft

---

## 8. 下一步建议

### T5.3.1 (推荐)
**标题**: Scene Plan 持久化 API 前端集成

**目标**:
1. 在前端 `useSceneGenerationActions.ts` 添加 save/load 调用
2. 生成成功后自动保存 Scene Plan
3. 后续 dry-run 前自动加载已保存的 Scene Plan

**预计工作量**: 中

### T5.3.2
**标题**: Scene Plan 编辑器 UI

**目标**:
1. 新增 ScenePlanEditor.vue 组件
2. 支持可视化编辑 Scene Plan
3. 支持预览已保存的 Scene Plan

**预计工作量**: 大

---

## 9. 路线图更新

| 阶段 | 状态 | 说明 |
|------|------|------|
| T4.7.x | ✅ 完成 | Candidate 链路收口 |
| T4.8 | ✅ 完成 | Scene Plan schema + validator |
| T4.9 | ✅ 完成 | Scene Plan validate API 后端 |
| T5.0 | ✅ 完成 | 写作闭环盘点 |
| T5.1 | ✅ 完成 | Scene Plan validate API 软接入 |
| T5.2 | ✅ 完成 | Scene Plan generate API 最小版本 |
| T5.2.1 | ✅ 完成 | raw_output 安全修正 |
| T5.2.2 | ✅ 完成 | 全量回归补票 |
| **T5.3** | **✅ 完成** | **Scene Plan 持久化 API** |
| T5.4 | 📋 规划中 | Scene Plan 前端 UI 最小集成 |

**预计 T5.3 完成后进度**: 约 76%
