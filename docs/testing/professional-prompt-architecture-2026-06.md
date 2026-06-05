# Phase T4 — Professional Prompt 专业版写作流程

## 1. 背景

**T4 = 先验旧专业版，再扩展新专业版。**

Lite Prompt 已完成初步实验体系，T3-D7 已完成写作质量与一致性引擎 MVP 链路：
```
Diff Engine → Review Engine → Validator → State Snapshot → Plot Debt → Rewrite Engine → Pipeline dry-run
```

现在进入 T4，但 T4 的第一步不是设计 Scene Plan 或 Prompt 编辑器，而是**先盘点、验收原专业版现有功能**。

**专业版的目标不是"更长的续写"，而是：**
* 写前有计划
* 写中有约束
* 写后有审查
* 状态能沉淀
* 剧情债务能追踪
* 修改建议能结构化

## 2. T4 正确顺序

| 阶段 | 任务 | 说明 |
| ---- | ---- | ---- |
| **T4.0** | 原专业版现有功能总盘点 | ✅ 本文档 |
| **T4.1** | 原专业版用户主流程端到端验收 | 验证从打开项目到生成 candidate 的完整流程 |
| **T4.2** | Lite / Professional 共存与切换基线验收 | 验证 Lite 和 Professional 入口切换 |
| **T4.3** | 原专业版编辑能力验收 | 验证 Rewrite/Polish/DeAI 功能 |
| **T4.4** | Workflow / Pipeline / Prompt 模块验收 | 验证工作流、管线、Prompt 引擎 |
| **T4.5** | Story State / Materials / 文件系统验收 | 验证状态管理、素材、文件操作 |
| **T4.6** | Batch / Stream / SSE / Task 验收 | 验证流式响应、任务追踪 |
| **T4.7** | 原专业版问题修复收口 | 修复发现的问题 |
| **T4.8** | Scene Plan schema + validator dry-run | 设计场景计划验收 |
| **T4.9** | Selected-card → Scene Brief / Scene Plan | 扩展到场景计划模式 |
| **T4.10** | Professional Draft Prompt 模板 | 设计专业版 Prompt |
| **T4.11** | Professional 接入 D7 Pipeline | 集成质量引擎 |
| **T4.12** | 用户确认清单 MVP | 用户确认流程 |

**核心原则：不跳步骤，先验收原专业版功能，再扩展新能力。**

## 3. Lite Prompt 与 Professional Prompt 的区别

| 维度   | Lite Prompt             | Professional Prompt                                                 |
| ---- | ----------------------- | ------------------------------------------------------------------- |
| 目标   | 快速续写                    | 长篇稳定生成                                                              |
| 输入   | selected card + context | scene plan + state snapshot + style guide + plot debt + constraints |
| 输出   | 正文片段                    | 正文 + 可审查结构                                                          |
| 质量控制 | 轻量规则                    | D7 Pipeline                                                         |
| 用户参与 | 少                       | 需要确认关键设定/剧情债务                                                       |
| 适用场景 | 快速生成                    | 长篇小说/专业写作                                                           |

## 4. Professional 生成流程（扩展阶段）

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

## 5. Scene Plan 结构（扩展阶段）

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

## 6. Scene Plan 验收规则（扩展阶段）

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

## 7. 与 D7 Pipeline 的关系

明确分工：

* **T4 负责** - 生成前计划和正文生成（扩展阶段 T4.8+）
* **D7 负责** - 生成后审查、状态沉淀、剧情债务、修订建议

**关键约束：**
* D7 Pipeline 不自动改正文
* 用户确认后才进入后续改写/入库
* 所有写入设定库的操作必须明确可控

## 8. 不做的事

**T4 全阶段不做：**
* 不修改生产 Prompt（除非验收发现问题）
* 不调用 LLM（验收除外）
* 不实现真实生成（验收除外）
* 不自动改正文
* 不自动入库
* 不接 UI（扩展阶段 T4.12 除外）
* 不跳步骤直接设计新功能

## 9. 当前结论

**T4 下一步应进入 T4.1：原专业版用户主流程端到端验收。**

必须先验证原专业版现有功能是否可用、稳定，再进行 Scene Plan 或 Prompt 编辑器扩展。

详细盘点见：[professional-existing-feature-inventory-2026-06.md](./professional-existing-feature-inventory-2026-06.md)
