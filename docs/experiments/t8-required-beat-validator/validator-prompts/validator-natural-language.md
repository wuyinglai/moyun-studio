# Validator: Natural Language

Outputs Markdown and human-readable evidence.

```text
你是小说连续性审稿人。请检查正文是否满足 required beats，并标记 forbidden violations。

Case:
{{ case_json }}

Generated text:
{{ text }}

请用 Markdown 输出：

## Required Beats

逐条列出：
- id
- status: satisfied / partial / missing
- evidence
- reason

## Forbidden Violations

逐条列出：
- id
- violated: yes / no
- evidence

## Logic Risks

列出人物状态、地点、道具、时间线、新实体方面的风险。

## Overall Status

输出 satisfied / needs_repair / unusable。
```
