# T9 阶段规划：产品化收口与下一阶段稳定规划

> 阶段：T9
> 类型：Stage Planning / Documentation
> 风险等级：Risk C
> 状态：v0.2.1 已发布（T9.1-T9.5 完成）
> 日期：2026-06-16 规划，2026-06-17 v0.2.1 发布
> 前置依赖：T8 写作质量闭环已归档，见 `docs/archives/t8-writing-quality-closure.md`
> 发布标签：`v0.2.1`
> 发布提交：`fa99483`
> GitHub Release：https://github.com/wuyinglai/moyun-studio/releases/tag/v0.2.1

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

✅ **已完成**（2026-06-16，作为 v0.2.0 发布）。

已交付内容：

- 明确版本定位：`v0.2.0` Writing Quality Loop Developer Preview。
- 更新 README / CHANGELOG。
- 新增 Release checklist / Preflight checklist / Smoke checklist。
- 汇总 T8 capability summary。
- tag `v0.2.0` 已推送，GitHub Release 已发布。

### Priority 2：T9.2 测试债务专项

✅ **已完成**（2026-06-17，作为 v0.2.1 的一部分）。

已交付内容：

- Focused E2E recovery（`tests/e2e/14-candidate-workflow.spec.ts` 23 passed）。
- Real backend / real LLM smoke 分层。
- 明确 release gate 测试集与日常 CI 测试集的分界。
- Continuity anchors 测试（`test_continuity_anchors.py` 7 passed）。

### Priority 3：T9.3 长文连续性 / Story State 最小设计

✅ **已完成**（2026-06-17，作为 v0.2.1 的一部分）。

已交付内容：

- Continuity Anchors 设计已归档：`docs/design/t9-3-final-continuity-anchors-closure.md`。
- 定义 5 类锚点：人物状态、道具归属、地点/时间、伏笔状态、必须记住的事实。
- `ContinuityAnchorService.list_active()` / `metadata()` 实现。
- anchors 进入 prompt + 影响 quality continuity 评分。
- 未引入大纲强依赖或自动全书规划。

### Priority 4：T9.4 写作质量增强

✅ **已完成**（2026-06-17，作为 v0.2.1 的一部分）。

已交付内容（从规划→实现）：

- **Repair Candidate MVP** — `CandidateAction.REPAIR`，`create_repair_candidate()`，不修改 parent/source。
- **Candidate Quality Metadata MVP** — 5 维度（instruction_following, continuity, style_preservation, change_scope, forbidden_check）。
- **Continuity Anchors metadata 修复** — `create_candidate()` 自动从 service 获取 active anchors。
- **Safety boundary verification** — adopted/discarded parent 不可 revision/repair；repair 创建新 child candidate 仅。
- **Real LLM dogfood** — Agnes AI 8 个真实中文写作场景验证通过。

### Priority 5：T9.5 Pipeline Prompt Rendering Cleanup

✅ **已完成**（2026-06-17，作为 v0.2.1 的一部分）。

已交付内容：

- 归档问题已不存在：prompt 文件路径正常，无需从 archive 恢复。
- `docs/design/t9-5-pipeline-prompt-rendering-cleanup.md` 已归档。
- 115 backend tests passed（完整回归）。

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

## 6. 推荐执行顺序 ✅ 已完成

T9 推荐执行顺序已全部执行：

1. ✅ T9.0：阶段方向评估与优先级排序。
2. ✅ T9.1：Release Candidate / 维护版收口（v0.2.0）。
3. ✅ T9.1-final：Release preflight / smoke checklist。
4. ✅ T9.2：测试债务专项（focused E2E + real LLM smoke 分层）。
5. ✅ T9.3：Continuity Anchors 最小设计 + 最小实现。
6. ✅ T9.4：写作质量增强（Quality Metadata + Repair Candidate + Real LLM dogfood）。
7. ✅ T9.5：Pipeline Prompt Rendering Cleanup。

交付成果：

- **v0.2.0`：Writing Quality Loop Developer Preview（2026-06-16，tag `v0.2.0`）。
- **v0.2.1`：Writing Quality Enhancement Release（2026-06-17，tag `v0.2.1`，commit `fa99483`）。
- 完整发布文档：`docs/releases/v0.2.1-rc-notes.md`、`docs/releases/v0.2.1-rc-checklist.md`、`docs/releases/v0.2.1-release-final-report.md`。

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

T9 阶段已完成：v0.2.0 + v0.2.1 已发布。

### T9 交付总结

| 项目 | 状态 | 备注 |
|------|------|------|
| v0.2.0 Writing Quality Loop Developer Preview | ✅ Released | 2026-06-16, tag `v0.2.0` |
| v0.2.1 Writing Quality Enhancement Release | ✅ Released | 2026-06-17, tag `v0.2.1`, commit `fa99483` |
| Release gate backend tests | ✅ 52 passed | 完整 115 passed |
| Frontend build | ✅ passed | 3435 modules |
| Focused E2E | ✅ 23 passed | `14-candidate-workflow.spec.ts` |
| Full mock E2E | ✅ 77 passed | 93 skipped |
| Real LLM dogfood | ✅ 8 cases | Agnes AI `agnes-2.0-flash` |
| Safety boundaries | ✅ verified | repair/revision 不修改 parent/source |
| API key 安全检查 | ✅ clean | 无真实 key 泄露 |

### 推荐路线

T9 阶段结束，建议进入 **T10 阶段** 或 **v0.2.2 维护迭代**：

1. **v0.2.2** — 小版本维护：guardrails 噪音清理、T9.4 文档合并、quality score UI 迭代。
2. **测试债务持续治理** — 把 skipped E2E 逐步恢复或删除。
3. **下一阶段规划** — 定义 T10 目标（Story State 操作界面、candidate comparison、quality explanation）。

### 结论

T8 + T9 已经完成"写作质量闭环"从 MVP 到可发布版本的完整路径。v0.2.1 是当前的稳定发布基线。下一步应聚焦文档整合和小范围维护，而非继续扩大功能范围。
