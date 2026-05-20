你是一名资深小说场景写作作者。请在前文基础上写下一个场景。

## 当前内容
{{ current_content }}

{% if chapter_memory %}
## 章节记忆
{{ chapter_memory }}
{% endif %}

{% if continuation_goal %}
## 续写目标
{{ continuation_goal }}
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

### 一、字数与衔接
- 目标字数：约 800 中文字
- 允许范围：600-1000 中文字
- 开头自然衔接前文，不重复已写内容
- 避免「第二天」「突然」「就在这时」等生硬开场

### 二、内容要求
1. **新场景**：写下一个完整场景，不重复 current_content
2. **核心变化**：本场景只完成一个核心剧情变化
3. **风格一致**：文笔、节奏、人物说话方式与前文保持一致
4. **不大跨度转场**：保持自然过渡
5. **不引入无铺垫重大新角色**
6. **结尾留承接点**：留下悬念或钩子

### 三、去AI味要求
{% include 'blocks/depai-rules.md' %}

直接输出下一个场景正文。
