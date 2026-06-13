# Assembly C: Plan -> Check -> Draft Assembly

This variant simulates a three-layer assembly:

1. build a scene plan from facts and prior context;
2. run a checker against the plan;
3. draft only from a checked plan.

The goal is not only better text. The goal is an auditable intermediate layer that can expose problems before prose generation.

## C1: Scene Plan Assembly

```text
【任务】
根据事实块和上文，为下一场景生成 scene plan，不写正文。

【事实块】
{{facts}}

【禁止改变项】
{{forbidden}}

【本场目标】
{{goal}}

【参考上文】
{{context}}

【输出格式】
输出 JSON：
{
  "start_state": "...",
  "allowed_characters": ["..."],
  "allowed_locations": ["..."],
  "allowed_items": ["..."],
  "scene_goal": "...",
  "required_beats": ["..."],
  "forbidden_mistakes": ["..."],
  "ending_hook": "..."
}
```

## C2: Logic Checker Assembly

```text
【任务】
检查 scene plan 是否违反事实。只输出 JSON。

【事实块】
{{facts}}

【禁止改变项】
{{forbidden}}

【scene plan】
{{plan}}

【输出格式】
{
  "valid": true,
  "issues": [],
  "risk_level": "low|medium|high",
  "fix_suggestions": []
}
```

## C3: Draft Assembly

```text
【任务】
根据已检查的 scene plan 写下一场景正文。

【scene plan】
{{plan}}

【checker result】
{{checker}}

【参考上文】
{{context}}

【硬性要求】
- 不得改变 scene plan 中的人物、地点、道具、时间线和禁令。
- 不得新增 scene plan 未允许的人物、组织、能力或关键设定。
- 只输出正文，不输出计划或解释。
```

