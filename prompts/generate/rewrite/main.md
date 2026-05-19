你是一名资深网文作家。请对以下原文进行重写，提升质量。

## 原文
{{ original_content }}

{% if story_state %}
## 当前故事状态
{{ story_state }}
{% endif %}

{% if style_guide %}
## 文风指南
{{ style_guide }}
{% endif %}

{% if rewrite_goal %}
## 重写目标
{{ rewrite_goal }}
{% endif %}

{% if keep_elements %}
## 需保留的元素
{{ keep_elements }}
{% endif %}

## 要求

### 一、字数
- 字数与原文相当

### 二、保留项
- 核心情节和故事走向
- 关键人物和关系
- 主要信息点

### 三、改进方向
1. **表达优化**：改善句式结构，提升用词精准度
2. **节奏调整**：长短句交替，张弛有度
3. **场景增强**：增加感官细节，但不过度描写

### 四、去AI味要求
{% include 'blocks/depai-rules.md' %}

### 四、禁止项
- 不改变核心情节
- 不改变人物性格和关系
- 不丢失重要信息点

直接输出重写后的完整内容。
