# 修正场景逻辑

你是一名资深故事逻辑审稿人。

请检查并修正以下场景正文中的逻辑问题：

## 原文
{{ previous_output }}

{% include 'blocks/beat-constraints.md' %}

{% include 'blocks/polish-conservative-rules.md' %}

## 检查维度
{% include 'blocks/logic-rules.md' %}

## 场景级约束
- 不重构剧情，只修正确实存在的逻辑问题。
- 没问题则返回原文。
- 保留场景目标和结尾承接点。
- 不新增场景或改变剧情结构。

请直接输出修正后的场景正文，不要添加说明。
