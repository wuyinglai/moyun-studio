{% if continuity_anchor_items %}
## 连续性锚点（长期不可违反）
以下锚点来自作者手动维护，用于保持长篇连续性。它们不是本场必须全部出现的爽点，但正文不能违反。
{% for anchor in continuity_anchor_items %}
- [{{ anchor.priority }} / {{ anchor.type }} / {{ anchor.scope }}] {{ anchor.title }}：{{ anchor.content }}
{% endfor %}
{% endif %}
