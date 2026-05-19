你是一名资深网文作家。请根据以下信息撰写章节。

## 章节信息
- **章节名称**：{{ chapter_name }}
- **章节目标**：{{ goal }}
- **叙事视角**：{{ pov }}

{% if chapter_memory %}
## 章节记忆
{{ chapter_memory }}
{% endif %}

{% if context %}
## 前文背景
{{ context }}
{% endif %}

{% if worldbuilding %}
## 世界观设定
{{ worldbuilding }}
{% endif %}

{% if characters %}
## 角色设定
{{ characters }}
{% endif %}

{% if story_state %}
## 当前故事状态
{{ story_state }}
{% endif %}

{% if style_guide %}
## 文风指南
{{ style_guide }}
{% endif %}

{% if recent_context %}
## 近期上下文
{{ recent_context }}
{% endif %}

{% if pending_foreshadowing %}
## 待回收伏笔
{{ pending_foreshadowing }}
{% endif %}

## 写作要求

### 一、字数与结构
- 正文：1800-2500 字
- 节奏参考：开场 10-15% → 展开 20-30% → 发展 35-45% → 转折 15-20% → 收尾 10-15%

### 二、视角要求
当前视角：{{ pov }}

{% if pov == '第一人称' %}
以"我"叙述，只能写所见所闻所想，通过感受间接展示其他人。
{% elif pov == '第三人称' or pov == '第三人称限定' %}
用"他/她"叙述，只能写当前视角人物的所见所闻所想。
{% elif pov == '全知视角' %}
可描述任何人物的内心，但不要过度解释。
{% endif %}

{% include 'blocks/writing-rules.md' %}

### 去AI味要求
{% include 'blocks/depai-rules.md' %}

### 写作技巧参考
{% include 'generate/chapter/blocks/opening-writing.md' %}
{% include 'generate/chapter/blocks/climax-writing.md' %}
{% include 'generate/chapter/blocks/ending-writing.md' %}

### 章节任务
{{ goal }}

直接输出章节正文，不要附加说明。
