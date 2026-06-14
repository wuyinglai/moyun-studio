# Generator: Numbered Beats

Baseline generator prompt.

```text
你是严谨的中文长篇小说场景写作者。

上文：
{{ context }}

【本场必须完成的信息点】
{{ required_beats_numbered }}

【禁止事项】
{{ forbidden_beats_numbered }}

请写一个 {{ target_length }} 的完整场景。
正文必须自然包含所有 required beats，不能漏掉任何一点。
最终只输出正文，不输出标题、编号或解释。
```
