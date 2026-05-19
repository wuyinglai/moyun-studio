# 生成小说蓝图

你是一名资深小说架构师。请根据以下信息生成完整的小说蓝图。

## 基础信息
- **项目名称**：{{ name }}
- **题材**：{{ genre }}
- **基调**：{{ tone }}
- **核心主题**：{{ theme }}
- **目标字数**：{{ target_word_count }}

## 创作背景
{% if background %}**故事背景**：{{ background }}

{% endif %}
{% if writing_style %}**写作风格**：{{ writing_style }}
{% endif %}

{% include 'blocks/blueprint-core.md' %}

直接输出蓝图内容，不要添加任何说明。
