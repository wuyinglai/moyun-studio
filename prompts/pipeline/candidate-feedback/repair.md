你正在根据系统警告信息修复一个候选稿。
重要规则：
- 这是生成新的 child candidate，不是修改正式正文
- 正式正文事务点不可覆盖
- 父候选稿是待修复的内容，不是最终事实
- 不要自动覆盖正式正文
- 不要自动采用候选稿
- 不要新增重要人物、组织、地点、时间线设定，除非用户反馈明确要求
- 输出修复后的完整候选稿正文
- 不要输出解释、评分、列表、标题或任何额外信息。

## 源文件路径：{{ source_path }}

{% include 'blocks/continuity-anchors.md' %}

## 正式正文事务点：{{ official_source_text }}

## 父候选稿：{{ parent_candidate_text }}

## 系统警告信息：
{{ warnings_text }}

{% if required_beats %}
## 必须保留或补上的信息点：{% for beat in required_beats %}
{{ loop.index }}. {{ beat.text }}
{% endfor %}
{% endif %}

{% if forbidden_beats %}
## 必须避免出现的内容：{% for beat in forbidden_beats %}
{{ loop.index }}. {{ beat.text }}
{% endfor %}
{% endif %}

{% if extra_instruction %}
## 用户补充说明：
{{ extra_instruction }}
{% endif %}

请根据以上警告信息修复父候选稿。修复时以正式正文事务点为基准，保留已经满足的信息点，修复存在问题的内容，并严格遵守禁止项约束。
现在只输出修复后的候选稿正文。
