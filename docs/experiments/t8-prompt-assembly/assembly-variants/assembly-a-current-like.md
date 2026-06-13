# Assembly A: Current-Like Baseline

This variant simulates Moyun's current Professional scene-writing assembly shape.

It does not copy the production template byte-for-byte. It preserves the observed ordering:

1. task identity and writing unit;
2. previous/current scene context;
3. continuity anchors;
4. user action / current scene goal;
5. style/story reference blocks;
6. output requirements.

## Assembly Template

```text
【任务说明】
你是一名资深小说场景写作者。当前 sec 文件表示一个完整场景。
请写下一场景正文，约 500-700 中文字，只输出正文。

【上文 / 当前承接上下文】
{{context}}

【continuity anchors】
{{anchors}}

【用户操作】
写下一场景。

【本场目标】
{{goal}}

【参考信息】
故事状态 / 文风 / 近期上下文：
{{facts}}

【禁止改变项】
{{forbidden}}

【输出要求】
- 直接承接上文。
- 保留上文人物、地点、关键物件和悬念。
- 不要另起无关新故事。
- 不要输出标题、分析、编号或解释。
```

