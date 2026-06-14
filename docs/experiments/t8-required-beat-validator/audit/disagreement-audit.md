# T8.2.3 Validator Disagreement Manual Audit

## 1. Background

T8.2.2 created a reusable required-beat validator benchmark and ran 6 real LLM flows.

Key T8.2.2 metrics:

| Metric | Value |
| --- | ---: |
| Runs | 6 |
| Initial beat completion | 95.24% |
| JSON parse rate | 100.00% |
| Validator agreement | 50.00% |
| Repair success | 33.33% |
| Final usable rate | 66.67% |

This audit reads the existing T8.2.2 artifacts and manually inspects the disagreement runs. It does not modify product code, production prompts, pipeline, frontend, backend, candidate logic, release tags, or API key configuration.

## 2. Audit Scope

Input files:

- `docs/experiments/t8-required-beat-validator/results/scored/`
- `docs/experiments/t8-required-beat-validator/results/raw/`
- `docs/experiments/t8-required-beat-validator/results/validator-summary.md`
- `docs/experiments/t8-required-beat-validator/results/validator-summary.json`
- `docs/experiments/t8-required-beat-validator/results/validator-summary.csv`

Disagreement runs:

| Run | Case | Disagreement Source |
| --- | --- | --- |
| `case-02-ending-hook-s1` | ending hook | rule/natural mismatch; JSON/rule agree on repair need for different reasons |
| `case-03-injury-limitation-s1` | injury limitation | rule vs JSON; rule vs natural |
| `case-04-item-handover-s1` | item handover | rule vs JSON; rule vs natural |

## 3. Manual Judgments

### case-02-ending-hook-s1

Human judgment: `needs_repair`

Required beats:

| Beat | Human Status | Evidence | Comment |
| --- | --- | --- | --- |
| beat-1 familiar footsteps | satisfied | "皮鞋敲击水磨石地面的声音" | The familiar footstep signal is present. |
| beat-2 Lin recognizes footsteps | satisfied | "这个频率……他在无数个深夜的梦境边缘听过这个声音" | Semantic recognition is present even without the exact word "认出". |
| beat-3 ending stops at Lin looking up | partial | "他缓缓抬起头，目光……投向……通风口" | The text contains the action but continues past it into a new vent hook. |
| forbid-1 identity reveal | not violated | "那个名字在他舌尖打转，却被他强行咽回喉咙" | The reader does not learn the name, role, or relationship. |

Closest validator: `mixed`

Natural validator is closest on semantic recognition and forbidden judgment. JSON is right that the sample needs repair, but its forbidden-violation reason over-infers identity reveal. Rule-based precheck is too loose on the terminal ending and too strict on the forbidden keyword `那是`.

Repair audit:

The repair output is mostly successful by human judgment: it adds "他听出了这脚步声", removes "是那个人", and ends at "他缓缓抬起头." The benchmark marked repair failure mainly because rule-based forbidden matching remains brittle.

### case-03-injury-limitation-s1

Human judgment: `pass`

Required beats:

| Beat | Human Status | Evidence | Comment |
| --- | --- | --- | --- |
| beat-1 left arm injury | satisfied | "她的左臂无力地垂在身侧" | Clear injury state. |
| beat-2 cannot high-intensity fight | satisfied | "更别提进行任何高强度的格斗动作" | Clear action limitation. |
| beat-3 helps by observation/judgment/reminder | satisfied | "脚步声太杂，说明他们在分头搜索……他在试探空心墙" | She helps through auditory/environmental analysis. |
| beat-4 Lin performs main action | satisfied | "林澈……将闪光弹掷向走廊尽头" | Lin drives the action. |
| forbid-1 high-action Shen | not violated | Shen stays hidden and does not climb/fight. | No violation. |

Closest validator: `natural`

Natural and JSON both correctly recognize beat-3 semantically. Rule-based precheck misses it because the case keywords did not include acceptable paraphrases such as "说明", "分析", "指了指", "听出", or "地形".

Repair audit:

Repair was unnecessary. It was triggered by a rule-based false positive and only adds explicit "观察" phrasing. This is a warning that rule-based precheck should not independently trigger repair.

### case-04-item-handover-s1

Human judgment: `needs_repair`

Required beats:

| Beat | Human Status | Evidence | Comment |
| --- | --- | --- | --- |
| beat-1 medicine remains with Shen | satisfied | "沈知夏的手指紧紧扣住那支透明药剂" | Medicine remains under Shen's control. |
| beat-2 Lin only sees label | satisfied | "他只能勉强辨认出标签上那行模糊的小字" | Label-only observation appears. |
| beat-3 enemy does not take medicine | satisfied | Enemy loses target; medicine remains with Shen. | No enemy handover. |
| beat-4 side-effect hint | satisfied | "药剂的副作用已经开始显现" | Side-effect hint appears, though too strong. |
| forbid-1 enemy takes medicine | not violated | No such event. | No violation. |
| forbid-2 complete medicine usage known | violated | "她知道，这支药剂能暂时屏蔽他们的生物信号..." | The scene reveals usage and side effect too explicitly to the reader. |

Closest validator: `json`

JSON correctly catches the knowledge/reveal boundary violation. Rule-based precheck is too loose because its forbidden keywords only cover exact phrases like "林澈已经知道药剂用途". Natural validator misses the forbidden violation and treats the problem mostly as logic risk.

Repair audit:

Repair partially removes direct usage explanation but keeps a weak substitute: "未注射，仅接触/微量挥发就副作用显现". JSON re-validation still reports `needs_repair`. Human audit agrees the repaired text still needs review because it replaces one explanation problem with another strained mechanism.

## 4. Validator Comparison

| Run | Rule | Natural | JSON | Closest |
| --- | --- | --- | --- | --- |
| ending hook | Too loose on terminal hook, too strict on `那是` | Best semantic read, but misses terminal-position strictness | Correct repair need, wrong forbidden reason | mixed |
| injury limitation | Too strict; keyword false positive | Correct | Correct, but schema output mixes forbid item into required list | natural/json |
| item handover | Too loose; misses semantic forbidden reveal | Catches logic risk, misses explicit forbidden boundary | Correct | json |

Aggregate closest validator:

| Validator | Count |
| --- | ---: |
| rule | 0 |
| natural | 1 |
| json | 1 |
| mixed | 1 |

## 5. False Positive / False Negative Analysis

False positives:

1. `case-02` rule-based forbidden: keyword `那是` is too broad.
2. `case-02` JSON forbidden: over-infers identity reveal from "是那个人".
3. `case-03` rule-based missing beat-3: semantic satisfaction missed due narrow keywords.
4. `case-02` benchmark repair failure: metric false negative after a mostly successful repair.

False negatives:

1. `case-02` rule-based beat-3: sees "抬起头" but does not verify terminal position.
2. `case-04` rule-based forbid-2: misses reader-facing explanation of drug purpose.
3. `case-04` natural validator forbid-2: downgrades boundary violation into a logic risk.

Hardest beat type:

- Ending hooks with terminal-position constraints.
- Knowledge-boundary / reader-reveal constraints.
- Semantic "help by observation/judgment" beats that can be phrased many ways.

## 6. Repair Failure Analysis

| Run | Repair Trigger | Human Result | Failure Type |
| --- | --- | --- | --- |
| ending hook | JSON/rule repair need | Mostly successful | benchmark metric false negative |
| injury limitation | rule false positive | unnecessary but harmless | unnecessary repair |
| item handover | real forbidden violation | still needs review | retained weak logic |

Repair should remain experimental. It should not automatically overwrite or adopt. At most it should create a repair candidate with a validator warning.

## 7. Case / Schema / Prompt Problems

### Case Schema

Add fields:

```json
{
  "acceptable_paraphrases": ["说明", "分析", "听出", "意识到"],
  "required_semantic_condition": "沈知夏通过观察、听觉判断或地形分析帮助林澈，而不是体力行动。",
  "forbidden_semantic_condition": "正文不得向读者揭晓来人的姓名、身份、组织归属或与主角的具体关系。",
  "terminal_position_required": true,
  "knowledge_boundary": {
    "character": "林澈",
    "may_know": ["药剂标签"],
    "must_not_know": ["药剂完整用途", "副作用机制"],
    "reader_reveal_allowed": false
  },
  "violation_threshold": "explicit_name_or_role | specific_identity_hint | reader_reveal"
}
```

### Validator Prompt

Change validator prompt requirements:

- Do not judge only by keyword presence.
- Quote evidence from generated text for every satisfied or partial beat.
- Distinguish keyword mention from semantic satisfaction.
- Distinguish character knowledge from reader-facing reveal.
- For ending hooks, check whether the required ending action is truly at the terminal position.
- If uncertain, mark `partial`, not `satisfied`.
- Do not place forbidden beats inside `required_beats`; keep them only in `forbidden_violations`.

### Rule-based Precheck

Recommendation:

Rule-based precheck should become a weak signal only. It can flag audit candidates but should not independently trigger repair.

Specific fixes:

- Remove broad forbidden keywords such as `那是`.
- Add acceptable paraphrase lists per beat.
- Add terminal-position checks for ending hooks.
- Add semantic category labels so rule can report `weak_missing` rather than `missing`.
- Separate `required_keyword_hit` from `semantic_satisfied`.

## 8. Next Benchmark Corrections

Do not immediately run `--samples 2` with the current schema/prompt. It will amplify noisy disagreement.

Before expanding samples:

1. update case JSON with semantic condition fields;
2. revise JSON validator prompt to use `partial` for ambiguous evidence;
3. revise rule-based scoring so it does not trigger repair alone;
4. add manual-audit fields to scored output;
5. add terminal hook evaluation for ending cases;
6. add reader-reveal vs character-knowledge boundary fields.

## 9. Productization Recommendation

Current recommendation: **B. 暂不扩大样本，先修正 validator prompt / case schema。**

Reasons:

- Agreement is only 50%.
- Rule-based precheck created at least one unnecessary repair.
- JSON is parse-stable but can over-infer ambiguous identity hints.
- Repair is not reliable enough for automation.

Do not enter T8.3 yet. Validator warning remains promising, but the benchmark needs schema and prompt refinement first.

## 10. Next Step

T8.2.4 should implement the schema/prompt/scoring corrections above, then rerun the benchmark with `--samples 2`. Automatic repair should stay out of product design until repaired outputs pass human audit more consistently.
