
# T5.1-T5.6：墨韵真实写作闭环盘点报告（含 T5.6 完成版）

**执行日期**: 2026-06-08
**执行人**: Solo Agent
**当前进度**: 约 80%

---

## 1. 当前结论

### 当前墨韵是否已经能完成一条真实写作闭环？

**答案：部分能完成，Scene Plan validate API 已软接入！**

墨韵目前具备以下能力：
- ✅ 项目创建和文件树显示
- ✅ 场景文件打开和编辑
- ✅ Professional dry-run 触发（通过润色/精修按钮）
- ✅ Candidate 生成机制（通过 candidate_policy 强制）
- ✅ CandidatePanel 预览、采用、删除功能
- ✅ Story State / Materials 读写
- ✅ Scene Plan schema 和 validator（后端完成）
- ✅ Scene Plan validate API（后端完成，已软接入 pipeline！）

**当前状态**：
1. ✅ **Scene Plan validate API 已软接入** - 后端 API 存在，在 pipeline 中已集成验证
2. ⚠️ **Scene Plan 生成功能未实现** - 只有校验，没有生成
3. ⚠️ **前端没有 Scene Plan 相关 UI** - 无法让用户创建/编辑 Scene Plan

---

## 2. 闭环检查表

| 环节 | 当前状态 | 是否阻断 | 优先级 | 涉及文件 | 建议处理方式 |
|------|----------|----------|--------|----------|--------------|
| 1. 创建新项目 | ✅ 可用 | - | - | backend/api/projects.py | - |
| 2. 显示项目文件树 | ✅ 可用 | - | - | frontend/stores/file.ts | - |
| 3. 打开场景文件 | ✅ 可用 | - | - | frontend/stores/file.ts | - |
| 4. 填写/读取故事素材 | ✅ 可用 | - | - | backend/api/materials.py | - |
| 5. 触发 Professional dry-run | ✅ 可用 | - | - | frontend/composables/useSceneGenerationActions.ts | - |
| 6. dry-run 生成 candidate | ✅ 可用 | - | - | backend/policies/candidate_policy.py | - |
| 7. CandidatePanel 显示候选稿 | ✅ 可用 | - | - | frontend/components/right-panel/CandidatePanel.vue | - |
| 8. 预览候选稿 | ✅ 可用 | - | - | frontend/components/right-panel/CandidatePanel.vue | - |
| 9. Delete 候选稿 | ✅ 可用 | - | - | backend/api/candidates.py | - |
| 10. Adopt 候选稿 | ✅ 可用 | - | - | backend/api/candidates.py | - |
| 11. Adopt 前冲突检查 | ✅ 可用 | - | - | backend/core/candidate_service.py | - |
| 12. Adopt 后正文更新 | ✅ 可用 | - | - | backend/core/candidate_service.py | - |
| 13. Adopt 后不破坏 story_state | ✅ 可用 | - | - | backend/core/story_state_service.py | - |
| 14. 继续下一场景 | ✅ 可用 | - | - | frontend/composables/useSceneGenerationActions.ts | - |
| 15. Scene Plan validate API 被调用 | ✅ 已接入（后端） | - | backend/core/pipeline.py, backend/api/scene_plan.py | 软接入成功 |

---

## 2.5 T5.1：Scene Plan validate API 软接入完成

### T5.1 目标回顾

**已完成任务：**

1. ✅ 修改 `PipelineRunRequest` 添加 `scene_plan` 可选字段
2. ✅ 在 `pipeline.run()` 方法添加 scene_plan 验证逻辑
3. ✅ 验证软接入：不传 scene_plan 时，旧流程不变；传了 scene_plan 且非法时，阻止 pipeline 执行
4. ✅ 更新 `api/pipeline.py` 传递 scene_plan
5. ✅ 新增 `tests/test_scene_plan_pipeline_integration.py` 测试文件
6. ✅ 所有测试通过

### 软接入设计原则

**向后兼容**：
- **不传 scene_plan**：pipeline 行为与之前完全一致，保持旧流程不受影响
- **传了 scene_plan**：先验证通过后继续执行 pipeline

**安全校验**：
- **传了非法 scene_plan**（含危险路径、违反 candidate_policy 等）：阻止 pipeline 执行，返回明确错误

---

## 3. P0 缺口清单

**无 P0 缺口** - 当前墨韵已经能够完成基本的写作闭环。

---

## 4. P1 缺口清单

### P1-1：Scene Plan validate API 未被实际调用

**描述**：
- 后端 API `POST /api/scene-plan/validate` 已实现并测试通过
- 但 Professional dry-run 的 pipeline 执行时没有调用该 API
- 导致 Scene Plan 的安全校验能力没有被实际使用

**涉及文件**：
- `backend/core/pipeline.py` - 需要在 pipeline 执行前调用 validate API
- `frontend/composables/useSceneGenerationActions.ts` - 需要在前端触发时调用 validate API

**建议处理方式**：
- T5.1 优先：在 Professional dry-run 触发时，先调用 Scene Plan validate API 校验输入
- 可以先在 `backend/core/pipeline.py` 的 `execute_pipeline` 函数中添加 validate 调用
- 如果校验失败，阻止 pipeline 执行并返回错误

### P1-2：Scene Plan 生成功能未实现

**描述**：
- 只有 Scene Plan 的 schema、validator、validate API
- 没有 LLM 调用来生成 Scene Plan
- 用户无法创建结构化的场景规划

**涉及文件**：
- `backend/core/scene_plan_generator.py` - 需要新增（如果 T5.2 要实现）
- `frontend/components/scene-plan/` - 需要新增 UI（如果 T5.2 要实现）

**建议处理方式**：
- T5.2 或后续版本处理
- 可以先做 mock 生成，用于干运行测试
- 后续再接入真实 LLM

### P1-3：前端缺少 Scene Plan 相关 UI

**描述**：
- 前端没有 Scene Plan 创建/编辑入口
- 用户无法直观地看到和修改场景规划

**涉及文件**：
- `frontend/src/components/scene-plan/` - 需要新增
- `frontend/src/composables/useScenePlan.ts` - 需要新增

**建议处理方式**：
- T5.2 或后续版本处理
- 可以先做隐藏的开发者入口，用于测试

---

## 5. Scene Plan validate API 接入结论

### 后端 API 是否存在？
✅ 是 - `backend/api/scene_plan.py` 已实现

### 是否有测试？
✅ 是 - `tests/test_scene_plan_validate_api.py` 有 7 个测试用例

### 是否已被 Professional dry-run 实际调用？
❌ **否** - 需要接入

### T5.1 是否应优先接入？
✅ **是** - 理由：
1. API 已完成并测试通过
2. 接入可以增强安全校验
3. 工作量相对较小
4. 为后续 Scene Plan 生成功能打下基础

---

## 6. 下一步建议

### T5.1 推荐任务
**标题**：Scene Plan validate API 接入 Professional dry-run

**目标**：
1. 在 `backend/core/pipeline.py` 的 `execute_pipeline` 函数中调用 Scene Plan validate API
2. 如果校验失败，阻止 pipeline 执行并返回错误
3. 新增测试验证 validate API 被正确调用
4. 不破坏现有 candidate 机制

**预计工作量**：小

### T5.2 推荐任务
**标题**：Scene Plan 前端 UI 最小接入

**目标**：
1. 新增 Scene Plan 创建/编辑入口（可以是隐藏的开发者入口）
2. 在 Professional dry-run 触发前，先让用户确认/编辑 Scene Plan
3. 集成 Scene Plan validate API 到前端流程

**预计工作量**：中

---

## 7. 详细分析

### 7.1 Professional dry-run 当前实现

**前端触发链路**：
```
EditorToolbar.vue (润色/精修按钮)
  → useSceneGenerationActions.ts (runPipeline)
    → useFileGeneration.ts (runPipeline)
      → backend API (pipeline execution)
        → backend/core/pipeline.py (execute_pipeline)
          → backend/policies/candidate_policy.py (RequireCandidateMiddleware)
```

**关键代码位置**：
- `frontend/src/composables/useSceneGenerationActions.ts:290-337` - `runPipeline` 函数
- `backend/core/pipeline.py` - Pipeline 执行引擎
- `backend/policies/candidate_policy.py` - Candidate 策略强制

### 7.2 Candidate 机制当前实现

**CandidatePolicy 中间件**：
```python
RequireCandidateMiddleware
  - 高风险操作（polish/rewrite）强制 require_candidate=True
  - allow_direct_write 强制为 False
```

**CandidatePanel 功能**：
- 预览候选稿内容
- Adopt 候选稿（更新正文）
- Delete 候选稿
- 冲突检查

### 7.3 Scene Plan validate API 当前状态

**后端实现**：
```python
# backend/api/scene_plan.py
@router.post("/validate")
async def validate_scene_plan_api(scene_plan_data: ScenePlan | dict):
    result = validate_scene_plan(scene_plan_data)
    return ApiResponse.ok(ScenePlanValidateResponse(
        valid=result.valid,
        errors=[...],
        warnings=[...]
    ))
```

**当前未被调用**：
- `backend/core/pipeline.py` 中没有调用 `validate_scene_plan_api`
- `frontend/composables/useSceneGenerationActions.ts` 中没有调用 validate API

---

## 8. 总体评估

### 8.1 优点
1. ✅ 核心安全机制（CandidatePolicy）已完整实现
2. ✅ CandidatePanel UI 功能完整
3. ✅ Story State / Materials 读写正常
4. ✅ Scene Plan schema 和 validator 已完成
5. ✅ Scene Plan validate API 后端完成并测试通过

### 8.2 待改进
1. ❌ Scene Plan validate API 未被实际调用
2. ⚠️ Scene Plan 生成功能未实现
3. ⚠️ 前端缺少 Scene Plan UI

### 8.3 结论
墨韵已经具备基本的真实写作闭环能力。Candidate 机制确保高风险操作必须通过候选稿，不会直接覆盖正文。Scene Plan validate API 的接入将是下一个优先事项，可以在不破坏现有功能的前提下增强安全校验。

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
| T5.3 | ✅ 完成 | Scene Plan 持久化 API |
| T5.4 | ✅ 完成 | Scene Plan 前端 UI 最小集成 |
| T5.4.1 | ✅ 完成 | Scene Plan 前端浏览器 Smoke Test |
| T5.4.2 | ✅ 完成 | Scene Plan 前端完整浏览器 Smoke 修复 |
| T5.5 | ✅ 完成 | Scene Plan 自动加载优化 |
| **T5.6** | **✅ 完成** | **Scene Plan JSON 编辑器最小版本** |
| **T5.7** | **✅ 完成** | **Scene Plan 可选接入 Professional dry-run** |
| **T5.7.1** | **✅ 完成** | **Scene Plan 安全收口（source file 匹配校验）** |
| **T5.8** | **✅ 完成** | **Scene Plan 接入 Professional 真实 smoke test** |
| **T5.8.1** | **✅ 完成** | **真实 smoke 安全收口（脚本隔离、敏感信息扫描）** |
| **T5.9** | **✅ 完成** | **Scene Plan 驱动生成质量对比 smoke test** |
| **T5.9.1** | **✅ 完成** | **质量对比安全与文档收口** |
| **T5.10** | **✅ 完成** | **Scene Plan 质量对比自动评分脚本** |
| **T5.10.1a** | **✅ 完成** | **上传 candidate 证据供人工复评** |
| **T5.10.1** | **✅ 完成** | **评分规则校准（基于人工复评）** |
| **T5.11** | **✅ 初步 PASS** | **多场景样本验证评分稳定性** |
| **T5.12** | **✅ 完成** | **真实生成第二组 Scene Plan 多样本评分样本** |
| **T5.13** | **✅ OK** | **Scene Plan 多案例评分稳定性验证（2 个完整案例）** |
| **T5.14** | **✅ OK** | **多案例评分快照归档** |
| **T5.15** | **⚠️ 归档完成 / 数据质量存在限制** | **多案例评分 final 快照整理（发现 sec-001 为测试数据，需后续真实 Scene Plan 补齐）** |

**当前进度**: 约 87%（数据质量待补齐）
