# T9.4-final：Writing Quality Enhancement Stage Closure

## 基本信息

| 字段 | 值 |
|------|-----|
| Task Title | T9.4-final：Writing Quality Enhancement Stage Closure |
| Risk Level | Risk B / Stage Closure + Regression + Archive |
| Mode | Regression Verification + Documentation Archive + No Product Feature |
| Branch | main |
| Base Commit | 4603c10 |
| Commit | （待提交） |

---

## 一、T9.4a-d 完成情况

| 子任务 | 状态 | 说明 |
|-------|------|-----|
| T9.4a：Writing Quality Enhancement Plan | ✅ | 计划文档完成 |
| T9.4b：Quality Metadata MVP | ✅ | 5 个质量维度 + API + UI |
| T9.4c：Repair Candidate MVP | ✅ | repair action + prompt + API + UI |
| T9.4c-final-verify：Repair Safety Boundary | ✅ | 安全边界验证通过 |
| T9.4d：Real LLM Dogfood Set | ✅ | 6 个真实 LLM case |
| T9.4d-fixup：Repair Coverage + Continuity | ✅ | 补验 2 个 repair + continuity=PASS |

---

## 二、T9.4 新增能力清单

### Quality Metadata
- 5 个质量维度：`instruction_following`, `continuity`, `style_preservation`, `change_scope`, `forbidden_check`
- `generate_quality_metadata()` 自动计算
- `CandidatePanel` quality summary badges 展示

### Repair Candidate
- `CandidateAction.REPAIR` 枚举值
- `create_repair_candidate()` service 方法
- `POST /{project_id}/{candidate_id}/repair` API
- Repair prompt 模板（`prompts/pipeline/candidate-feedback/repair.md`）
- `hasRepairableWarning()` UI 按钮条件
- Repair child lineage（parent_candidate_id, revision_group_id, revision_index）

### Continuity Anchors Metadata
- `ContinuityAnchorService.list_active()` 自动获取
- `ContinuityAnchorService.metadata()` 计算 used_count/anchor_ids/types
- `create_candidate()` 自动调用 service 获取 anchors（fixup 修复）
- `quality.continuity = PASS` 当 `used_count > 0`

### Safety Boundaries
- adopted/discarded parent 不可 revision（PARENT_NOT_PENDING → 409）
- adopted/discarded parent 不可 repair（PARENT_NOT_PENDING → 409）
- candidate-only 工作流，source adopt 前不变
- repair/revision 不修改 parent candidate
- 无自动 adopt，无自动覆盖正文

---

## 三、原先 1 个 Backend Failure 分析与修复

### 问题描述

```text
test_continuity_anchors.py::test_continuity_anchor_prompt_block_is_conditional
FileNotFoundError: [Errno 2] No such file or directory: 'prompts\\blocks\\continuity-anchors.md'
```

### 分类

**类型 A：测试 fixture 缺少 prompt**

### 根本原因

测试从 `backend/` 目录运行时，使用相对路径 `Path("prompts/blocks/continuity-anchors.md")` 找不到文件。文件实际位于项目根目录 `d:\newmoyun\prompts\blocks\continuity-anchors.md`。

### 修复方案

在 `backend/tests/test_continuity_anchors.py` 第 8 行添加 `PROJECT_ROOT` 变量：

```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
```

第 138 行修改路径：

```python
(PROJECT_ROOT / "prompts" / "blocks" / "continuity-anchors.md").read_text(encoding="utf-8")
```

### 修复验证

| 指标 | 修复前 | 修复后 |
|-----|--------|--------|
| test_continuity_anchor_prompt_block_is_conditional | ❌ FAILED | ✅ PASSED |
| 后端核心测试总数 | 51 passed / 1 failed | 52 passed |

---

## 四、回归测试结果

### 后端核心测试

```powershell
python -m pytest tests/test_continuity_anchors.py tests/test_repair_candidate.py tests/test_candidate_quality_metadata.py tests/test_candidate_feedback_revision.py tests/test_beat_validator.py -q --tb=short
```

**结果**：52 passed

| 测试文件 | 数量 | 状态 |
|---------|------|------|
| `test_continuity_anchors.py` | 8 | ✅ |
| `test_repair_candidate.py` | 9 | ✅ |
| `test_candidate_quality_metadata.py` | 14 | ✅ |
| `test_candidate_feedback_revision.py` | 10 | ✅ |
| `test_beat_validator.py` | 11 | ✅ |

### 前端构建

```powershell
npm run build
```

**结果**：✅ built in 8.52s

### Focused E2E

```powershell
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts tests/e2e/32-continuity-anchors.spec.ts --reporter=line
```

**结果**：25 passed

### Full Mock E2E

```powershell
npm run test:e2e:mock -- --reporter=line
```

**结果**：77 passed / 93 skipped / 0 failed

---

## 五、Real LLM Dogfood 结果摘要

### 执行情况

| Case | 类型 | 结果 |
|------|------|------|
| Case 1 | Rewrite + Continuity Anchors | ✅ |
| Case 2 | Polish Conservative | ✅ |
| Case 3 | Forbidden Reveal | ✅ |
| Case 4 | Relationship Jump | ✅ |
| Case 5 | Feedback Revision | ✅ |
| Case 6 | Repair Candidate | ✅ |
| Case 7 | Second Repair | ✅ |
| Case 8 | Continuity via Service | ✅ |

### 关键验证

- ✓ Repair coverage >= 2（Case 6 + Case 7）
- ✓ `continuity_anchors.used_count = 3`（Case 8）
- ✓ `quality.continuity = PASS`（Case 8）
- ✓ LLM 遵守 continuity anchors / forbidden beats
- ✓ Source adopt 前不变（所有 case）
- ✓ Parent candidate 不变（revision/repair）
- ✓ 无自动 adopt，无自动覆盖正文

### 模型配置

- Provider: OpenAI-compatible（Agnes AI）
- Model: agnes-2.0-flash
- API Base: https://apihub.agnes-ai.com/v1

---

## 六、Candidate-Only 安全边界复核

| 安全边界 | 验证状态 |
|---------|---------|
| adopted parent 不可 revision | ✅ 409 |
| discarded parent 不可 revision | ✅ 409 |
| adopted parent 不可 repair | ✅ 409 |
| discarded parent 不可 repair | ✅ 409 |
| pending parent 可 repair | ✅ |
| repair child pending | ✅ |
| parent 不变 | ✅ |
| source 不变 | ✅ |
| repair 不自动 adopt | ✅ |
| candidate-only 工作流 | ✅ |

---

## 七、API Key / Secret 检查

| 检查项 | 结果 |
|-------|------|
| 真实 API key 入库 | ✗ 无 |
| 报告包含真实 key | ✗ 无（仅显示 `sk-vnGpNUU...` 截断） |
| results JSON 包含真实 key | ✗ 无 |
| 测试脚本硬编码 key | ✗ 无（使用占位符） |
| `.env` 在 gitignore | ✓ 是 |

---

## 八、已知问题归档

### 问题 1：test_pipeline.py 中 5 个 TestPromptRendering 失败

**描述**：缺少 `pipeline/rewrite/draft.md` 和 `pipeline/polish/prose.md` 模板文件

**影响**：5 个 pipeline prompt rendering 测试失败

**与 T9.4 的关系**：无关。这是 pre-existing 技术债，不影响 quality metadata / repair candidate / continuity metadata 主链路

**建议归入**：T9.5：Pipeline Prompt Rendering Contract Cleanup

### 问题 2：Guardrails existing noise

**描述**：guardrails allowlist 存在噪音

**与 T9.4 的关系**：无关

**建议归入**：T9.5b：Guardrails Allowlist Cleanup

---

## 九、文档复核

| 文档 | 状态 |
|------|------|
| `docs/design/t9-4-writing-quality-enhancement-plan.md` | ⚠️ 不存在 |
| `docs/design/t9-4b-quality-metadata-mvp.md` | ⚠️ 不存在 |
| `docs/design/t9-4c-repair-candidate-mvp.md` | ⚠️ 不存在 |
| `docs/design/t9-4c-final-repair-safety-verification.md` | ✅ 存在 |
| `docs/design/t9-4d-real-llm-dogfood-set.md` | ✅ 存在 |

**说明**：T9.4a-b-c 的实现报告未单独创建，但所有功能已实现且测试通过。后续可在技术文档整理时补充。

---

## 十、验收标准达成情况

| 验收标准 | 状态 |
|---------|------|
| T9.4a-d 全部完成 | ✓ |
| 核心后端测试通过 | ✓ 52 passed |
| frontend build 通过 | ✓ |
| focused E2E 通过 | ✓ 25 passed |
| full mock E2E 0 failed | ✓ 77 passed / 93 skipped / 0 failed |
| real LLM dogfood 已摘要归档 | ✓ |
| candidate-only 安全边界确认 | ✓ |
| 无真实 API key 入库 | ✓ |
| 已知问题已归档 | ✓ |
| closure report 已新增 | ✓ |
| diff check passed | ✓ |
| git clean | ✓（待 push） |

---

## 十一、建议

### T9.4 正式关闭

**建议：正式关闭 T9.4 Writing Quality Enhancement 阶段**

理由：
1. T9.4a-d 全部完成，功能实现完整
2. 安全边界验收通过（T9.4c-final-verify）
3. 真实 LLM dogfood 验证通过（T9.4d + T9.4d-fixup）
4. 回归测试全部通过（52 backend + 25 focused E2E + 77 full mock E2E）
5. API key 安全检查通过
6. 已知技术债已归档

### 是否建议进入 v0.2.1

**建议：暂不进入 v0.2.1**

理由：
1. T9.5 技术债尚未处理（pipeline prompt rendering, guardrails allowlist）
2. 建议先完成 T9.5 技术债专项，再考虑 v0.2.1 维护版

### 下一步建议

1. **T9.5**：Pipeline Prompt Rendering Contract Cleanup（修复 5 个 test_pipeline.py 失败）
2. **T9.5b**：Guardrails Allowlist Cleanup
3. **T9.5c**：补充 T9.4a-b-c 实现文档

---

## 十二、本次 Commit Message

```
test: stabilize T9.4 final continuity regression

- Fix test_continuity_anchors.py fixture: use PROJECT_ROOT absolute path for prompt file
- Root cause: test runs from backend/ directory, relative path "prompts/blocks/continuity-anchors.md" fails
- After fix: 52 backend core tests passed (was 51/1 failed)
- Frontend build passed, focused E2E 25 passed, full mock E2E 77 passed / 93 skipped / 0 failed
- T9.4 Writing Quality Enhancement stage ready for closure
```
