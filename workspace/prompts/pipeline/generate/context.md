# 整合上下文

## 当前章节
目标文件：{{ file_path }}
用户意图：{{ user_input }}

## 项目上下文
文风指南：{% if style_guide %}{{ style_guide }}{% endif %}
故事状态：{% if story_state %}{{ story_state }}{% endif %}

## 任务
请整合以上上下文信息，提取与当前章节相关的关键元素：
1. 当前故事进度和角色状态
2. 本章需要处理的情节线
3. 需要注意的设定约束

输出应为简洁的总结段落。
