# T10.4b：T10 Regression Gate + Stage Checkpoint

## Status

**阶段**: T10.4b (Regression Gate + Stage Checkpoint)
**状态**: ✅ 通过
**创建日期**: 2026-06-18
**基于 commit**: aaeac12
**范围**: T10.1–T10.4a 整体回归验收，无功能修改。

---

## 1. 当前 commit

```
Base Commit: aaeac12 (fix: polish T10 candidate interaction layout)
Working Dir: clean
Diff Check:   clean
```

---

## 2. T10.1–T10.4a 已完成能力清单

| 阶段 | 功能 | 状态 |
|------|------|------|
| T10.1b | Quality Explanation UI MVP — 折叠展开、5维度展示、repair说明、safety文本 | ✅ |
| T10.2b | Candidate Compare MVP — mode A/B对比、safety notice、无adopt按钮 | ✅ |
| T10.3b | Candidate Decision Flow UI — 按钮分组、adopt hint、状态可见性矩阵 | ✅ |
| T10.4a | Interaction Smoke + Small-screen Layout — CSS小补丁、布局review | ✅ |

---

## 3. 后端核心回归测试

```
python -m pytest backend/tests/test_repair_candidate.py
                                  test_candidate_quality_metadata.py
                                  test_candidate_feedback_revision.py
                                  test_continuity_anchors.py
                                  test_beat_validator.py
                                  -q --tb=short
```

**结果**: ✅ **52 passed** (27.64s)

覆盖范围：
- candidate repair/revision 核心逻辑
- quality metadata 结构与展示
- feedback revision 生成流程
- continuity anchors 一致性检查
- beat validator 检查

---

## 4. Frontend Build

```
cd frontend && npm run build
```

**结果**: ✅ **3440 modules transformed**, vite build in 2.95s

无 TypeScript 错误，无模块解析错误。

---

## 5. Focused E2E — Candidate Workflow

```
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

**结果**: ✅ **43 passed** (3.3m)

包含 T10.1b (8 tests)、T10.2b (7 tests)、T10.3b (6 tests) 所有新增场景。

---

## 6. Focused E2E — Continuity Anchors

```
npm run test:e2e:mock -- tests/e2e/32-continuity-anchors.spec.ts --reporter=line
```

**结果**: ✅ **2 passed** (25.2s)

---

## 7. Full Mock E2E

```
npm run test:e2e:mock -- --reporter=line
```

**结果**: ✅ **97 passed, 93 skipped, 0 failed**

说明：
- 93 skipped 是预期行为（依赖特定环境或未实现的场景）
- 无测试失败
- 全量 E2E 通过

---

## 8. Guardrails 检查

```
powershell -ExecutionPolicy Bypass -File scripts/ai-guardrails.ps1
```

**结果**: ✅ **GUARDRAILS: PASS**

| 规则 | 结果 |
|------|------|
| API path concatenation (project_dir / req) | ✅ PASS |
| file.updated content leak | ✅ PASS (all hits allowlisted) |
| API Key in localStorage | ✅ PASS |
| Scene terminology (scene not section) | ✅ PASS |
| Duplicate project_id in source_path | ✅ PASS (all hits allowlisted) |
| output_mode=overwrite 防御 | ✅ PASS (LEGACY_COMPAT noted) |

---

## 9. API Key 检查

```
rg "sk-" frontend/src backend/src frontend/src/components
rg "OPENAI_API_KEY" frontend/src backend/src
rg "Authorization: Bearer" frontend/src backend/src
```

**结果**: ✅ 无真实 API key 泄露

命中说明：
- `sk-` 在 `backend/main.py` 中为 `task-queue` 路径片段，无问题
- `sk-1234567890abcdef` 在 `tests/e2e/09-error-boundary.spec.ts` 为测试 fake key，无问题
- `OPENAI_API_KEY` 出现在 `tests/prompt_experiments/*.py` 中仅为 `os.getenv()` 读取，无硬编码
- `check_security.py` 仅列出检查模式，无实际 key
- `.env` 不在 git status 中

---

## 10. Candidate-Only 安全边界复核

| 检查项 | 文件 | 结果 | 说明 |
|--------|------|------|------|
| CompareModal 无 adopt 按钮 | `CompareModal.vue` | ✅ | 仅1处 `采纳` 在 safety notice 文案中 |
| CompareModal 无写/LLM操作 | `CompareModal.vue` | ✅ | 无 write/save/status/repair/generate/LLM 调用 |
| CompareModal 为纯 diff 展示 | `compareDiff.ts` | ✅ | 纯函数，无副作用 |
| CandidatePanel adopt 仅在候选稿面板 | `CandidatePanel.vue` | ✅ | adopt button 在候选稿卡片和 preview modal 中，符合设计 |
| Quality Explanation 不改 candidate 状态 | `CandidatePanel.vue` | ✅ | 纯展示，无 status 写操作 |
| Adopt hint 不禁用 adopt 按钮 | E2E: `adopt hint does not block adopt action` | ✅ | 43rd test confirmed |
| Repair/Feedback Revision 仅生成 child | backend `generation_service.py` | ✅ | backend 测试通过 |

---

## 11. Bugs Found

**无阻断 bug 发现。**

---

## 12. Fixes

**无修复。** T10.4a 提交的 CSS 补丁在本次回归中无回退。

---

## 13. Remaining Issues

| # | 描述 | 严重程度 | 来源 |
|---|------|---------|------|
| R1 | revision modal body 内容过长时可能被 overflow: hidden 截断 | 低 | T10.4a遗留 |
| R2 | candidate-filename 省略号无 tooltip 提示完整文件名 | 低 | T10.4a遗留 |
| R3 | 93 skipped tests in full E2E（预期行为，非bug） | 信息 | 条件依赖未满足 |

---

## 14. 是否建议进入 T10.5

**建议：可以进入 T10.5。**

T10.1–T10.4b 全链路已验证：
- 后端核心逻辑：52 passed ✅
- 前端交互层：43 passed ✅
- 全量 E2E：97 passed, 0 failed ✅
- Guardrails：PASS ✅
- 安全边界：完整 ✅
- 小屏幕布局：已修复 ✅

候选稿系统（T10 系列）的 MVP 核心功能已稳定。

---

## 15. 最终状态

```
HEAD:           aaeac12
前端构建:       ✅ 3440 modules
Backend Tests:  ✅ 52 passed
Focused E2E:    ✅ 45 passed (43 + 2)
Full Mock E2E:  ✅ 97 passed, 93 skipped, 0 failed
Guardrails:     ✅ PASS
API Key:        ✅ 无泄露
Safety Boundary:✅ 完整
Git Status:     ✅ clean
代码改动范围:    仅文档
Backend:        无改动
```

**状态: ✅ T10.4b 通过，建议进入 T10.5**
