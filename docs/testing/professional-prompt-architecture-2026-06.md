# Phase T4.0 — Professional Prompt 架构设计

## 1. 背景

Lite Prompt 已完成初步实验体系，T3-D7 已完成写作质量与一致性引擎 MVP 链路：

```
Diff Engine → Review Engine → Validator → State Snapshot → Plot Debt → Rewrite Engine → Pipeline dry-run
```

现在进入专业版 Prompt 设计阶段。

**专业版的目标不是“更长的续写”，而是：**
* 写前有计划
* 写中有约束
* 写后有审查
* 状态能沉淀
* 剧情债务能追踪
* 修改建议能结构化

## 2. Lite Prompt 与 Professional Prompt 的区别

| 维度   | Lite Prompt             | Professional Prompt                                                 |
| ---- | ----------------------- | ------------------------------------------------------------------- |
| 目标   | 快速续写                    | 长篇稳定生成                                                              |
| 输入   | selected card + context | scene plan + state snapshot + style guide + plot debt + constraints |
| 输出   | 正文片段                    | 正文 + 可审查结构                                                          |
| 质量控制 | 轻量规则                    | D7 Pipeline                                                         |
| 用户参与 | 少                       | 需要确认关键设定/剧情债务                                                       |
| 适用场景 | 快速生成                    | 长篇小说/专业写作                                                           |

## 3. Professional 生成流程

完整流程：

```
Scene Brief
↓
Scene Plan
↓
Scene Plan Validator
↓
Professional Draft Prompt
↓
正文生成
↓
D7 Pipeline dry-run
↓
Review Suggestions
↓
User Confirmation
↓
可选入库/改写
```

## 4. Scene Plan 结构

Scene Plan JSON 结构：

```json
{
  "scene_id": "ch001-sec001",
  "scene_goal": "李玄进入墨香阁，发现沈鹤年和玄黄秘录的关系",
  "pov_character": "李玄",
  "time": "深夜",
  "location": "墨香阁",
  "characters_present": ["李玄", "沈鹤年"],
  "must_include": [
    "玄铁令牌",
    "玄黄秘录",
    "沈鹤年与天机阁的关系"
  ],
  "must_not_break": [
    "墨香阁在江南古镇",
    "李玄从未来过这里",
    "玄黄秘境尚未开启"
  ],
  "conflict": "李玄想知道沈鹤年的真实身份",
  "obstacle": "沈鹤年不愿意透露太多",
  "turning_point": "李玄拿出玄铁令牌",
  "ending_hook": "沈鹤年暗示玄黄秘境即将开启",
  "plot_debts_to_touch": [
    "unexplained_item-玄铁令牌",
    "unresolved_setting-玄黄秘录",
    "open_question-沈鹤年的身份"
  ],
  "style_constraints": [
    "保持悬疑氛围",
    "避免现代词汇"
  ],
  "continuity_constraints": [
    "李玄刚从巷子里逃出来",
    "玄铁令牌是黑衣客给的",
    "沈鹤年刚见过黑衣客"
  ]
}
```

## 5. Scene Plan 验收规则

生成正文前，必须检查 Scene Plan 是否具备：

**必备要素：**
* 本场目标
* 冲突/阻碍
* 至少一个状态变化
* 结尾钩子
* 必须包含的设定/伏笔
* 不得破坏的连续性约束
* 与当前 State Snapshot 不冲突
* 与 Plot Debt 表的关系

**验收不通过的处理：**
* 如果 Scene Plan 不合格，不应直接生成正文
* 应先让 LLM 补强 Scene Plan
* 只有验收通过后才能进入 Professional Draft Prompt

## 6. Professional Draft Prompt 设计原则

专业版正文 Prompt 应该：

* **使用 Scene Plan 作为主控输入** - 明确本场要发生什么
* **使用 State Snapshot 保持连续性** - 防止遗忘已有的设定和事实
* **使用 Plot Debt 表提醒伏笔/承诺/未解释信息** - 确保伏笔不丢失
* **使用 Style Guide 控制文风** - 保持一致的写作风格
* **使用 must_not_break 避免破坏设定** - 防止自动生成冲突设定
* **生成正文时不直接更新设定库** - 所有设定更新必须经过用户确认
* **生成后交给 D7 Pipeline 审查** - 使用已有质量引擎进行审查

## 7. 与 D7 Pipeline 的关系

明确分工：

* **T4 负责** - 生成前计划和正文生成
* **D7 负责** - 生成后审查、状态沉淀、剧情债务、修订建议

**关键约束：**
* D7 Pipeline 不自动改正文
* 用户确认后才进入后续改写/入库
* 所有写入设定库的操作必须明确可控

## 8. T4 后续阶段建议

建议拆分：

* **Phase T4.1**：Scene Plan schema + validator dry-run
* **Phase T4.2**：Professional Draft Prompt 模板
* **Phase T4.3**：Professional 生成 dry-run / mock
* **Phase T4.4**：Professional 真实 LLM 小冒烟
* **Phase T4.5**：Professional 生成后接入 D7 Pipeline
* **Phase T4.6**：用户确认清单 MVP
* **Phase T4.7**：专业版 UI 接入设计

## 9. 不做的事

本阶段不做：

* 不修改生产 Prompt
* 不调用 LLM
* 不实现真实生成
* 不自动改正文
* 不自动入库
* 不接 UI
* 不把 Professional 写成已完成

## 10. 当前结论

T4.0 只完成架构设计。

**下一步应做：**
Phase T4.1：Scene Plan schema + validator dry-run
