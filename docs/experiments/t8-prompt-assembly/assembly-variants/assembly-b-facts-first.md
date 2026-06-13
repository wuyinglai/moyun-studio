# Assembly B: Facts-First Assembly

This variant tests ordering and priority rather than simply piling on more rules.

Facts and forbidden changes are placed before context so the model sees hard constraints before prose material.

## Assembly Template

```text
【任务】
写下一场景正文，约 500-700 中文字，只输出正文。

【不可违反事实】
人物状态：
{{character_facts}}

道具归属：
{{item_facts}}

地点限制：
{{location_facts}}

时间线：
{{timeline_facts}}

禁止事项：
{{forbidden}}

【本场目标】
{{goal}}

【参考上文】
{{context}}

【输出要求】
- 用动作、环境、对话潜台词推进。
- 不要新增未允许的人物、组织、能力、道具、地点或关键设定。
- 不要提前揭晓伏笔。
- 不要解释自检过程。
```

