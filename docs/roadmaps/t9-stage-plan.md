# T9 阶段规划：产品化收口与下一阶段稳定规划

> **阶段**: T9 (Product Stabilization & Next Stage Planning)
> **状态**: 规划中
> **创建日期**: 2026-06-16
> **前置依赖**: T8 写作质量闭环已归档 (`d6a8a7a`)

---

## 一、T8 收口状态

T8 阶段已正式归档（`docs/archives/t8-writing-quality-closure.md`）。最终测试基线：

- Backend tests: 85 passed
- Frontend build: ✓ passed
- Focused E2E: 16 passed
- Full E2E: 62 passed / 93 skipped / 0 failed
- Real LLM smoke: 3/3 passed
- Git: clean

**核心判断：T8 已完成，不应继续在 T8 内无限打磨。** T8 交付了完整的写作质量闭环，包括 beats 输入/注入/validator/warning/feedback revision/multi-round lineage/conservative rules/真实中文链路/真实 LLM smoke。

---

## 二、T9 总目标

T9 不是继续盲目新增功能，而是：

**产品化收口 → 测试债务治理 → 长文连续性最小设计 → 后续写作质量增强规划**

阶段命名：**T9 — 产品化收口与下一阶段稳定规划**

核心判断：

1. T8 已经完成，不能继续在 T8 内无限打磨
2. T9 第一优先级应该是 Release Candidate / 维护版收口
3. 测试债务需要治理，但不一定全部阻断 release
4. 长文连续性是下一阶段核心价值，但必须先做最小设计
5. 写作质量增强可以规划，但不应优先于 release 和测试债务
6. Scene Plan 大系统暂缓，不作为 T9 立即开发目标

---

## 三、当前产品能力基线

### 已交付能力（T8 成果）

- Required / forbidden beats 输入（Professional 面板）
- Generate / rewrite / polish / revise prompt 注入（beat-constraints.md）
- Beat validator metadata（pass / warning / unknown）
- CandidatePanel 质量区展示（beat validation + continuity + warning）
- Adopt 前 warning confirm（advisory，不阻断）
- Feedback revision child candidate（pending → child）
- Multi-round revision lineage（revision_group_id + revision_index）
- Polish conservative rules（polish-conservative-rules.md）
- 真实中文后端链路（无乱码、无 mojibake）
- 真实 UI + 真实 LLM smoke（agnes-2.0-flash，3/3 通过）
- Candidate-only 安全边界（AI 不自动覆盖正文）

### 已交付基础设施

- LiteLLM 统一模型调用
- 本地文件系统存储（无数据库）
- SSE 实时事件推送
- Candidate 安全生命周期（pending → adopted / discarded）
- FileService 并发控制（expected_mtime / expected_hash / FILE_CONFLICT）
- Pipeline YAML 工作流（generate / rewrite / polish）
- CodeMirror 6 编辑器
- Vue 3 + TypeScript + Pinia 前端架构
- FastAPI + async 后端架构

---

## 四、四个候选方向与优先级排序

### Priority 1：T9.1 — Release Candidate / 维护版收口

**优先级：最高**

**原因**：T8 已经形成完整阶段成果，现在应该先固化成一个稳定版本。用户和团队都需要一个明确的里程碑来确认"这些功能是稳定的、可用的"。

**建议内容**：

- 版本定位：v0.1.3 维护版或 v0.2.0 正式版
- README 更新（安装、快速开始、功能列表）
- CHANGELOG 更新（T7→T8 变更汇总）
- KNOWN_ISSUES 更新（remaining issues 列表）
- Release checklist（发布前检查清单）
- Preflight checklist（环境检查清单）
- Smoke checklist（冒烟测试清单）
- T8 能力摘要（面向用户的功能说明）
- 已知限制说明

**重点问题**：

- 是否把 T8 成果作为 v0.1.3 维护版（推荐：是）
- 是否升级为 v0.2.0（需要评估破坏性变更）
- Release 前必须补哪些文档
- 哪些 remaining issues 进入 KNOWN_ISSUES

**判断**：T9.1 应该作为 T9 第一批任务。

---

### Priority 2：T9.2 — 测试债务专项

**优先级：高**

**当前状态**：full E2E 62 passed / 93 skipped / 0 failed

**建议内容**：

- 恢复 skipped E2E 分类（93 个 skipped 逐个审计）
- Mock helper 抽离（减少 copy-paste）
- waitForTimeout 清理（改用 wait-for-condition）
- Spec 99 标准 mock 化
- Real backend smoke 分层（unit / integration / smoke）
- Real LLM smoke 分层（快速冒烟 / 完整验证）

**重点问题**：

- 哪些 skipped 是合理跳过（real LLM guard、phase smoke）
- 哪些 skipped 是旧测试债务（过时用例、环境依赖）
- 哪些 release 前必须恢复
- 哪些可以 release 后治理

**判断**：T9.2 应该排在 release 收口之后，作为稳定性专项。

---

### Priority 3：T9.3 — 长文连续性 / Story State 最小设计

**优先级：中高**

**注意**：不要直接做 Scene Plan 大系统。

**建议方向**：

- Story State Anchors（故事状态锚点）
- Continuity Anchors（连续性锚点）
- 角色状态追踪
- 线索状态追踪
- 地点状态追踪
- 关系状态追踪
- 用户可控入口（不是全自动）
- Candidate 生成时引用（prompt 注入）

**核心原则**：先做用户可控的 continuity anchors，不做自动规划全书。

**T9.3 不应马上开发大功能，应该先做设计文档**：

```
docs/design/t9-3-continuity-anchors.md
```

**判断**：T9.3 是下一阶段真正价值点，但必须先设计，不能直接开写代码。

---

### Priority 4：T9.4 — 写作质量增强

**优先级：中**

**可能内容**：

- Repair candidate（自动修复候选稿 — 注意：仍然只生成 candidate）
- Better validator categories（更细粒度的 beat 分类）
- Quality score（综合质量评分 — 展示用，不做硬判断）
- Candidate comparison（候选稿对比视图）
- More helpful warning explanation（更有用的 warning 说明）

**必须遵守**：

- Repair 也只能生成 candidate
- Validator 不能直接改正文
- Quality score 不能变成硬判断
- 不能 automatic repair
- 不能 auto adopt

**判断**：T9.4 可以规划，但不应优先于 T9.1 / T9.2 / T9.3。

---

## 五、暂缓事项

以下方向明确**不在 T9 阶段立即开发**：

- **Scene Plan 大系统** — 复杂度过高，容易破坏 candidate-only 安全边界
- **自动修文** — 与 candidate-only 原则冲突
- **自动规划全书** — 需要更成熟的故事理解能力
- **多模型裁判** — 成本和复杂度高于当前收益
- **Adopted candidate revision** — 违反安全边界
- **复杂质量仪表盘** — CandidatePanel 质量区已满足需求

**原因**：这些功能会显著增加系统复杂度，容易破坏 T8 已经稳定的 candidate-only 安全边界。

---

## 六、推荐执行顺序

```
T9.0  → 阶段规划文档（本文档）              ✅ 已完成
T9.1  → Release Candidate / 维护版收口       ⏭ 第一优先级
T9.1-final → Release preflight / smoke checklist
T9.2  → 测试债务专项                         ⏭ 第二优先级
T9.3  → 长文连续性最小设计                    ⏭ 第三优先级（先设计）
T9.4  → 写作质量增强规划                      📋 仅规划，暂不实现
```

执行原则：

- T9.1 是第一优先级
- T9.3 必须先设计再开发
- T9.4 暂不进入实现

---

## 七、第一批任务建议

### T9.1a：版本定位与 Release 文档审查

| 属性 | 值 |
|------|------|
| Risk | Risk C / Documentation Review |
| 目标 | 确认 v0.1.3 / v0.2.0 版本定位 |
| 输入 | T8 归档文档、当前 README、CHANGELOG |
| 输出 | 版本定位决策、必须更新项清单 |
| 预估 | 1 个任务 |

### T9.1b：Release 文档更新

| 属性 | 值 |
|------|------|
| Risk | Risk B / Documentation + Release Prep |
| 目标 | 更新全部 release 相关文档 |
| 输入 | T9.1a 决策 |
| 输出 | 更新后的 README / CHANGELOG / KNOWN_ISSUES / RELEASE_CHECKLIST + T8 能力摘要 |
| 预估 | 1-2 个任务 |

### T9.1c：Preflight 与 Smoke Checklist

| 属性 | 值 |
|------|------|
| Risk | Risk B / Release Validation |
| 目标 | 跑全部测试并整理 release checklist |
| 输入 | T9.1b 完成的文档 |
| 输出 | 测试结果报告、release checklist 逐项确认 |
| 预估 | 1 个任务 |

### T9.2a：Skipped E2E 分类报告

| 属性 | 值 |
|------|------|
| Risk | Risk C / Test Audit |
| 目标 | 把 93 skipped 分类 |
| 输入 | E2E 测试文件和 skip 注释 |
| 输出 | 分类报告（合理跳过 / 旧债务 / 应恢复） |
| 预估 | 1 个任务 |

### T9.3a：Continuity Anchors 设计文档

| 属性 | 值 |
|------|------|
| Risk | Risk C / Design Only |
| 目标 | 设计用户可控的 story state / continuity anchors |
| 输入 | T8 story-state / continuity anchors 现有实现 |
| 输出 | 设计文档（不写代码、不做 Scene Plan） |
| 预估 | 1-2 个任务 |

---

## 八、T9 必须继续遵守的安全边界

以下边界从 T8 继承，在 T9 全部子任务中**不可违反**：

1. **不自动覆盖正文** — AI 输出永远不直接写入正式场景文件
2. **不自动 adopt** — 正文只在用户明确点击 adopt 后才改变
3. **所有 AI 输出必须先进入 candidate** — 包括 repair、revision、任何新操作
4. **Adopt 前正式正文不变** — source 文件在 adopt 操作前保持原样
5. **Delete 不影响正文** — 删除 candidate 不修改任何正式文件
6. **Parent candidate 不被 child 修改** — revision 只创建新的 child candidate
7. **Validator 只能提示，不能直接改正文** — beat validation 结果是 advisory
8. **Repair 只能生成 candidate** — 即使未来实现自动修复，也必须通过 candidate 流程
9. **不能绕过 FILE_CONFLICT / hash / expected_mtime** — 并发安全机制不可绕过
10. **不能泄露 API Key** — prompt 事件、日志、测试报告中不含敏感信息

---

## 九、每个任务的风险等级汇总

| 任务 | 风险等级 | 类型 | 是否改代码 |
|------|----------|------|-----------|
| T9.0 阶段规划 | Risk C | Documentation | ❌ |
| T9.1a 版本定位 | Risk C | Doc Review | ❌ |
| T9.1b 文档更新 | Risk B | Doc + Release | ❌ |
| T9.1c Preflight | Risk B | Validation | ❌ |
| T9.2a Skipped 分类 | Risk C | Test Audit | ❌ |
| T9.2b 恢复 skipped | Risk B | Test Fix | ✅ |
| T9.2c Mock 抽离 | Risk B | Refactor | ✅ |
| T9.3a Anchors 设计 | Risk C | Design | ❌ |
| T9.3b Anchors 实现 | Risk A | Feature | ✅ |
| T9.4a 质量增强规划 | Risk C | Planning | ❌ |

---

## 十、最终建议

T9 阶段应以**稳定优先、增量规划**为原则：

1. **第一步**（T9.1）：把 T8 成果固化为稳定版本，让用户和团队看到明确的里程碑
2. **第二步**（T9.2）：治理测试债务，提升 CI/CD 信心和可维护性
3. **第三步**（T9.3）：设计长文连续性方案，为下一阶段核心价值做准备
4. **第四步**（T9.4）：规划写作质量增强，但暂不进入实现

T9 不应追求大量新功能，而应确保已有功能**稳定、可用、可发布**，同时为下一阶段做好**设计和规划储备**。
