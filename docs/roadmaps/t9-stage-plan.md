# T9 阶段规划：产品化收口与下一阶段稳定规划

> 阶段：T9
> 类型：Stage Planning / Documentation
> 风险等级：Risk C
> 状态：规划完成
> 日期：2026-06-16
> 前置依赖：T8 写作质量闭环已归档，见 `docs/archives/t8-writing-quality-closure.md`

## 1. T8 收口状态

T8 阶段已经完成“写作质量闭环”的主线收口，不建议继续在 T8 内无限延伸 prompt、validator、polish、repair 或 Scene Plan 相关工作。

T8 已完成的核心能力：

- required / forbidden beats 最小输入 UI。
- required / forbidden beats 条件注入生成 prompt。
- required beat validator metadata 写入 candidate。
- CandidatePanel 显示 pass / warning / unknown。
- warning adopt 前确认，但不阻断用户决策。
- feedback revision candidate 闭环。
- child candidate 保留 parent 关系，不自动 adopt，不覆盖正式正文。
- 真实 LLM rewrite / polish dogfood。
- Polish 微动作与隐性连续性 prompt tuning。
- 中文 prompt 链路 in-product dogfood。
- T8 写作质量闭环归档。

已知验证基线：

- Backend tests: passed。
- Frontend build: passed。
- Focused E2E: passed。
- Full E2E: 有大量 skipped，但阻断性失败已清理。
- Real LLM smoke: passed。
- Git 状态：T8 收口时为 clean。

关键判断：

T8 的主要价值已经形成：AI 生成结果默认进入 candidate，用户通过 preview / adopt / delete / feedback revision 控制正式正文。后续不应继续在 T8 内做大范围功能扩张，而应进入 T9 的产品化、测试治理和下一阶段设计。

## 2. T9 总目标

T9 的目标不是继续盲目新增写作功能，而是把已经可用的写作质量闭环变成更可发布、更可维护、更可验证的产品基线。

T9 总目标分为四类：

1. 产品化收口：准备一个稳定的 Release Candidate 或维护版。
2. 测试债务治理：把当前 skipped / fragile / mock 分散的问题梳理清楚。
3. 长文连续性设计：围绕 Story State / Continuity Anchors 做最小设计，而不是立刻上大纲系统。
4. 写作质量增强规划：设计下一轮 repair、score、comparison、warning explanation，但不急于实现。

## 3. 当前产品能力基线

当前 Moyun Studio 已经具备以下产品能力：

- Professional 主工作台可以打开项目、读取场景文件、编辑正文、保存文件。
- `sec-*.md` 被定义为单场景，是 AI 生成、重写、润色、审查的最小单位。
- 高风险写作操作默认生成 candidate，不直接覆盖正式正文。
- candidate 支持 preview / adopt / delete。
- candidate adopt 前保留安全检查，不绕过 hash / mtime / FILE_CONFLICT 机制。
- required / forbidden beats 可以作为生成前约束进入 prompt。
- validator 结果以 metadata 形式附加到 candidate，用于 advisory warning。
- feedback revision 可以基于 pending candidate 生成 child candidate。
- Lite 和 Professional 的关键写作链路已经被多轮 dogfood 覆盖。
- 真实 LLM 链路已可用于受控 smoke，不再只是 mock 流程。

当前仍存在的产品限制：

- 长篇连续性仍主要依赖 prompt、recent context 和人工控制，没有形成完整的 Story State 操作界面。
- full E2E 仍有较多 skipped，需要分类治理。
- warning 后还没有 automatic repair，只能通过用户反馈再生成 candidate。
- candidate comparison / quality score / explanation 仍处于设计前阶段。
- release 文档、版本定位和 known issues 需要统一。

## 4. 候选方向与优先级

### Priority 1：T9.1 Release Candidate / 维护版收口

这是 T9 的第一优先级。

目标是把 T8 已完成的能力整理成一个可交付、可说明、可回归的版本，而不是继续堆功能。

建议内容：

- 明确版本定位：`v0.1.3` 维护版或 `v0.2.0` RC。
- 更新 README。
- 更新 CHANGELOG。
- 新增或更新 KNOWN_ISSUES。
- 新增 Release checklist。
- 新增 Preflight checklist。
- 新增 Smoke checklist。
- 汇总 T8 capability summary。
- 明确已知限制和不承诺项。

阶段目标：

- 让外部用户或未来维护者能理解当前版本能做什么、不能做什么。
- 让发布前检查有固定清单。
- 让当前能力形成一个稳定 baseline。

风险等级：Risk C / Risk B。文档为主，涉及 release checklist 时为中低风险。

### Priority 2：T9.2 测试债务专项

第二优先级是测试债务治理。

当前 full E2E 已能跑通主要链路，但 skipped 数量仍然较多。T9.2 应先做分类和治理设计，再逐步修复。

建议内容：

- 分类 skipped E2E：环境依赖、真实 LLM、历史流程、缺 mock、已废弃流程。
- 提取通用 mock helpers。
- 清理不必要的 `waitForTimeout`。
- 统一 `spec 99` mock / smoke 规范。
- 分层 real backend smoke。
- 分层 real LLM smoke。
- 明确哪些测试进入 CI，哪些保留为手动 release gate。

阶段目标：

- 降低 E2E 维护成本。
- 减少“看似通过但实际没覆盖”的测试假象。
- 把真实 LLM 测试从日常 CI 中分离成可控 smoke。

风险等级：Risk C / Risk B。先做报告为 Risk C；修改测试基础设施为 Risk B。

### Priority 3：T9.3 长文连续性 / Story State 最小设计

第三优先级是长文连续性设计，但不建议立即实现大系统。

当前更适合先设计 `docs/design/t9-3-continuity-anchors.md`，聚焦“用户可控的连续性锚点”，而不是完整 Scene Plan 或自动全书规划。

建议关注：

- 当前场景发生前必须记住的事实。
- 人物状态锚点。
- 道具归属锚点。
- 地点 / 时间锚点。
- 伏笔状态锚点。
- 用户可以手动确认、修改、删除的 continuity anchors。
- anchors 如何进入 prompt。
- anchors 如何影响 validator 或 candidate warning。

不建议此阶段直接做：

- 全书自动规划。
- 大纲强依赖。
- 自动改写 story-state。
- 自动 repair 正文。

阶段目标：

- 找到比 Scene Plan 更轻、更可控的长文连续性方案。
- 让用户能理解并掌控 AI 需要记住什么。

风险等级：Risk C。设计优先，不直接改产品代码。

### Priority 4：T9.4 写作质量增强规划

第四优先级是下一轮写作质量增强规划。

它应该建立在 T9.1 发布收口、T9.2 测试治理和 T9.3 continuity design 之后。

候选方向：

- repair candidate。
- validator categories。
- quality score。
- candidate comparison。
- warning explanation。
- “为什么不建议 adopt” 的解释型 UI。
- 多候选稿横向比较。

阶段目标：

- 明确哪些增强真正有助于用户决策。
- 避免直接走 automatic repair 或复杂 dashboard。

风险等级：Risk C。只做规划；若实现则升为 Risk B+。

## 5. 暂缓事项

以下方向不建议在 T9 起步阶段立即推进：

- Scene Plan 大系统。
- automatic text repair。
- 自动全书规划。
- 多模型仲裁。
- adopted candidate revision。
- 复杂质量 dashboard。
- 自动修改正式正文。
- 自动 adopt。
- 大范围 prompt 架构重写。

原因：

这些方向都会显著增加状态复杂度、测试成本和用户误操作风险。当前更重要的是把已有 candidate 安全闭环、真实 LLM dogfood 和测试基线稳定下来。

## 6. 推荐执行顺序

推荐 T9 执行顺序：

1. T9.0：阶段方向评估与优先级排序。
2. T9.1：Release Candidate / 维护版收口。
3. T9.1-final：Release preflight / smoke checklist。
4. T9.2：测试债务专项。
5. T9.3：Continuity Anchors 最小设计。
6. T9.4：写作质量增强规划。

该顺序的核心理由：

- 先发布收口，避免在未稳定的基线上继续扩张。
- 再治理测试债务，提升后续开发安全性。
- 再设计长文连续性，避免过早进入大纲或 Scene Plan 系统。
- 最后规划更复杂的质量增强。

## 7. 第一批任务建议

### T9.1a：Version positioning and release docs audit

风险等级：Risk C。

目标：

- 决定版本定位：`v0.1.3` maintenance release 或 `v0.2.0` RC。
- 审计 README / CHANGELOG / release notes / known issues。
- 列出需要补齐的发布文档。

### T9.1b：Release docs update

风险等级：Risk B。

目标：

- 更新 README。
- 更新 CHANGELOG。
- 新增或更新 KNOWN_ISSUES。
- 补充 T8 capability summary。
- 明确 known limits。

### T9.1c：Preflight and smoke checklist

风险等级：Risk B。

目标：

- 固化发布前检查命令。
- 固化 browser smoke 路径。
- 固化 real LLM smoke 边界。
- 明确哪些测试失败应阻断 release。

### T9.2a：Skipped E2E classification report

风险等级：Risk C。

目标：

- 列出当前 skipped E2E。
- 按原因分类。
- 标记应恢复、应重写、应删除、应保留手动验证的测试。

### T9.3a：Continuity Anchors design doc

风险等级：Risk C。

目标：

- 新增 `docs/design/t9-3-continuity-anchors.md`。
- 定义最小 continuity anchors。
- 设计用户可控的修改入口。
- 设计 anchors 与 prompt / candidate / validator 的关系。

## 8. 每个任务的风险等级

| Task | 目标 | 风险等级 | 是否改代码 |
| --- | --- | --- | --- |
| T9.0 | 阶段规划 | Risk C | No |
| T9.1a | 版本定位与发布文档审计 | Risk C | No |
| T9.1b | 发布文档更新 | Risk B | No |
| T9.1c | Preflight / smoke checklist | Risk B | No |
| T9.2a | skipped E2E 分类 | Risk C | No |
| T9.2b | E2E mock helper 清理 | Risk B | Yes, tests only |
| T9.2c | real backend / real LLM smoke 分层 | Risk B+ | Possibly |
| T9.3a | Continuity Anchors 设计 | Risk C | No |
| T9.4a | 写作质量增强规划 | Risk C | No |

## 9. T9 必须遵守的安全边界

T9 期间必须继续遵守以下边界：

- 不自动覆盖正式正文。
- 不自动 adopt。
- 所有 AI 输出默认先进入 candidate。
- adopt 前正式正文保持不变。
- delete candidate 不影响正式正文。
- child candidate 不修改 parent candidate。
- validator 只做 advisory warning，不能直接修改正文。
- repair 只能创建 candidate，不能直接改正式正文。
- 不能绕过 FILE_CONFLICT / hash / expected_mtime。
- candidate source_path 必须是项目内相对路径。
- 不泄露 API Key。
- 不把 API Key 写入 localStorage、日志、截图或测试报告。
- 不修改 `workspace/` 用户数据。
- 不修改 `_misc/archive/` 归档数据。

## 10. 最终建议

建议 T9 立即进入 T9.1 Release Candidate / 维护版收口，而不是继续追加写作功能。

推荐路线：

1. 先完成 T9.1a / T9.1b / T9.1c，把当前能力变成可发布基线。
2. 再进入 T9.2，清理测试债务，尤其是 skipped E2E 和真实 LLM smoke 分层。
3. 然后进入 T9.3，用 Continuity Anchors 设计解决长文连续性，而不是直接引入重型 Scene Plan。
4. 最后进入 T9.4，规划 repair candidate、quality score、candidate comparison 等增强。

结论：

T8 已经完成“写作质量闭环”的基本产品能力。T9 的第一目标应是产品化和稳定化，而不是继续扩大生成链路复杂度。
