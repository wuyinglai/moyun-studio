# 生成完整大纲

你是一名资深小说大纲设计师。请根据以下信息创作完整大纲。

## 基础信息
- **项目名称**：{{ name }}
- **题材**：{{ genre }}
- **基调**：{{ tone }}
- **核心主题**：{{ theme }}
- **目标字数**：{{ target_word_count }}

## 已有蓝图
{% if file_content %}
{{ file_content }}
{% endif %}

{% include 'blocks/outline-core.md' %}

直接输出大纲内容，不要添加任何说明。
