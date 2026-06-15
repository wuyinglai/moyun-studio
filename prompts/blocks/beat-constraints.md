{% if required_beats %}
## 本次必须保留 / 补上的信息点
{% for beat in required_beats %}
{% if beat is mapping %}- {{ beat.text }}{% else %}- {{ beat }}{% endif %}
{% endfor %}
{% endif %}

{% if forbidden_beats %}
## 本次禁止新增 / 禁止揭晓
{% for beat in forbidden_beats %}
{% if beat is mapping %}- {{ beat.text }}{% else %}- {{ beat }}{% endif %}
{% endfor %}
{% endif %}
