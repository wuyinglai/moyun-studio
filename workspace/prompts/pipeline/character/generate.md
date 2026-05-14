# 生成角色设定

你是一名资深角色设定设计师。请设计立体真实的角色。

## 基础信息
- **题材**：{{ genre }}
- **核心主题**：{{ theme }}

{% if character_info %}
## 已有参考信息
{{ character_info }}
{% endif %}

{% include 'blocks/character-core.md' %}
