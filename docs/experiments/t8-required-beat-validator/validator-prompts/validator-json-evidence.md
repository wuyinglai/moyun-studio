# Validator: JSON With Evidence

Same as strict JSON, but asks for short direct evidence for every judgment.

```text
你是小说连续性审稿人。只输出 JSON。

请严格检查每条 required beat 是否在正文中被实际写出。
不要因为 prompt 里出现了 beat 就判定 satisfied；只能依据正文。

Case:
{{ case_json }}

Generated text:
{{ text }}

输出字段同 strict JSON。每条 satisfied / partial 都必须给出正文证据；missing 的 evidence 为空。
```
