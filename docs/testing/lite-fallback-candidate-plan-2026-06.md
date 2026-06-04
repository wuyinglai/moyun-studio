# Lite Fallback Candidate 化方案

## 1. 背景

T3-C 真实生成冒烟测试（phase-t3b-continuous-scenes.py）发现，
当 LLM 调用失败或超时后，系统会使用固定模板生成 fallback 草稿，
这些草稿会直接写入正文文件，污染真实创作流程。

T3-D1 已完成 fallback_used 标记；
T3-D2 已完成前端 fallback 警告 UI；
T3-D3 已完成 LLM 失败后自动重试一次。

但 fallback 仍会直接覆盖正文，需要进一步 candidate 化。

## 2. 当前状态

### 2.1 已完成
- ✅ fallback_used 标记已存在于后端响应和 SSE 事件；
- ✅ 前端会显示"本场为应急草稿，建议重写或扩写"警告；
- ✅ LLM 失败后会自动重试一次；
- ✅ retry_used 和 retry_count 标记已实现；
- ✅ response payload 包含所有标记信息。

### 2.2 仍存在的问题
- ❌ fallback 草稿仍会直接写入正式正文文件；
- ❌ 用户无法拒绝 fallback 草稿；
- ❌ 连续生成流程会继续推进到下一场，基于错误草稿；
- ❌ 测试脚本无法区分"真实 LLM 输出"和"fallback 模板输出"。

## 3. 为什么要 candidate 化

### 3.1 避免正文污染
Fallback 模板内容不是真实创作，不应直接进入项目正文。

### 3.2 用户控制权
用户应确认是否采用 fallback 草稿，或重写本场。

### 3.3 测试隔离
测试脚本应能明确区分真实 LLM 输出和 fallback 输出。

### 3.4 安全性
Candidate 机制提供了事务性安全修改，保留 base_hash/base_mtime，
可以避免覆盖用户的已修改内容。

## 4. 当前 CandidateService 链路

### 4.1 创建候选稿
- 函数：CandidateService.create_candidate
- 参数：project_id, source_path, action, content, source_mode, ...
- 存储：
  - 正文在 .candidates/{candidate_id}.{action}.md
  - metadata 在 .candidates/metadata.json
- 状态：CandidateStatus.PENDING

### 4.2 Lite 候选稿设置
- source_mode: "lite"（由 _create_lite_candidate 函数设置）
- action: 由 lite_action_to_candidate_action 映射
  - rewrite_current_scene -> CandidateAction.REWRITE
  - more_exciting -> CandidateAction.EXCITING
  - more_reasonable -> CandidateAction.REASONABLE

### 4.3 采用候选稿
- 函数：CandidateService.adopt_candidate
- 流程：
  1. 校验当前 source file 的 hash/mtime 和 base_hash/base_mtime
  2. 如果不匹配，返回 CONFLICT
  3. 如果匹配，写 revision-log
  4. 覆盖正式文件
  5. 更新 candidate status = ADOPTED

### 4.4 SSE 事件
- 事件名：candidate.created
- 由 backend/domain/events.make_candidate_created_event 生成

## 5. 方案 A：fallback 仍写正文，但同时生成 candidate 标记

**低风险，但不能避免污染正文。**

### 5.1 设计
- 保留当前 fallback 写入正文的行为；
- 当 fallback 触发时，同时创建一个 fallback candidate；
- 在 response 中增加 fallback_candidate_id；
- 前端显示警告，同时提供"查看应急候选稿"链接。

### 5.2 优点
- 改动最小；
- 连续生成流程不受影响；
- 兼容性最高。

### 5.3 缺点
- 正文仍被污染；
- 不符合"候选稿化"的初衷。

## 6. 方案 B：fallback 默认写 candidate，不覆盖正文

**推荐方案，但影响连续生成，需要明确下一步行为。**

### 6.1 设计
- 当 fallback 触发时：
  - 不覆盖正式正文；
  - 创建 fallback candidate，action="fallback_draft"；
  - 在 response 中标记 fallback_used=true，fallback_candidate_id；
  - 连续生成流程遇到 fallback 时暂停，等待用户决策。

### 6.2 优点
- 正文完全不受污染；
- 用户明确确认后才采用；
- 测试隔离更好。

### 6.3 缺点
- 连续生成流程需要改造；
- 用户需要额外决策步骤；
- 兼容性问题：旧项目可能期望 fallback 直接覆盖。

## 7. 方案 C：fallback 写入临时应急文件

**折中方案，复杂度中等。**

### 7.1 设计
- 当 fallback 触发时，不覆盖正式正文；
- 写入一个临时文件（例如 target_file.fallback.md）；
- 前端提示用户有应急草稿；
- 用户可以选择查看、采用或忽略。

### 7.2 优点
- 正文不受污染；
- 实现简单，不需要 CandidateService 改动。

### 7.3 缺点
- 与 Candidate 系统不统一；
- 仍然需要用户手动操作；
- 临时文件管理复杂。

## 8. 推荐方案

**我们推荐方案 B 并分阶段实施：**

### 8.1 阶段划分
- **D4.1**：fallback candidate 元数据设计，不改写入行为
- **D4.2**：fallback 同步创建 candidate，但仍写正文
- **D4.3**：fallback 不直接覆盖正文，进入待确认状态
- **D4.4**：连续生成遇到 fallback 时暂停，要求用户采用/重写
- **D4.5**：UI/FlowPanel 联动优化

## 9. 数据结构设计

### 9.1 新增字段
建议在 LiteWriteNextResponse 中新增：
- fallback_candidate_id: str | None（新增）
- fallback_reason: str | None（新增，例如 "llm_timeout", "llm_error", "retry_failed"）
- retry_count: int（已存在）
- retry_used: bool（已存在）

### 9.2 fallback candidate metadata
- source_mode: "lite"
- action: "fallback_draft"（需要在 CandidateAction 中新增）
- fallback_reason: 在 candidate_info 的扩展字段或 metadata 中
- retry_count: 同上
- fallback_used: 作为候选稿的上下文标记

## 10. UI 设计

### 10.1 fallback 警告增强
在 LiteWritingView 的 fallback 警告中：
- 显示"本场为应急草稿，建议重写或扩写"
- 新增"查看应急候选稿"按钮
- 点击后导航到候选稿查看

### 10.2 CandidatePanel 显示
在 CandidatePanel 中：
- fallback candidate 显示"应急草稿"标签
- 优先显示在列表顶部

### 10.3 采用前状态
- fallback candidate 采用前，不覆盖正文；
- 如果目标场是空的，用户可以直接"采用"或"重写"；
- 如果目标场有内容，候选稿会作为对比显示。

### 10.4 FlowPanel 标记
在 FlowPanel 中：
- 标记 fallback 节点（用橙色或警告色）
- 显示 fallback_candidate_id

## 11. 测试设计

### 11.1 单元测试
- [ ] fallback 时正确创建 candidate
- [ ] fallback candidate path 正确
- [ ] fallback candidate metadata 包含 fallback_reason 和 retry_count
- [ ] adopt fallback candidate 后正确覆盖正文
- [ ] 不 adopt fallback candidate 不污染正文

### 11.2 集成测试
- [ ] 连续生成遇 fallback 暂停
- [ ] fallback 警告 UI 显示正确
- [ ] 候选稿面板显示 fallback candidate
- [ ] 采用 fallback candidate 后 flow 继续
- [ ] 不采用 fallback candidate 时 flow 等待

### 11.3 冒烟测试
- [ ] results.json 记录 fallback_candidate_id
- [ ] 区分真实 LLM 输出和 fallback 输出
- [ ] 统计 fallback 率和候选稿采用率

## 12. 风险分析

### 12.1 连续生成流程复杂化
风险：连续生成是 T3-B 的核心流程，改动可能引入 bug。
缓解：分阶段实施，D4.1 和 D4.2 先不影响连续生成，D4.3/D4.4 再改。

### 12.2 用户体验退化
风险：原来 fallback 能自动继续，现在需要用户手动决策，打断创作流。
缓解：可以增加一个设置项"自动采用 fallback 草稿"，默认关闭，高级用户可开启。

### 12.3 旧项目兼容性
风险：旧项目可能依赖 fallback 直接覆盖正文的行为。
缓解：保留旧行为作为可选设置，或在 UI 中明确告知变化。

### 12.4 CandidateService 和 Lite flow 耦合增加
风险：Lite 生成现在依赖 CandidateService，系统复杂度提升。
缓解：保持 _create_lite_candidate 作为轻量 wrapper，尽量不耦合业务逻辑。

## 13. 推荐实施顺序

### Phase T3-D4.1: fallback candidate 元数据设计
- 目标：确定字段和数据结构
- 交付：文档更新
- 风险：极低
- 改动：无代码改动

### Phase T3-D4.2: fallback 同步创建 candidate，但仍写正文
- 目标：验证候选稿创建流程
- 交付：
  - 新增 fallback_candidate_id 到 response
  - 当 fallback 触发时同步创建 candidate
  - 但仍保留写正文的行为
- 风险：低
- 改动：
  - backend/api/lite.py：在 fallback 分支调用 _create_lite_candidate
  - backend/schemas/lite.py：新增 fallback_candidate_id 字段
  - 新增 CandidateAction.FALLBACK_DRAFT

### Phase T3-D4.3: fallback 不直接覆盖正文
- 目标：避免正文污染
- 交付：
  - fallback 时不写正式文件
  - 只写 candidate
  - response 标记 fallback_used=true
- 风险：中
- 改动：
  - backend/api/lite.py：修改 sync 和 stream 分支
  - 增加判断：fallback 时不做文件写入
  - 只有 adopt 后才写入

### Phase T3-D4.4: 连续生成 fallback 暂停策略
- 目标：让连续生成流程知道遇到 fallback 并暂停
- 交付：
  - 前端检测 fallback_used=true 时，不自动继续
  - UI 提示用户决策：采用、重写或暂停
- 风险：中高
- 改动：
  - frontend/src/composables/useLiteGeneration.ts
  - frontend/src/views/LiteWritingView.vue

### Phase T3-D4.5: UI/FlowPanel 联动优化
- 目标：完善用户体验
- 交付：
  - fallback 警告 UI 增加候选稿链接
  - FlowPanel 显示 fallback 标记
  - 候选稿面板优先显示 fallback candidate
- 风险：低
- 改动：
  - frontend 各组件

## 14. 结论

本轮任务仅完成方案设计和边界评估，不实施业务代码改动。

我们明确了：
- 当前 fallback 在 lite.py 的第 690 行（sync）和第 950 行（stream）触发
- CandidateService 可以安全地创建 fallback candidate
- 需要新增 CandidateAction.FALLBACK_DRAFT
- 推荐分 5 阶段（D4.1-D4.5）实施，优先从 D4.1/D4.2 这种低风险改动开始

下一阶段：进入 Phase T3-D4.1，开始元数据设计和低风险改动。

---

## 15. Phase T3-D4.1 元数据准备

**实施日期**: 2026-06-04

### 15.1 完成内容

#### 1. 新增 FALLBACK_DRAFT action 枚举
在 `backend/schemas/candidate.py` 中：
```python
class CandidateAction(str, Enum):
    # ... 原有 action ...
    FALLBACK_DRAFT = "fallback_draft"  # 应急草稿（LLM 失败后 fallback 生成）
```

#### 2. 添加 lite_action_to_candidate_action 映射
在 `backend/application/lite_candidate_policy.py` 中：
```python
def lite_action_to_candidate_action(action: str) -> CandidateAction:
    mapping = {
        # ... 原有映射 ...
        "fallback_draft": CandidateAction.FALLBACK_DRAFT,  # 应急草稿
    }
```

#### 3. 新增测试
在 `backend/tests/test_lite_fallback_candidate_metadata.py` 中：
- 测试 FALLBACK_DRAFT 枚举存在
- 测试 fallback_draft 映射正确
- 测试 fallback candidate metadata 可构造

### 15.2 本轮不实施的内容

- ❌ 不创建 fallback candidate（将在 D4.2 实施）
- ❌ 不改变 fallback 写入正文行为
- ❌ 不调用 CandidateService 写文件

### 15.3 元数据字段约定

Phase T3-D4.1 确认了 fallback candidate 的元数据字段：

| 字段 | 值 | 说明 |
|------|-----|------|
| action | `fallback_draft` | 应急草稿动作 |
| source_mode | `lite` | 来源模式 |
| status | `pending` | 默认待确认 |
| fallback_used | `true` | 标记为 fallback 生成 |
| fallback_reason | `llm_failed_after_retry` | 失败原因 |
| retry_count | `1` | 重试次数 |

### 15.4 下一阶段 D4.2 计划

D4.2 将：
1. 在 lite.py 的 fallback 分支中调用 `_create_lite_candidate`
2. 传入 `action="fallback_draft"`
3. 传入 fallback_reason 和 retry_count 等 metadata
4. **但仍保留写正文的行为**（保持向后兼容）

### 15.5 验证

| 检查项 | 结果 |
|--------|------|
| CandidateAction.FALLBACK_DRAFT 存在 | ✅ |
| lite_action_to_candidate_action 映射 fallback_draft | ✅ |
| 测试通过 | ✅ |
| 前端 build 不受影响 | ✅ |
| API Key 未提交 | ✅ |

### 15.6 结论

**Phase T3-D4.1 ✅ 完成！**

可以进入 Phase T3-D4.2。

---

## 16. Phase T3-D4.2 fallback 同步创建 candidate

**实施日期：** 2026-06-04

### 16.1 完成内容

在保持现有写正文行为不变的前提下：
- ✅ 新增 `CandidateAction.FALLBACK_DRAFT` 枚举值
- ✅ 当 `fallback_used=True` 时，同步创建 fallback candidate
- ✅ 在 sync response 中返回 `fallback_candidate_id`
- ✅ 在 stream done 事件中返回 `fallback_candidate_id`
- ✅ 前端类型支持接收 `fallback_candidate_id`
- ✅ `useLiteGeneration` 添加 `fallbackCandidateId` 状态变量
- ✅ 保留原有写正文行为，连续生成不受影响

### 16.2 当前行为（与旧版保持一致）

当 LLM 失败时：
1. 仍然写入 fallback 内容到正文文件
2. 仍然更新 story_engine.md、recent-context.md 等
3. 仍然继续生成下一场景
4. 仍然显示 fallback_used 警告

### 16.3 新增行为（候选稿保存）

在保持上述行为的同时：
1. 当 `fallback_used=True` 时，额外调用 `_create_lite_candidate` 创建候选稿
2. 使用 `action="fallback_draft"` 和 `source_mode="lite"`
3. 在 response 中添加 `fallback_candidate_id` 字段
4. 候选稿保存到 `.candidates/` 目录下

### 16.4 测试覆盖

新增测试文件 `backend/tests/test_lite_fallback_candidate_creation.py`：
- ✅ 测试 `CandidateAction.FALLBACK_DRAFT` 枚举存在
- ✅ 测试 lite action "fallback_draft" 映射正确
- ✅ 测试其他 action 仍然正常工作
- ✅ 测试 fallback candidate metadata 结构正确

### 16.5 下一阶段计划

**Phase T3-D4.3：** fallback 不覆盖正文
- 修改 fallback 分支，不直接写正文文件
- 只创建 fallback candidate
- 用户需要手动采用 fallback candidate 或重写

### 16.6 风险评估

- ✅ **低风险：** 保持现有行为完全不变，只是额外添加候选稿保存
- ✅ **向后兼容：** 所有现有功能继续正常工作
- ✅ **易于回滚：** 如果发现问题，可以简单禁用 fallback candidate 创建

### 16.7 结论

**Phase T3-D4.2 ✅ 完成！**

可以进入 Phase T3-D4.3。

---

## 17. Phase T3-D4.3 fallback 不覆盖正文

**实施日期：** 2026-06-04

### 17.1 目标

- 当 fallback_used=true 时，**不再**直接写入正式正文文件
- fallback 内容只保存为 fallback_draft candidate
- 不更新 story engine、recent-context、chapter plan 等
- 返回 write_skipped=true 和 write_skip_reason
- 前端不自动继续下一场景

### 17.2 完成内容

**后端变更：**
1. `backend/schemas/lite.py` - 添加 `write_skipped` 和 `write_skip_reason` 字段
2. `backend/api/lite.py` - 当 `used_fallback=true` 时：
   - 优先创建 `fallback_draft` candidate
   - **不再**调用 `file_service.write_file` 写入正式文件
   - **不再**调用 `update_ch_meta` 更新章记忆
   - **不再**更新 `story-engine.md` 和 `recent-context.md`
   - **不再**生成下一章规划
   - 返回 `write_skipped=true` 和 `write_skip_reason`

**前端变更：**
1. `frontend/src/services/liteService.ts` - 更新类型，添加 `write_skipped` 和 `write_skip_reason`
2. `frontend/src/composables/useLiteGeneration.ts` - 新增 `writeSkipped` 和 `writeSkipReason` 状态
3. `frontend/src/views/LiteWritingView.vue` - 更新 fallback 警告 UI，显示新提示

**测试更新：**
1. `backend/tests/test_lite_fallback_candidate_creation.py` - 添加响应 schema 测试

### 17.3 新的 fallback 行为

1. **用户体验：**
   - 用户看到 "本场未写入正式正文，已保存为应急候选稿"
   - 用户必须手动在候选稿面板中采用或重写
   - 不会自动继续下一场景

2. **文件安全：**
   - Fallback 内容永远不会污染正式正文
   - Story engine 和记忆只在正常生成时才更新

3. **候选稿功能：**
   - Fallback 候选稿作为正式候选稿保存
   - 用户可以查看、采用或放弃
   - 提供了明确的 fallback 来源记录

### 17.4 下阶段计划

**Phase T3-D4.4：** 连续生成 fallback 暂停策略
- 完善连续生成流程
- 当遇到 fallback 时清晰地提示用户
- 提供手动继续的入口

**Phase T3-D4.5：** UI/FlowPanel 联动优化
- 在 FlowPanel 中显示 fallback 状态
- 提供更直观的用户交互

### 17.5 结论

**Phase T3-D4.3 ✅ 完成！**

---

## 18. Phase T3-D4.4 连续生成 fallback 暂停策略

**实施日期：** 2026-06-04

### 18.1 目标

- 当 write_skipped=true 时，明确暂停连续生成流程
- 防止用户在未处理 fallback candidate 时继续生成下一场景
- 提供清晰的 UI 提示
- 完善测试脚本支持

### 18.2 完成内容

**前端变更：
1. `frontend/src/composables/useLiteGeneration.ts` - 新增 `clearFallbackPauseStatus` 函数
2. `frontend/src/views/LiteWritingView.vue` - 实现：
   - 当 writeSkipped=true 时：
     - 禁用 "换个方向" 按钮
     - 禁用 "生成下一场景爽点卡" 按钮
     - 禁用所有 option card
     - 显示 "本场未写入正式正文" 提示
     - 显示候选稿 ID（如果有）
   - 当采用或放弃候选稿后，自动清除暂停状态
3. `frontend/src/composables/useLiteCandidateActions.ts` - 更新：
   - 支持接收 `clearFallbackPauseStatus` 作为依赖
   - 当 acceptCandidate 和 discardCandidate 时调用

**新增 data-testid：**
1. `lite-fallback-write-skipped` - 用于标识 write_skipped 的提示
2. `lite-fallback-pause-notice` - 暂停提示
3. `lite-fallback-candidate-id` - 候选稿 ID

**测试更新：**
1. `tests/phase-t3b-continuous-scenes.py` - 更新：
   - 新增对 write_skipped 的检测和记录
   - 当检测到 write_skipped 时停止继续生成
   - 新增记录 fallbackCandidateId

### 18.3 新的暂停行为

当遇到 fallback 触发后：
1. **UI 状态：
   - 显示："本场未写入正式正文，已保存为应急候选稿"
   - 显示："系统已保存为应急候选稿。请先采用候选稿或重写本场，再继续生成下一场"
   - 如果有候选稿 ID，也显示
   - 所有继续生成的按钮和选项卡均禁用
2. **用户决策：
   - 用户必须采用候选稿替换正文
   - 用户放弃候选稿并重写
   - 用户使用重写当前场景
3. **状态清除：
   - 一旦用户采取上述任一操作后，暂停状态自动清除
   - 可以继续生成

### 18.4 下阶段计划

**Phase T3-D4.5：** UI/FlowPanel 联动优化
- 在 FlowPanel 中显示 fallback 状态
- 提供更直观的用户交互

### 18.5 结论

**Phase T3-D4.4 ✅ 完成！**

Fallback 现在不会再污染正式正文，用户有完全的控制权。可以进入下一个阶段。
