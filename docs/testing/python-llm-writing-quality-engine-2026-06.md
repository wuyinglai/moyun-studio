# Phase T3-D7 — Python + LLM 写作质量与一致性引擎

## 1. 背景

当前单靠 LLM 生成文本存在几个核心问题：
- **遗忘设定**：LLM 生成过程中容易遗忘前面的设定、人物关系、时间线
- **漏检矛盾**：新增内容可能与已有内容冲突，但 LLM 容易漏检
- **判断不稳定**：同一问题多次调用 LLM，判断结果可能不一致
- **缺乏闭环**：没有事实快照、剧情债务表等结构化机制

因此需要设计 Python + LLM 配合的双引擎体系：
- **Python** 负责：结构化比对、切片、扫描、校验、记录、批处理
- **LLM** 负责：语境判断、改写建议、摘要归纳、质量评分
- **用户** 负责：最终确认、是否接受改写、是否入库

---

## 2. 核心分工

### 2.1 Python 负责

| 能力 | 说明 |
|------|------|
| 比对 | 正文 vs 设定库、大纲、时间线、上一场景、剧情债务表 |
| 扫描 | 逐段、逐句扫描关键词、实体、设定、人名、地名 |
| 切片 | 按场景、按段落、按句子切分内容，便于逐块处理 |
| 候选项生成 | 从比对结果中提取候选问题（candidate issues） |
| LLM 输出校验 | 校验 LLM 返回的 review 结果是否覆盖所有候选项 |
| 状态记录 | 记录事实快照、剧情债务表、角色状态变化 |
| 批处理 | 批量处理多个场景、多个章节 |

### 2.2 LLM 负责

| 能力 | 说明 |
|------|------|
| 语境判断 | 判断候选问题是否真正有问题（context-aware） |
| 是否确认问题 | 给候选问题打标签：confirmed / false_positive / needs_more_context |
| 改写建议 | 对 confirmed issues 提供改写建议 |
| 入库建议 | 建议哪些变化应该写入设定库、角色状态 |
| 摘要归纳 | 摘要剧情债务表、事实快照 |
| 质量评分 | 结构化评分（连贯性、一致性、画面感等） |

### 2.3 用户负责

| 责任 | 说明 |
|------|------|
| 最终确认 | 确认哪些问题是真正需要修复的 |
| 是否接受改写 | 选择接受、拒绝或编辑 LLM 提供的改写建议 |
| 是否入库 | 决定哪些状态变化应该写入设定库、角色状态 |

---

## 3. 四大引擎

### 3.1 Diff Engine

**职责**：比对正文与设定库、大纲、时间线、上一场景、剧情债务表

**输入**：
- 正文（当前场景）
- 设定库（story-engine.md、story-state.md）
- 大纲（可选）
- 时间线（可选）
- 上一场景
- 剧情债务表（可选）

**输出**：
- 新增事实
- 冲突事实
- 变化事实
- 遗漏事实
- 超期剧情债务

**技术实现**：
- 实体提取（人名、地名、物品名）
- 属性比对（角色状态、时间、地点）
- 关键词匹配
- 简单语义相似度

---

### 3.2 Review Engine

**职责**：对 Diff Engine 输出的候选问题做语境判断

**输入**：
- Diff Engine 输出的 candidate issues
- 正文
- 上下文（上一场景、设定库）

**输出**：
- JSON 格式 review 结果
- 每个 issue 的状态（confirmed / false_positive / needs_more_context）
- 改写建议
- 结构化评分

**关键机制**：
- 确保 LLM 覆盖所有候选项（Python 校验覆盖率）
- 明确要求 LLM 不能跳过候选项
- 每个候选项必须有明确的判断结果

---

### 3.3 Rewrite Engine

**职责**：对 confirmed issues 做局部改写

**输入**：
- Review Engine 确认的 issues
- 正文
- 改写建议

**输出**：
- 局部改写的 candidate（markdown 格式）
- 改写前后 diff
- 明确标注改写范围

**规则**：
- 不默认重写整场
- 尽量做最小范围改写
- 保留原文的核心意思和风格
- 生成 candidate，不直接覆盖正文

---

### 3.4 Memory Engine

**职责**：将用户确认后的变化写入设定库、角色状态、剧情债务表

**输入**：
- 用户确认的变化
- 正文
- 当前设定库

**输出**：
- 更新后的设定库（候选稿，需用户确认）
- 更新后的剧情债务表
- 事实快照记录

**规则**：
- 不自动入库，只生成候选稿
- 用户确认后再写入
- 保留修改历史

---

## 4. 质量提升机制

### 4.1 大纲验收

在开始写新章节前：
1. Python 读取大纲
2. Python 读取已有设定
3. LLM 对大纲做一致性检查
4. 用户确认大纲

### 4.2 场景执行清单

每个场景开始前：
1. 明确必须完成的剧情点
2. 明确必须保留的设定
3. 明确必须推进的人物弧光
4. Python 生成 checklist
5. 生成结束后 Python 校验 checklist 完成情况

### 4.3 分阶段生成

不一次性生成完整场景，而是：
1. 生成提纲（Python + LLM 确认）
2. 生成段落（逐段 Review）
3. 整合完整场景（Final Review）

### 4.4 State Snapshot（事实快照）

在关键节点（如每卷、每章结束）：
1. Python 提取所有事实
2. Python 与上一次 snapshot 比对
3. LLM 归纳关键变化
4. 生成 snapshot.md

### 4.5 差异审稿

对比：
- 正文 vs 上一场景
- 正文 vs 设定库
- 正文 vs 大纲

输出：
- 新增事实
- 冲突事实
- 遗漏设定

### 4.6 Plot Debt（剧情债务表）

记录：
- 未完成的伏笔
- 未解释的谜团
- 未兑现的承诺
- 未解决的冲突
- 到期时间

Python 负责：
- 扫描正文发现潜在伏笔
- 记录伏笔位置和状态
- 检查是否超期

### 4.7 角色声音指纹

为每个角色建立：
- 常用词汇表
- 说话节奏
- 典型句式
- 价值观倾向

Python 负责：
- 扫描对话提取特征
- 比对当前对话与指纹

LLM 负责：
- 判断对话是否符合角色声音
- 提供改写建议

### 4.8 样本文风对照库

建立：
- 用户认可的高质量场景
- 作为风格参考

Python 负责：
- 提取文风特征
- 比对当前场景与样本

### 4.9 多角色审稿

从不同视角审稿：
- 作者视角（整体质量）
- 读者视角（可读性）
- 设定官视角（一致性）
- 角色视角（对话是否符合人设）

### 4.10 结构化评分闭环

评分维度：
- 连贯性
- 一致性
- 画面感
- 节奏
- 对话质量
- 人物塑造

流程：
1. Python 计算自动指标（字数、段落数等）
2. LLM 做结构化评分
3. 用户调整评分
4. Python 记录评分历史

---

## 5. 第一批实现顺序

### Phase T3-D7.0：架构设计文档 ✅
（本阶段）

### Phase T3-D7.1：Diff Engine 存在性比对 MVP ✅
- 扫描正文提取实体（人名、地名、道具、势力、术语）
- 比对实体是否在设定库中存在
- 生成 candidate issues（新增实体 vs 已知实体）
- 不做语义理解，只做存在性比对
- 输出 JSON 和 Markdown 报告
- 不调用 LLM
- 不自动入库

**本阶段完成说明**：
- 脚本位置：`tests/prompt_experiments/diff_engine_existence_mvp.py`
- 示例报告：`docs/testing/prompt-experiments/diff-engine-existence-mvp-sample.json` 和 `diff-engine-existence-mvp-sample.md`
- 下一阶段：Phase T3-D7.2 可以基于此做更完善的 candidate 格式化，然后 Phase T3-D7.3 接入 LLM review

### Phase T3-D7.1.1：候选提取降噪与断言测试 ✅
- 增加候选清洗函数，过滤明显无效候选
- 过滤包含标点、过短、过长、包含半截引号/冒号/逗号的候选
- 按 entity_type + entity 去重
- 增加噪声过滤统计（raw / filtered_by_noise / filtered_by_dedup / final）
- 新增断言测试脚本，验证 expected entities 存在、forbidden fragments 不存在
- 不调用 LLM
- 不自动入库

**本阶段完成说明**：
- 脚本位置：`tests/prompt_experiments/diff_engine_existence_mvp.py`（已更新）
- 测试脚本：`tests/prompt_experiments/test_diff_engine_existence_mvp.py`
- 测试结果：所有期望实体已识别，所有禁止片段已过滤
- 重要：Diff Engine candidates 必须先经过降噪，才能进入 LLM Review（Phase T3-D7.3）

### Phase T3-D7.2：Candidate JSON + Markdown report ✅
- 已随 D7.1/D7.1.1 一起实现
- 支持 JSON schema 和 Markdown 报告
- 包含噪声过滤统计

### Phase T3-D7.3a：Review Engine schema + 覆盖校验 dry-run ✅
- 定义 LLM review JSON schema（candidate_id, confirmed, confidence, severity, action 等）
- 实现 Python 覆盖校验机制
- 校验 candidate_id 全覆盖、无重复、无多余
- 校验必填字段齐全、字段类型合法
- 校验 action 枚举值、confidence 范围
- 不调用真实 LLM，只使用 mock fixture 验证
- 新增 4 个 fixture（valid, missing_id, duplicate_id, invalid_action）
- 新增断言测试，验证 validator 正确性

**本阶段完成说明**：
- Validator 脚本：`tests/prompt_experiments/review_engine_validator.py`
- 测试脚本：`tests/prompt_experiments/test_review_engine_validator.py`
- 示例报告：`docs/testing/prompt-experiments/review-engine-validator-sample.md`
- 重要：防止 LLM 漏判是 Review Engine 的核心能力，必须先通过 validator 才能认为 review 有效

### Phase T3-D7.3：LLM Review + 覆盖校验 ⏳
- 定义 LLM review JSON schema
- Python 调用 LLM 对 candidates 做判断
- Python 校验 LLM 是否覆盖所有 candidates
- 生成 review report

### Phase T3-D7.4：State Snapshot MVP ⏳
- 定义 snapshot JSON schema
- Python 扫描正文提取事实
- 生成 snapshot.md
- 记录 snapshot 历史

### Phase T3-D7.5：Plot Debt 表 MVP ⏳
- 定义 plot debt JSON schema
- Python 扫描正文发现潜在伏笔
- 生成 plot_debt.md
- 简单的到期提醒

### Phase T3-D7.6：局部 Rewrite Engine MVP ⏳
- 对 confirmed issues 提供改写建议
- 生成 candidate 而非直接覆盖
- 展示改写前后 diff

---

## 6. 不做的事

| 不做 | 原因 |
|------|------|
| 不自动改正文 | 用户必须有最终控制权 |
| 不自动入库 | 用户必须确认哪些变化值得记录 |
| 不自动改生产 Prompt | 这是设计文档，不是实现任务 |
| 不把 candidate 当 confirmed issue | candidate 只是怀疑，需要确认 |
| 不让 LLM 跳过候选项 | 必须覆盖所有候选项，避免漏检 |
| 不做复杂 UI | 先做命令行工具和简单报告 |

---

## 7. 相关文档归档

以下文档归入 T3-D7 的质量与一致性引擎体系：
- configurable-writing-scanner-design-2026-06.md → Diff Engine 一部分
- python-llm-candidate-review-pipeline-2026-06.md → Review Engine 一部分
- writing-diff-engine-design-2026-06.md → Diff Engine 一部分

这些文档不删除，但后续开发以本设计文档为准。

---

## 8. 风险与注意事项

1. **不要把设计写成已实现**：本阶段只做设计，不写生产代码
2. **不要引入成人题材专用规则**：保持通用
3. **不要记录或输出 API Key**：安全第一
4. **不要修改生产 Prompt**：这是架构设计任务
5. **不要修改生成主流程**：当前架构先不动

---

## 9. 验收标准

完成 Phase T3-D7.0 后验收：
- ✅ 设计文档完成
- ✅ 明确 Python + LLM 分工
- ✅ 明确四大引擎职责
- ✅ 明确第一批实现顺序
- ✅ 更新路线图

完成 Phase T3-D7.1 后验收：
- ✅ Diff Engine MVP 可以运行
- ✅ 能扫描正文提取实体
- ✅ 能比对设定库
- ✅ 能生成 candidate issues
