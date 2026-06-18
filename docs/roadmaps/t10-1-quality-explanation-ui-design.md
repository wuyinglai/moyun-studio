# T10.1：Quality Explanation UI 规划设计

> **阶段**: T10.1a (Design Documentation)
> **状态**: ✅ 设计完成
> **创建日期**: 2026-06-19
> **下一步**: T10.1b — Quality Explanation UI MVP

---

## 1. 当前阶段背景

Moyun Studio 已完成 v0.2.2 维护版发布。当前主线已经具备较完整的候选稿安全工作流和写作质量基础能力。

截至 v0.2.2，系统已有能力包括：

- candidate-only 安全工作流
- AI 输出默认生成候选稿，不直接覆盖正文
- preview / adopt / delete
- feedback revision child candidate
- repair candidate child candidate
- candidate lineage
- required / forbidden beats
- beat validation warning
- continuity anchors
- quality metadata
- CandidatePanel quality summary
- real LLM dogfood 验证
- guardrails allowlist noise cleanup
- known issues / roadmap 文档整理

T9 阶段解决的是：

> AI 能不能安全地产生候选稿，并且不破坏正文。

T10 阶段要解决的是：

> 用户能不能理解候选稿为什么好、哪里有风险、下一步该怎么处理。

因此，T10 的核心不是继续增加生成能力，而是增强候选稿的解释、比较、判断和决策体验。

---

## 2. T10 阶段总目标

T10 阶段目标：

> 让用户从"看到候选稿"升级为"看懂候选稿、比较候选稿、修复候选稿、放心采纳候选稿"。

T10 不应破坏 T9 已建立的安全边界：

- 不自动覆盖正文
- 不自动 adopt
- 不让 AI 自动替用户做最终判断
- repair 仍然只生成 child candidate
- warning 仍然只做 advisory
- quality metadata 不作为硬性评分
- 用户始终拥有最终采纳权

---

## 3. 为什么 T10.1 不先做 Candidate Compare

Candidate Compare 很有价值，但不适合作为 T10.1 的第一步。

原因：

1. Candidate Compare 需要更复杂的 diff UI
2. 需要定义原文 vs candidate、parent vs child、candidate A vs candidate B 三种比较模式
3. UI 复杂度高，容易拖慢节奏
4. 当前 quality metadata 已经存在，但解释层不足
5. repair candidate 已经存在，但用户还不知道为什么需要 repair
6. 如果先做解释层，后续 Candidate Compare 会更容易设计

因此，T10.1 先做 **Quality Explanation UI 设计**，T10.2 再做 **Candidate Compare MVP**。

---

## 4. T10.1 核心问题

当前 CandidatePanel 中已经能看到类似：

```
指令遵守：pass / warning / unknown
连续性：pass / warning / unknown
文风保持：pass / unknown
改动幅度：small / medium / large
禁区检查：pass / warning / unknown
```

但问题是：

1. 用户不知道 pass 是什么意思
2. 用户不知道 warning 是否严重
3. 用户不知道 unknown 是失败还是未检测
4. 用户不知道 change_scope=large 是好是坏
5. 用户不知道 repair 按钮为什么出现
6. 用户不知道哪些 warning 来自 beats，哪些来自 anchors，哪些来自 quality metadata
7. 用户不知道下一步应该 preview、repair、feedback revision 还是 adopt

所以 T10.1 的设计目标是：

> 把 quality metadata 从"内部状态"变成"用户可理解的解释"。

---

## 5. T10.1 设计目标

T10.1 设计一个最小解释层，让用户在 CandidatePanel 中可以理解：

1. 这个候选稿整体是否值得看
2. 哪些质量项通过
3. 哪些质量项需要注意
4. 哪些质量项无法判断
5. 为什么出现 repair 按钮
6. repair 会做什么
7. adopt 前有什么风险
8. 这些提示是否会自动修改正文

T10.1 不做完整评分系统。

T10.1 不做候选稿排名。

T10.1 不做多模型裁判。

T10.1 不做自动修文。

---

## 6. Quality Explanation UI 的基本形态

建议在 CandidatePanel 中，把当前 quality summary 扩展为一个可展开的说明区。

### 6.1 折叠态

默认显示简洁摘要：

```
质量提示：2 项通过，1 项需注意，2 项未检测
```

或：

```
质量提示：整体可预览，但建议检查连续性
```

视觉上可以保留轻量 badge，不要占用正文空间。

### 6.2 展开态

点击后展示每个维度解释：

```
指令遵守：通过
说明：候选稿满足当前 required / forbidden beats 检查。

连续性：需注意
说明：本次使用了 3 条连续性锚点，但仍建议人工确认人物状态是否一致。

文风保持：未检测
说明：当前操作不是润色模式，系统不会判断文风保持程度。

改动幅度：较大
说明：候选稿长度相比原文变化较大，建议预览后再采纳。

禁区检查：通过
说明：未发现违反 forbidden beats 的内容。
```

---

## 7. 状态文案规范

### 7.1 pass

不要写成：

```
完全正确
```

建议写成：

```
通过
未发现明显问题
当前规则检查通过
```

原因：系统不是最终裁判，不能做绝对判断。

### 7.2 warning

不要写成：

```
失败
错误
不能采用
```

建议写成：

```
需注意
建议检查
可能需要修复
```

原因：warning 是 advisory，不阻断 adopt。

### 7.3 unknown

不要写成：

```
失败
未通过
无法处理
```

建议写成：

```
未检测
暂无判断
当前模式不适用
```

原因：unknown 很多时候只是没有对应数据，不代表候选稿差。

### 7.4 large change_scope

不要写成：

```
改动过大，不能用
```

建议写成：

```
改动较大，建议预览
```

原因：大改动可能是合理的重写，不一定是问题。

---

## 8. 五个质量维度解释设计

### 8.1 instruction_following

**来源**：beat_validation、required beats、forbidden beats

**解释逻辑**：

```
pass：当前规则检查通过。
warning：有 required / forbidden beats 相关提示。
unknown：没有可用的 beats 检查结果。
```

**用户文案**：

```
指令遵守：候选稿是否遵守本次写作要求。
```

---

### 8.2 continuity

**来源**：continuity_anchors metadata、used_count、anchor_ids、types

**解释逻辑**：

```
pass：本次候选稿生成时使用了连续性锚点。
warning：未来如果出现 anchor warning，则提示需检查。
unknown：没有使用连续性锚点，或当前项目未设置锚点。
```

**用户文案**：

```
连续性：候选稿是否参考了人物状态、线索、关系和世界规则。
```

**注意**：当前 `used_count` 表示"本次生成时注入了多少条 active anchors"，不等于"LLM 输出中逐字引用了多少条"。文案要避免误导。

建议文案：

```
本次生成参考了 3 条连续性锚点。
```

不要写：

```
候选稿完全遵守了 3 条连续性锚点。
```

---

### 8.3 style_preservation

**来源**：candidate action、polish 模式、rewrite / generate / feedback / repair 模式

**解释逻辑**：

```
polish：pass
rewrite：unknown
generate：unknown
feedback revision：unknown
repair：unknown
```

**用户文案**：

```
文风保持：当前候选稿是否倾向保留原句风格。
```

**说明**：

```
润色模式默认更重视保留原意和原句风格；重写、续写和修复模式不强行判断文风保持。
```

---

### 8.4 change_scope

**来源**：原文长度、candidate 长度、粗略字符变化比例

**解释逻辑**：

```
small：变化较小
medium：变化适中
large：变化较大
unknown：无法判断
```

**用户文案**：

```
改动幅度：候选稿相对原文变化有多大。
```

**建议说明**：

```
改动较大不一定是坏事，但建议 adopt 前先预览。
```

---

### 8.5 forbidden_check

**来源**：forbidden beats、beat validation

**解释逻辑**：

```
pass：未发现 forbidden beats 违规。
warning：可能触及 forbidden beats。
unknown：未设置 forbidden beats 或未检测。
```

**用户文案**：

```
禁区检查：候选稿是否触碰本次明确禁止的内容。
```

---

## 9. Repair Candidate 解释设计

当前 repair candidate 已经存在，但用户需要知道它的含义。

### 9.1 按钮文案

建议：

```
修复候选稿
```

辅助说明：

```
根据当前提示生成一个新的修复版候选稿，不会修改正文。
```

### 9.2 出现条件解释

当 repair 按钮出现时，可以显示：

```
系统发现候选稿存在可修复提示，你可以生成一个新的修复版候选稿。
```

### 9.3 点击前确认

MVP 阶段可以不做弹窗，但文案必须明确：

```
修复会生成新的候选稿，不会自动采纳，也不会覆盖正文。
```

### 9.4 修复后的 child candidate 说明

repair child 应显示：

```
来源：由候选稿 cand_xxx 修复生成
```

以及：

```
修复类型：基于质量提示 / beats warning / continuity warning
```

---

## 10. Candidate-only 安全边界文案

T10.1 必须继续强化候选稿安全边界。

在解释区中可以加入一句固定说明：

```
所有质量提示仅供参考。AI 不会自动修改正文，只有你点击采纳后，正文才会更新。
```

这句很重要，因为 Repair Candidate 容易让用户误解为"自动修文"。

---

## 11. T10.1 不做事项

T10.1 不做以下内容：

- 不做总分
- 不做候选稿排名
- 不做 AI 自动推荐最佳候选稿
- 不做完整 diff UI
- 不做多模型评审
- 不做自动 repair
- 不做自动 adopt
- 不做 Scene Plan
- 不改 pipeline 核心
- 不改 LLM 调用逻辑

---

## 12. T10.1 MVP 范围

T10.1 MVP 建议只包含设计，不实现代码。

如果进入实现（T10.1b），最小实现范围应是：

1. CandidatePanel 中新增 Quality Explanation 可展开区
2. 每个 quality dimension 有用户友好文案
3. warning / unknown 文案不误导
4. repair 按钮旁边有说明
5. candidate-only 安全提示
6. old candidate 无 quality metadata 不崩
7. 不改变 adopt / delete / preview 行为

---

## 13. T10.1 后续任务拆分

### T10.1a：Quality Explanation UI Design

| 属性 | 值 |
|------|------|
| 风险 | Risk C |
| 性质 | 文档设计 |
| 是否改代码 | 否 |

**目标**：确定 CandidatePanel quality explanation 的信息架构、文案、状态规则和验收标准。

**验收**：设计文档完成；明确 pass/warning/unknown 文案；明确 repair 解释；明确不做事项；明确 T10.1b 实现范围。

---

### T10.1b：Quality Explanation UI MVP

| 属性 | 值 |
|------|------|
| 风险 | Risk B |
| 性质 | 前端 UI + 类型安全 + E2E |
| 是否改代码 | 是 |

**目标**：在 CandidatePanel 中实现 quality explanation 展开区。

**验收**：old candidate 不崩；pass/warning/unknown 正确显示；repair 说明正确；preview/adopt/delete 不受影响；frontend build 通过；focused E2E 通过。

---

### T10.2：Candidate Compare MVP Design

| 属性 | 值 |
|------|------|
| 风险 | Risk C |
| 性质 | 设计 |
| 是否改代码 | 否 |

**目标**：设计原文 vs candidate、parent vs child 的最小比较模式。

**验收**：明确比较范围；明确不做复杂 diff；明确 UI 信息架构；明确 T10.2b 实现任务。

---

## 14. T10.1 推荐路线

```
T10.1a：Quality Explanation UI Design        ✅ 本文档
→ T10.1b：Quality Explanation UI MVP          ⏭ 下一步
→ T10.2a：Candidate Compare MVP Design
→ T10.2b：Candidate Compare MVP
```

不建议直接做 Candidate Compare。

不建议直接做 Story State UI。

原因：当前用户最先需要的是理解候选稿质量提示，而不是新增更复杂的状态管理。

---

## 15. 验收标准

T10.1 设计阶段完成标准：

1. ✅ 明确 T10 阶段总目标
2. ✅ 明确为什么 T10.1 先做 Quality Explanation
3. ✅ 明确五个 quality dimensions 的解释文案
4. ✅ 明确 pass / warning / unknown / large 的用户语义
5. ✅ 明确 repair candidate 的解释方式
6. ✅ 明确 candidate-only 安全文案
7. ✅ 明确不做事项
8. ✅ 明确 T10.1b 实现范围
9. ✅ 明确后续任务拆分

---

## 16. 最终结论

T10.1 建议定位为 **Quality Explanation UI 规划设计**。

它是 T9.4 Quality Metadata 和 Repair Candidate 之后最自然的一步。

T10.1 不应该增加新的生成能力，而应该提升用户理解和决策能力。

建议下一步进入 **T10.1b：Quality Explanation UI MVP** 实现。
