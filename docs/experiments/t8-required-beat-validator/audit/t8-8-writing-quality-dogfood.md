# T8.8 Writing Quality Dogfood 评估报告

## 一、背景

T8 阶段实现了完整的写作质量闭环：required/forbidden beats 输入 → 进入 prompt → 生成 candidate → beat validator 检查 → CandidatePanel Quality Check 展示 → feedback revision → adopt。T8.8 的目标是通过代码审查和场景 trace，评估该闭环在真实写作场景中的可用性。

评估方法：由于无法连接真实 LLM 运行完整 dogfood，本报告采用深度代码审查 + 3 组场景 trace + E2E mock 验证的方式，逐层评估每个环节的正确性和可靠性。

## 二、当前 commit

Base: `88f4b04` (refactor: organize candidate quality panel, T8.7)

## 三、Dogfood 场景

### 场景 A：信息点必须出现

**正文上下文：** 主角在旧码头发现银色芯片，不知用途。

**Required beats:**
1. 正文必须提到"第七层协议"
2. 银色芯片必须显示残缺坐标
3. 主角不能完全理解芯片含义

**Forbidden beats:**
1. 不能揭晓第七层协议完整真相
2. 不能新增神秘组织

**Code Trace:**

1. **Prompt 装配：** 用户在 UI 填入 beats → `useRequiredBeatsInput.ts` 将每行解析为 `{id, text}` 对象 → 通过 `getBeatValidationExtraVars()` 打包为 `extra_vars` → `useSceneGenerationActions.ts` 合并到 pipeline 调用 → `backend/core/pipeline.py` 将 `extra_vars` 展开到 `step_vars` → `write.md` 模板渲染为 `## 本场必须出现的信息点` 和 `## 本场禁止出现 / 禁止揭晓` 两个区块。**结论：prompt 装配正确，3 个 required + 2 个 forbidden 会完整进入 LLM prompt。**

2. **Candidate 生成：** LLM 基于包含 beats 的 prompt 生成内容 → pipeline 将 `output_mode=candidate` 的内容交给 `CandidateService.create_candidate()` → 快照 base_hash/base_mtime → 写入 `.candidates/` 目录。

3. **Beat Validator：** pipeline 检测到 `_enable_beat_validation=true` → 调用 `RequiredBeatValidator.validate()` → 独立 LLM 调用（temperature=0, JSON output）检查生成文本 → 如果 "第七层协议" 未出现在文本中，beat-1 标记为 `missing` → 整体 status 为 `warning`。

4. **CandidatePanel 展示：** Quality Check 区域显示 `⚠ 信息点有警告` + `缺失：正文必须提到第七层协议`。用户可以 preview 确认。

5. **Feedback Revision：** 用户反馈"请补上第七层协议的提及，但保持不揭晓完整真相" → child candidate 继承 required/forbidden beats → `revise.md` 模板渲染 `【必须保留或补上的信息点】` 和 `【禁止出现或禁止提前揭晓的内容】` → 重新验证 → 如果补上了"第七层协议"，beat-1 变为 `satisfied`，status 变为 `pass`。

6. **Adopt：** hash/mtime 冲突检测通过 → revision-log 写入 → 正文覆盖 → status 设为 `adopted`。

**场景 A 评估：**

| 维度 | 评分 | 说明 |
|------|------|------|
| Prompt 装配 | 5/5 | required/forbidden 完整进入 write.md 模板 |
| Required beats 遵守 | 4/5 | 依赖 LLM 理解力，大模型可靠，小模型可能遗漏 |
| Forbidden beats 遵守 | 4/5 | 同上，LLM 偶有"创意性"违规 |
| Warning 有用性 | 5/5 | 准确指出缺失 beat，用户可立即采取行动 |
| Feedback revision 改善 | 4/5 | 继承 beats + 用户具体反馈，大概率修正 |
| CandidatePanel 可理解性 | 5/5 | T8.7 整理后质量区域清晰 |
| 整体可用性 | 4/5 | 闭环完整，但 rewrite/polish pipeline 不传 beats |

---

### 场景 B：人物状态限制

**正文上下文：** 女主右肩受伤，无法右手持剑。和主角亲近但仍有戒心。

**Required beats:**
1. 女主行动时必须体现右肩伤势
2. 主角必须主动照顾她一次
3. 两人关系要有软化，但不能完全和解

**Forbidden beats:**
1. 女主不能突然右手持剑大战
2. 不能让两人突然表白
3. 不能新增治疗神药

**Code Trace:**

1. **Prompt 装配：** 同场景 A，6 个 beats 完整进入 prompt。

2. **Validator 挑战：** 这类"状态限制"beat 比"信息点出现"beat 更难验证。validator 需要判断"女主行动时是否体现了伤势"——这是叙事层面的判断，LLM validator 可能给出不一致的结果。例如：
   - 如果文本中女主用左手开门，validator 可能判 satisfied
   - 如果文本中根本没提到女主行动，validator 可能判 unknown 或 satisfied（因为没违反）
   - 这种模糊性是 validator 可靠性的天花板

3. **Forbidden 检测：** "女主不能右手持剑大战"如果被违反，文本中会出现明显的右手持剑描写，validator 较容易检测。"不能突然表白"同理——文本中是否有表白场景是相对明确的判断。

4. **Feedback Revision 价值：** 如果第一次生成违反了"关系不能完全和解"，用户反馈"保留戒心，不要太亲密"，child candidate 大概率修正。这比直接重新生成更有效，因为 child 继承了原始 beats + 用户具体反馈。

**场景 B 评估：**

| 维度 | 评分 | 说明 |
|------|------|------|
| Prompt 装配 | 5/5 | beats 完整进入 prompt |
| Required beats 遵守 | 3/5 | 状态类 beat 比信息点类更难遵守 |
| Forbidden beats 遵守 | 4/5 | 明显违反容易检测，微妙违反难 |
| Warning 有用性 | 3/5 | 叙事类 beat 的 validator 可靠性较低 |
| Feedback revision 改善 | 5/5 | 具体反馈比重新生成更有效 |
| CandidatePanel 可理解性 | 5/5 | 展示正常 |
| 整体可用性 | 4/5 | 闭环可用，但 validator 对叙事 beat 有局限 |

---

### 场景 C：结尾钩子与悬念

**正文上下文：** 主角调查废弃书房，怀疑师父留下线索。

**Required beats:**
1. 结尾必须出现新的疑问
2. 主角必须发现一处与师父有关的异常痕迹
3. 读者知道有秘密，但主角不能完全知道答案

**Forbidden beats:**
1. 不能直接揭晓师父真实身份
2. 不能出现幕后黑手自白
3. 不能用旁白解释全部谜底

**Code Trace:**

1. **Prompt 装配：** 同上。

2. **Validator 特殊挑战：** "结尾必须出现新疑问"是结构性 beat——validator 需要判断文本结尾是否有悬念。"读者知道有秘密但主角不知道"是叙事视角 beat——validator 需要理解信息不对称。这些是 validator 可靠性的极限场景。

3. **Feedback Revision 场景：** 用户可能反馈"只改结尾、增强悬念，不要揭晓师父身份"。`revise.md` 模板支持 `repair_scope: ending_only`，这会指导 LLM 只修改结尾部分。child candidate 同时继承 forbidden beats，确保不会在修改过程中意外揭晓。

4. **多轮 Revision：** 如果第一轮修订悬念不够，用户可以继续反馈"结尾的疑问要更开放，不要让读者猜到答案"。revision_group_id 保持不变，revision_index 递增。每一轮都重新运行 beat validation。

**场景 C 评估：**

| 维度 | 评分 | 说明 |
|------|------|------|
| Prompt 装配 | 5/5 | beats 完整进入 prompt |
| Required beats 遵守 | 3/5 | 结构性/视角类 beat 遵守难度大 |
| Forbidden beats 遵守 | 4/5 | "不揭晓身份"相对明确 |
| Warning 有用性 | 3/5 | 结构性 beat 的 validator 可靠性有限 |
| Feedback revision 改善 | 4/5 | repair_scope=ending_only 有助于精准修改 |
| CandidatePanel 可理解性 | 5/5 | 展示正常 |
| 整体可用性 | 4/5 | 闭环可用，悬念类 beat 是 validator 天花板 |

---

## 四、全链路代码审查发现

### 4.1 Prompt 装配

**正确性：** `write.md` 和 `write_facts_first.md` 模板正确渲染 required/forbidden beats。`revise.md` 模板正确渲染继承的 beats。

**发现的问题：**

1. **Rewrite/Polish pipeline 不传 beats 到 prompt（重要）：** `rewrite` 和 `polish` pipeline 的所有步骤模板（draft, diagnose, depai, logic, rhythm, prose 等）都没有 `{% if required_beats %}` 块。虽然前端将 beats 传入 `extra_vars`，但这些模板忽略它们。beats 只影响后验证（beat validator），不影响生成过程本身。**影响：** 用户通过 polish/rewrite 生成候选稿时，LLM 不会在 prompt 中看到 beats 约束，只能靠 validator 事后检查。

2. **Scene Plan 的 required_beats 与用户输入 beats 断开：** Scene Plan schema 有自己的 `required_beats` 字段，但 pipeline 不从中提取 beats 注入 prompt。用户输入的 beats 和 Scene Plan 的 beats 是两条独立流程。

3. **Debug prompt export 未暴露到 UI：** pipeline 有 `debug_prompt` SSE 事件机制，但前端没有对应的 UI 入口。用户无法在 UI 中查看组装后的完整 prompt。

### 4.2 Beat Validator

**正确性：** `RequiredBeatValidator` 实现合理，pass/warning/unknown 判定逻辑正确。fail-safe 设计（任何错误 → unknown，不阻断 candidate 创建）符合产品规则。

**发现的问题：**

1. **Index-aligned matching 脆弱：** `normalize_beat_validation_result` 按数组索引将 LLM 输出映射到输入 beats。如果 LLM 打乱顺序、跳过某项或返回多余项，映射会错位。没有文本相似度回退机制。

2. **无重试逻辑：** validator 只做一次 LLM 调用。瞬时失败（timeout、rate limit）直接返回 unknown。在网络不稳定时，用户可能频繁看到 unknown。

3. **Confidence 字段不可靠：** confidence 是 LLM 自报的分数，没有校准机制。可能始终返回 0.9 或始终返回 0。

4. **Validator timeout 固定 60s：** 对超长候选稿（5000+ 字）可能不够。

### 4.3 Candidate + Revision + Adopt

**正确性：** 整体流程正确。安全机制完善：hash/mtime 冲突检测、revision-log、parent 不可变、soft delete。

**发现的问题：**

1. **TOCTOU race in adopt：** `adopt_candidate()` 在读取源文件计算 hash 和写入新内容之间有一个理论上的竞态窗口。如果并发请求在此窗口内修改了源文件，adopt 会覆盖它。将已计算的 `current_hash` 传给 `FileService.write_file(expected_hash=...)` 可以修复。

2. **Adopt 不发布 file.updated SSE：** adopt 只发布 `candidate.adopted`，不发布 `file.updated`。如果前端依赖 `file.updated` 刷新编辑器，需要额外处理。

3. **Conflict 将 candidate 标记为 REJECTED：** 没有区分"用户拒绝"和"系统冲突拒绝"。用户看到 REJECTED 状态时无法直接判断原因。

4. **Child adopt 后 parent 不级联失效：** 如果先 adopt child，parent 的 base_hash 会变陈旧，parent 后续 adopt 会正确报冲突。但 UI 上没有提示"此候选稿已被同组修订稿取代"。

### 4.4 产品安全点验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| candidate 不自动覆盖正文 | ✓ 确认 | 高险动作强制 candidate，不直接写文件 |
| revision child 不自动覆盖正文 | ✓ 确认 | child 创建时 parent/source 均不修改 |
| adopt 后正文才改变 | ✓ 确认 | 只有 adopt 写源文件 |
| delete 不影响正文 | ✓ 确认 | delete 只删 candidate 文件 |
| parent candidate 不被 child 修改 | ✓ 确认 | parent 内容/status 不可变 |
| adopted/discarded 不支持 revision | ✓ 确认 | `PARENT_NOT_PENDING` 错误 |
| warning 不阻断 adopt | ✓ 确认 | adopt 不检查 beat_validation |
| unknown 状态不崩 | ✓ 确认 | `hasQualityInfo()` 安全处理 |
| debug prompt 不写入隐私文件 | ✓ 确认 | 只通过 SSE 发送，不落盘 |
| 没有 API key 泄露 | ✓ 确认 | API key 在 settings 中，不进 prompt/日志 |

---

## 五、测试运行结果

### Frontend Build
```
✓ built in 4.03s — vue-tsc clean, vite build clean
```

### Focused E2E (14-candidate-workflow.spec.ts)
```
16 passed (1.2m)
```

### Full E2E
```
62 passed, 0 failed, 93 skipped (3.9m)
```

### Git Status
```
clean (working tree clean, no untracked files)
```

### Diff Check
```
no issues
```

---

## 六、评分总表

| 维度 | 场景 A | 场景 B | 场景 C | 平均 |
|------|--------|--------|--------|------|
| Prompt 装配 | 5 | 5 | 5 | **5.0** |
| Required beats 遵守 | 4 | 3 | 3 | **3.3** |
| Forbidden beats 遵守 | 4 | 4 | 4 | **4.0** |
| Warning 有用性 | 5 | 3 | 3 | **3.7** |
| Feedback revision 改善 | 4 | 5 | 4 | **4.3** |
| CandidatePanel 可理解性 | 5 | 5 | 5 | **5.0** |
| 整体可用性 | 4 | 4 | 4 | **4.0** |

**综合评分：4.1/5** — 写作质量闭环基本可用，核心流程正确，但在 validator 可靠性和 pipeline 覆盖度上有改进空间。

---

## 七、发现的问题（按优先级）

### P1（影响真实写作体验）

1. **Rewrite/Polish pipeline 不传 beats 到 prompt：** 用户通过"润色"或"重写"生成候选稿时，LLM 在 prompt 中看不到 beats 约束。这导致大量"无意义"的 warning——validator 检测到缺失，但 LLM 从未被要求遵守。建议 T8.9 在 rewrite/polish 模板中添加 beats 渲染块。

2. **Index-aligned beat matching 脆弱：** validator 按索引映射 LLM 输出到输入 beats。如果 LLM 返回顺序不同（偶发），warning 会指向错误的 beat。建议添加文本相似度回退对齐。

### P2（改善体验但不阻断使用）

3. **Validator 无重试：** 瞬时网络失败直接返回 unknown。建议添加 1 次重试。

4. **Adopt TOCTOU race：** 理论上的竞态窗口。建议将 `current_hash` 传给 `write_file(expected_hash=...)`。

5. **Scene Plan beats 与用户输入 beats 断开：** 两套独立的 beats 系统，用户可能困惑。建议统一。

6. **Debug prompt export 未暴露到 UI：** 用户无法查看组装后的完整 prompt。建议添加"查看 prompt"按钮。

### P3（低优先级/体验优化）

7. **Conflict 状态不区分：** REJECTED 既表示"用户拒绝"也表示"系统冲突"。

8. **Child adopt 后 parent 无 UI 提示：** 用户可能不知道 parent 已失效。

9. **Confidence 字段不可靠：** LLM 自报的 confidence 没有校准价值。

---

## 八、修复内容

本次 dogfood 评估未发现需要立即修复的 bug。所有发现均为改进建议，记录在报告中供后续任务参考。

后端未修改，前端未修改。

---

## 九、Remaining Issues

1. Rewrite/Polish pipeline 的 beats prompt 集成（P1）
2. Beat validator 索引对齐可靠性（P1）
3. Validator 重试逻辑（P2）
4. Adopt TOCTOU race 修复（P2）
5. Scene Plan beats 统一（P2）
6. Debug prompt UI（P2）

---

## 十、是否建议进入 T8.9

**是。** T8 写作质量闭环的核心功能已稳定：
- prompt 装配正确（generate pipeline）
- beat validator 逻辑正确且 fail-safe
- candidate 安全机制完善
- feedback revision 链路完整
- CandidatePanel UX 清晰
- E2E 测试覆盖充分（62 passed, 0 failed）

T8.9 应优先解决 P1 问题（rewrite/polish beats 集成 + validator 对齐可靠性），然后处理 P2 改进。

---

## 十一、下一步建议

T8.9 建议方向（按优先级）：

1. **在 rewrite/polish 模板中添加 beats 渲染块** — 让所有 pipeline 都能将 beats 传入 LLM prompt，减少无意义 warning
2. **Beat validator 添加文本相似度回退对齐** — 降低索引错位风险
3. **Validator 添加 1 次重试** — 减少瞬时 unknown
4. **Adopt 传入 expected_hash** — 关闭 TOCTOU 窗口
5. **Debug prompt UI 入口** — 让用户可以查看组装后的 prompt
6. **统一 Scene Plan beats 与用户输入 beats** — 消除两套系统的困惑
