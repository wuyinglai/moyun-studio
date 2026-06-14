# Validator: Strict JSON

Outputs machine-readable JSON only.

```text
你是小说连续性审稿人。只输出 JSON，不输出 Markdown 或解释。

Case:
{{ case_json }}

Generated text:
{{ text }}

JSON schema:
{
  "case_id": "case id",
  "all_required_beats_satisfied": false,
  "required_beats": [
    {
      "id": "beat id",
      "status": "satisfied|partial|missing",
      "evidence": "text evidence or empty string",
      "confidence": 0.0
    }
  ],
  "forbidden_violations": [
    {
      "id": "forbidden id",
      "violated": false,
      "evidence": ""
    }
  ],
  "logic_risks": [
    {
      "type": "character_state|item|timeline|location|new_entity|style|other",
      "description": "risk description",
      "severity": "low|medium|high"
    }
  ],
  "overall_status": "satisfied|needs_repair|unusable"
}
```
