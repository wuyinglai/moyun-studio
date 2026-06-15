你正在根据作者反馈修订一个小说候选稿。

重要规则：
- 这是生成新的 child candidate，不是修改正式正文。
- 正式正文事实锚点不可违背。
- 父候选稿是需要修订的草稿，不是最终事实。
- 不要自动覆盖正式正文。
- 不要自动采用候选稿。
- 不要新增重要人物、组织、道具、地点、时间线设定，除非用户反馈明确要求。
- 输出完整修订后的候选稿正文。
- 不要输出解释、评分、列表、标题说明或 Markdown 元信息。

【source_path】
{{ source_path }}

【正式正文事实锚点】
{{ official_source_text }}

【父候选稿】
{{ parent_candidate_text }}

【用户反馈】
{{ feedback_text }}

{% if quick_actions %}
【快捷反馈】
{% for action in quick_actions %}
- {{ action }}
{% endfor %}
{% endif %}

【修改范围】
{{ repair_scope }}

{% if parent_beat_validation_summary %}
【父候选稿信息点检查摘要】
状态：{{ parent_beat_validation_status }}
摘要：{{ parent_beat_validation_summary }}
{% endif %}

{% if required_beats %}
【必须保留或补上的信息点】
{% for beat in required_beats %}
{{ loop.index }}. {{ beat.text }}
{% endfor %}
{% endif %}

{% if forbidden_beats %}
【禁止出现或禁止提前揭晓的内容】
{% for beat in forbidden_beats %}
{{ loop.index }}. {{ beat.text }}
{% endfor %}
{% endif %}

请根据用户反馈修订父候选稿。修订时以正式正文事实锚点为准，保留已经满足的信息点，补足缺失内容，并避免引入新错误。

现在只输出完整修订后的候选稿正文。
