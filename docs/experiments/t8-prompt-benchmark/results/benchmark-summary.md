# T8.0 Prompt Quality Benchmark Summary

## 1. Background

Moyun Studio v0.2.0-alpha has a usable real-LLM path, but small-model long-form generation still shows logic drift: injury state changes, item ownership moves, future information appears early, locations jump, and foreshadowing can be over-explained.

This benchmark isolates the first layer of the problem: whether prompt wording alone can improve output under ideal, manually curated input conditions. It does not test Moyun frontend, backend prompt assembly, pipeline behavior, candidate adoption, or memory updates.

## 2. Test Model

- Model: `agnes-2.0-flash`
- API base: `https://apihub.agnes-ai.com/v1`
- Real LLM calls: Yes
- API key recorded: No
- Timeout: No timeout in the valid run
- Product code modified: No

## 3. Test Method

Six adversarial fiction-continuity samples were created. Each sample contains:

- 上文摘要
- 必须保持的事实
- 禁止改变的事实
- 本场生成目标
- 预期风险点
- 评价指标

Each case was run against three prompt variants:

- Prompt A: direct generation baseline
- Prompt B: hard-constraint fact-first generation
- Prompt C: scene plan first, then draft from plan

Scoring prioritizes hard logic over prose. Each output receives 0-2 on nine dimensions:

- 人物状态一致性
- 道具归属一致性
- 时间线一致性
- 地点一致性
- 禁止事项遵守
- 场景目标完成
- 伏笔处理
- 逻辑矛盾数量
- 可用性

Maximum score per case is 18. Maximum total per prompt over six cases is 108.

## 4. Prompt Variants

| Prompt | Strategy | Intended Advantage |
| --- | --- | --- |
| A | 直接根据上文写下一场景 | Baseline; least friction and fastest |
| B | 事实优先、硬约束、自检 | Push model to obey facts before style |
| C | 先生成场景计划，再按计划写正文 | Make state, allowed entities, forbidden mistakes explicit before prose |

## 5. Test Cases

| Case | Focus | Main Risk |
| --- | --- | --- |
| case-01-injury-state | 人物受伤状态 | 沈知夏左臂受伤却突然用力、攀爬、战斗 |
| case-02-item-ownership | 道具归属 | 银色芯片突然换持有人或被提前破解 |
| case-03-timeline | 时间顺序 | 第三天事件或证据提前出现 |
| case-04-location | 地点限制 | 被困地下二层却瞬移到灰塔实验室 |
| case-05-no-new-entities | 禁止新增实体 | 突然出现导师、黑客盟友、新组织或系统 |
| case-06-foreshadowing-relationship-style | 伏笔、关系、风格 | 第七层协议揭晓过度，关系进展过快，文风跑偏 |

## 6. Score Table

| Prompt | 总分 | 平均分 | 逻辑矛盾/风险命中数 | 可用候选数 | 平均耗时 | 结论 |
| --- | -: | -: | -: | -: | -: | --- |
| A 直接生成 | 105/108 | 17.50 | 1 | 5/6 | 6.91s | 在理想输入下意外稳定，速度最好，但没有中间可审计计划 |
| B 硬约束 | 98/108 | 16.33 | 6 | 3/6 | 19.56s | 约束变多后没有更稳，反而出现受伤动作、时间信息过确定、伏笔过度解释 |
| C 场景计划 | 105/108 | 17.50 | 2 | 5/6 | 22.41s | 总分与 A 持平，速度最慢，但有可检查的计划层，适合后续装配测试 |

## 7. Per-Case Findings

| Case | A | B | C |
| --- | --- | --- | --- |
| injury-state | 15: 写出左手用力攥住背包带 | 15: 左手/左臂仍被写成可发力 | 15: 左手用力且伤口漂移到右肩 |
| item-ownership | 18 | 18 | 18 |
| timeline | 18 | 14: 角色知道爆炸过于确定，未来事件表达越界 | 18 |
| location | 18 | 18 | 18 |
| no-new-entities | 18 | 18 | 18 |
| foreshadowing-relationship-style | 18 | 15: 第七层协议解释过多 | 18 |

## 8. Main Problems by Prompt

### Prompt A

Prompt A is surprisingly strong when the input is short, clean, and explicit. Its main failure is subtle state drift: in the injury case it remembered “受伤” but still let the injured left hand perform a forceful action. This suggests direct generation can pass many easy logic checks, but it has no explicit mechanism for catching small embodied-state violations.

### Prompt B

Prompt B did not improve reliability in this run. The hard-constraint wording may have increased the model's tendency to restate, rationalize, or over-specify hidden information. It produced the most risk hits:

- Injury state still failed.
- Timeline became too certain about explosion information.
- Foreshadowing revealed too much about the meaning of the seventh-layer protocol.

The lesson is important: simply adding more prohibitions is not enough. A small model may treat constraints as content to dramatize rather than boundaries to obey.

### Prompt C

Prompt C did not beat Prompt A on total score, but it has a different product value: the scene plan provides an auditable intermediate artifact. When C failed the injury sample, the failure could be traced to plan/draft state handling rather than being buried directly in prose.

Its cost is latency: C uses two model calls and averaged 22.41 seconds in this run. If used in product, it should be reserved for higher-risk scenes, not every lightweight continuation.

## 9. Best Prompt

Best single-output prompt by score and speed: Prompt A.

Best prompt architecture for Moyun's long-form reliability roadmap: Prompt C.

Reason: A is fast and works under ideal short inputs, but it gives no structured handle for later validation. C creates a scene-plan surface that can be validated, edited, stored, and compared before prose generation. That matters more for long-form continuity than this small benchmark's tied score.

## 10. Is Prompt-Only Optimization Enough?

No. Prompt-only optimization helps frame the problem but does not fully solve small-model continuity.

The strongest evidence is the injury-state case: all three prompt variants failed some version of the same embodied-state constraint. This is exactly the kind of small contradiction users reported: one obvious mistake gets fixed, another small one appears.

## 11. Should T8.1 Start?

Yes, but with a narrow scope.

T8.1 should test prompt assembly and validation, not simply rewrite production prompts. Recommended focus:

1. Add a structured facts block that separates current state, immutable facts, forbidden changes, scene goal, and open foreshadowing.
2. Test a scene-plan validator before drafting.
3. Test a post-draft consistency checker that specifically verifies injury/action compatibility, item ownership, time, location, and foreshadowing bounds.
4. Compare direct generation vs scene-plan-plus-validation under the same real pipeline input.

## 12. Next-Stage Recommendations

1. Do not replace current production prompts solely with Prompt B-style hard constraints.
2. Use Prompt C as the basis for T8.1 because it creates an inspectable scene-plan artifact.
3. Add targeted validators for common small-model mistakes:
   - injured body part cannot perform forceful action
   - item holder must remain stable
   - future evidence cannot appear early
   - current location cannot jump without transition
   - foreshadowing can be named but not fully explained
4. Keep direct Prompt A as a latency baseline.
5. For product use, consider a hybrid:
   - low-risk continuation: direct generation with compact fact block
   - high-risk continuity scene: scene plan -> validator -> draft -> consistency checker

## 13. Raw Artifacts

- Prompt files: `docs/experiments/t8-prompt-benchmark/prompts/`
- Case files: `docs/experiments/t8-prompt-benchmark/cases/`
- Raw generations: `docs/experiments/t8-prompt-benchmark/results/raw-generations.md`
- Scored JSON: `docs/experiments/t8-prompt-benchmark/results/benchmark-data.json`

## 14. Final Recommendation

是否进入 T8.1 Prompt 装配测试：Yes

理由：Prompt 单体优化并没有彻底解决小模型逻辑问题，但 Prompt C 证明“场景计划”值得进入装配层测试。下一步不应只调一句 prompt，而应测试“事实块 + 场景计划 + 校验器 + 正文生成”的组合是否能稳定压低小错误。
