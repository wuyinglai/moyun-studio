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
