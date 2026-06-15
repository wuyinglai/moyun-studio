# T8 写作质量闭环 — 阶段归档

> **阶段**: T8 (Writing Quality Closure)
> **状态**: ✅ 已完成并归档
> **最终 commit**: `58aa74b`
> **归档日期**: 2026-06-16

---

## 一、阶段目标

T8 阶段的核心问题是：

> 小模型写小说总是出现逻辑矛盾、小错误、漏信息点。

经过讨论后确定的策略不是简单地加 UI 控制项，而是建立一套完整的**写作质量闭环**：

```
Prompt 单体测试
→ Prompt 装配测试
→ Required beats 检查
→ Beat validator + warning
→ 用户反馈再生成 (feedback revision)
→ 多轮 revision lineage
→ 真实 UI + 真实 LLM smoke
```

最终交付的能力是：**AI 生成内容永远不自动覆盖正文，所有修改都通过 candidate 候选稿，正文只在用户明确 adopt 后才改变。**

---

## 二、时间线

### T8.0 — Prompt 单体质量基准

**Commit**: `3dbfd91` (docs: add T8 prompt quality benchmark)

比较了三种 prompt 策略：A baseline（当前 prompt）、B facts-first（事实优先）、C scene plan（场景计划）。

**结论**：硬约束不一定让输出更好；scene plan 有价值但不适合马上产品化。

---

### T8.1 — Prompt 装配一致性测试

**Commit**: `3675766` (docs: add T8 prompt assembly benchmark)

比较 current-like / facts-first / plan-checker-draft 三种装配方式。

**结论**：facts-first 可作为 opt-in 选项，但不是银弹；checker 不等于自动质量闭环。

---

### T8.2 — Facts-first + Debug Prompt Export

**Commit**: `2a238ef` (feat: add facts-first prompt assembly experiment)

debug prompt export 功能成为后续所有定位工作的基础。facts-first 保留 opt-in。required beats omission 被识别为重点问题。

---

### T8.2.1 — Required Beats 稳定性实验

**Commit**: `52a85f8` (docs: add T8 required beats benchmark)

评估 self-check 机制。**结论**：self-check 效果最好但仍不能 100% 可靠，需要生成后 validator。

---

### T8.2.2–T8.2.5 — Required Beat Validator Framework

**Commits**: `f81f4da` → `04cc38c` → `487c361` → `d3fdb65`

建立了完整的 validator 框架、disagreement audit、schema/prompt/rule 修正、expanded benchmark。

**关键决策**：

| 功能 | 决策 |
|------|------|
| JSON validator warning | ✅ Yes |
| Natural language explanation | Limited（有限展示） |
| Rule precheck | Weak signal（仅作弱信号） |
| Automatic repair | ❌ No |
| Repair candidate（未来） | 可考虑 |
| Required beats UI | ✅ Yes |

---

### T8.3-mini — Candidate Metadata Warning

**Commit**: `67a0bbf` (feat: add required beat validation metadata)

candidate metadata 加入 `beat_validation` 字段。CandidatePanel 显示 pass / warning / unknown 状态。adopt 前显示 warning confirm，但 warning 是 advisory，不阻断 adopt。

---

### T8.3.2 — Required Beats 输入 UI

**Commit**: `779a647` (feat: add required beats input for generation)

Professional 面板增加 required / forbidden beats 输入框。空输入不启用 validator；有输入则自动开启检查。

---

### T8.3.3 — Prompt Assembly Quality

**Commit**: `93ac146` (feat: include required beats in generation prompt)

required / forbidden beats 正确注入 generation prompt，通过 debug prompt 事件验证。

---

### T8.4 — 写作质量闭环稳定包

**Commits**: `cd5c295` → `f385bce`

修复 LLM 慢响应 UX、error recovery、CandidatePanel warning 展示、preview/adopt/delete 回归。

**Commit**: `a9e38a7` (docs: add T8.4 final regression report)

---

### T8.5-mini — Feedback Revision Candidate

**Commits**: `286fad0` (design) → `d650592` (review) → `b6088bd` (feat: add feedback revision candidates)

实现 pending candidate 可按用户反馈生成 child candidate。parent 保留不变、child 为 pending 状态、不自动 adopt、不覆盖正文。仅 pending 状态的 candidate 支持 revision。

**Commit**: `fcff072` (docs: add T8.5 mini final regression report)

---

### T8.6 — Feedback Revision 稳定包

**Commit**: `46eee74` (fix: stabilize feedback revision workflow)

LLM failure 不创建坏 child、多轮 A→B→C lineage、revision_group_id / revision_index、feedback modal UX、API retry 修复。

**Commit**: `f6a3a02` (docs: add T8.6 final regression report)

---

### T8.6.1 — Full E2E Mock 稳定性

**Commit**: `36f73fc` (test: stabilize full E2E mock suite)

full E2E 从超时变成完整结束：62 passed / 93 skipped / 0 failed。测试基础设施稳定。

---

### T8.7 — CandidatePanel 质量面板整理

**Commit**: `88f4b04` (refactor: organize candidate quality panel)

CandidatePanel 重构为 4 个清晰区域：Header / Quality Check / Revision Info / Actions。warning 与 revision info 展示更清晰。E2E 测试更新。

---

### T8.8 — 真实写作场景 Dogfood

**Commit**: `2a1fa9d` (docs: add T8.8 writing quality dogfood report)

3 组真实写作场景代码审查 + 场景追踪。综合评分 4.1/5。发现 rewrite/polish beats 未进入 prompt（P1）、validator index alignment fragile（P1）等问题。

---

### T8.9 — 质量链路可靠性修复

**Commit**: `c7de22e` (fix: improve writing quality chain reliability)

rewrite / polish prompt 加入 beats 渲染。validator 支持 id / text exact / difflib similarity 三级对齐。validator 增加最多 1 次 retry。

---

### T8.10 — Rewrite / Polish 真实 LLM Dogfood

**Commit**: `5492b04` (docs: add T8.10 rewrite polish dogfood report)

通过真实 LLM 验证 rewrite / polish 流程。polish 暴露微动作不自然问题。feedback revision 可有效修正。

---

### T8.11 — Polish Prompt Tuning

**Commit**: `c5331fd` (fix: tune polish prompt continuity constraints)

新增 `prompts/blocks/polish-conservative-rules.md`，接入 polish 4 个步骤模板。减少微动作添加、隐性连续性漂移、关系跳跃。backend tests 75 passed。

---

### T8.12 — 后端中文链路 Dogfood

**Commit**: `8377e46` (docs: add T8.12 in-product Chinese dogfood report)

使用真实后端代码路径 + fake LLM 验证中文全链路。polish/rewrite/feedback revision 三个场景全部通过。中文 prompt / candidate / metadata 无乱码。parent / source 安全。

---

### T8.13 — 真实 UI + 真实 LLM Smoke

**Commit**: `58aa74b` (docs: add T8.13 real UI LLM smoke report)

使用真实后端 + 真实 LLM（agnes-2.0-flash）端到端 smoke test。3/3 场景全部通过。beat validation 全部 pass。中文编码正常。安全边界完整。

---

## 三、已完成能力

T8 阶段交付的完整能力清单：

1. **Required / Forbidden Beats 输入** — Professional 面板支持用户输入必须保留和禁止出现的信息点
2. **Prompt 注入** — generate / rewrite / polish / revise prompt 自动注入 beats 约束
3. **Beat Validator** — 生成后自动检查 beats 满足情况，输出 pass / warning / unknown
4. **Candidate Metadata Warning** — CandidatePanel 展示 beat_validation 状态和详情
5. **Adopt Warning Confirm** — adopt 前如有 warning 显示确认提示（advisory，不阻断）
6. **Feedback Revision** — pending candidate 可按用户反馈生成 child candidate
7. **Multi-round Revision Lineage** — revision_group_id + revision_index 追踪多轮修改
8. **CandidatePanel 质量区** — 清晰展示 beat validation / continuity / warning 信息
9. **LLM Slow/Error UX** — 慢响应和错误时的友好提示和恢复机制
10. **真实中文链路** — 中文 prompt / candidate / metadata 全链路无乱码
11. **Polish Conservative Rules** — polish 流程包含保守润色边界规则

---

## 四、关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| AI 生成内容写入方式 | Candidate-only | 绝不自动覆盖正文 |
| Beat validator 输出 | JSON warning | 结构化、可展示、可追溯 |
| Automatic repair | ❌ 不做 | 风险高，不如让用户通过 feedback revision 控制 |
| Repair candidate | 暂不做 | 未来可考虑，当前 feedback revision 已覆盖需求 |
| Validator natural explanation | Limited | LLM 解释不稳定，优先展示结构化数据 |
| Warning 是否阻断 adopt | ❌ Advisory only | 用户应有最终决定权 |
| Feedback revision 范围 | Pending only | adopted/discarded 不应再修改 |
| Polish conservative rules | 仅 polish | rewrite 需要更大自由度 |
| Validator alignment | id + text exact + difflib | 三级回退，兼顾准确性和鲁棒性 |

---

## 五、安全边界

以下安全边界经过 T8 全阶段反复验证，是产品的**不可违反规则**：

1. **AI 输出不自动覆盖正文** — 所有生成内容都通过 candidate
2. **正文只在用户 adopt 后改变** — adopt 是唯一的正文写入触发
3. **Feedback revision 只生成 child candidate** — 不修改 parent，不覆盖正文
4. **Parent candidate 不被 child 修改** — parent 内容和状态保持不变
5. **Adopted / discarded / rejected candidate 不支持 revision** — 只有 pending 可以
6. **Warning 是 advisory，不阻断 adopt** — 用户有最终决定权
7. **expected_mtime / hash / FILE_CONFLICT 不可绕过** — 并发安全
8. **Debug prompt 不泄露 API Key** — prompt 事件不含敏感信息
9. **Candidate source_path 使用项目内相对路径** — 无重复 project_id

---

## 六、测试基线

最终稳定测试基线（T8.13 commit `58aa74b`）：

| 测试套件 | 结果 | 说明 |
|----------|------|------|
| Backend tests | **85 passed** | pipeline 75 + beat_validator + candidate_feedback 10 |
| Frontend build | **✓ passed** | TypeScript + Vite，无编译错误 |
| Focused E2E | **16 passed** | candidate-workflow.spec.ts |
| Full E2E | **62 passed / 93 skipped / 0 failed** | 完整结束，无超时 |
| Real LLM smoke | **3/3 passed** | polish + rewrite + feedback revision |
| Git status | **clean** | 无未提交变更 |

**关于 skipped tests**：93 个 skipped tests 大多是 real backend / real LLM / phase smoke 测试，被环境变量 guard（如 `MOYUN_ALLOW_REAL_LLM_SMOKE`）。这些测试在 CI 环境中按需启用，不影响日常开发。full E2E 可完整结束，无卡死或超时。Spec 99 等历史测试债务不是 T8 阻断项。

---

## 七、Remaining Issues

### P2（建议后续优先处理）

- **Full E2E skipped 数量较多**（93 个）— 后续可逐步恢复或清理过时的 guard
- **Validator 对叙事类 / terminal hook 判断有限** — beat validator 对非事实性 beats 的评估能力有待提升
- **TOCTOU / atomic write** — 文件写入的原子性和并发安全仍有优化空间
- **Real LLM latency 取决于模型服务** — 无产品侧解决方案，需要用户选择更快的模型

### P3（低优先级技术债）

- **MCP Unicode transport 问题** — Agnes MCP 对原始中文仍有 transport 问题，但不影响产品后端
- **Polish 仍可能出现轻微笨拙短语** — 微动作和隐性连续性已基本解决，偶有残余
- **Mock 实现 copy-paste 较多** — E2E mock 代码重复度高，可抽取公共 helper
- **waitForTimeout 硬编码较多** — E2E 测试中硬编码等待时间，可改用 wait-for-condition
- **Candidate 文件写入非原子** — 当前 FileService 的 write_file 非原子操作

---

## 八、不再继续打磨的内容

以下方向明确**不在 T8 阶段继续迭代**，应放到后续阶段评估：

1. **Polish 文采** — 文采调优是开放性任务，不应阻塞质量闭环
2. **Validator 绝对准确率** — 当前三级对齐 + retry 已足够实用，100% 准确率不现实
3. **Automatic repair** — 风险高于收益，feedback revision 已覆盖用户修正需求
4. **Scene Plan** — 有价值但复杂度高，需要独立阶段设计
5. **Complex quality dashboard** — 当前 CandidatePanel 质量区已满足需求
6. **Adopted candidate revision** — 违反安全边界，不应支持
7. **多模型裁判** — 成本和复杂度高于当前收益

---

## 九、下一阶段建议：T9

### T9.1 — Release Candidate / 维护版收口

整理 v0.1.3 或 v0.2.x 维护路线。更新 README / CHANGELOG / KNOWN_ISSUES。做 preflight check。release checklist 逐项验证。

### T9.2 — 测试债务专项

恢复 skipped E2E。mock helper 抽离公共模块。去掉 waitForTimeout 硬编码。real backend smoke 分层（unit / integration / smoke）。

### T9.3 — 长文连续性 / Story State

不是马上做 Scene Plan，而是先设计 story state / continuity anchors 的用户可控入口。让用户能看到和调整 AI 对"故事状态"的理解。

### T9.4 — 写作质量增强

Repair candidate（自动修复候选稿）。Better validator categories（更细粒度的 beat 分类）。Quality score（综合质量评分）。但必须保持 candidate-only，不自动覆盖正文。

---

## 十、最终结论

T8 阶段从"小模型写作总是出错"这个问题出发，经过 14 个子阶段的迭代，建立了完整的写作质量闭环。核心成果是：

1. **用户可控** — required / forbidden beats 让用户精确控制 AI 必须遵守的约束
2. **安全边界清晰** — AI 输出永远不自动覆盖正文，所有修改通过 candidate
3. **质量可见** — beat validator 提供结构化的 pass / warning / unknown 评估
4. **修正路径完备** — feedback revision 支持多轮迭代，lineage 可追溯
5. **真实验证** — 经过真实 LLM + 真实后端 + 中文全链路 smoke test

T8 阶段可以正式归档。后续质量优化工作应在 T9 及之后阶段展开。
