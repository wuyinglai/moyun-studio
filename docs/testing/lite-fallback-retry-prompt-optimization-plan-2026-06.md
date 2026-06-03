# Lite Fallback、自动重试与 Prompt 优化方案

> **创建时间**：2026-06-03
> **测试阶段**：Phase T3-D
> **设计背景**：基于 Phase T3-C 质量评分结果设计

---

## 1. 背景

Phase T3-B 系列真实功能测试已完成核心验收：
- Agnes LLM 单场景生成通过
- Candidate 改稿流程通过
- next-options 链路诊断通过
- 连续生成文件推进功能通过

但 Phase T3-B-13 测试中发现关键问题：第 2 场 702 字是 **fallback 模板内容**，不是真实 LLM 生成！

**Phase T3-B-13 关键数据回顾**：

| 场次 | 文件路径 | 字数 | 是否 fallback | 是否真实生成 |
|------|----------|------|--------------|--------------|
| 1 | sec-001.md | 1701 | 否 | ✅ |
| 2 | sec-002.md | 702 | **是** | ❌ |
| 3 | sec-003.md | 2163 | 否 | ✅ |

**质量评分结果**：
- 真实生成（场次 1、3）质量优秀：4.6/5 和 4.7/5
- Fallback 内容（场次 2）质量极低：1.7/5，不可用于正式生成

**关键发现**：Fallback 模板内容包含系统占位符 `（最近5章摘要，由系统自动维护）`，模板化严重，用户无法区分这是 fallback 还是真实生成。

---

## 2. 当前问题

### 2.1 Fallback 相关问题

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| **Fallback 直接进入正文** | 高 | 用户不知道这是应急草稿 |
| **前端无法区分 Fallback** | 高 | 没有结构化标记，只能靠文字推测 |
| **Fallback 模板质量低** | 中 | 包含系统占位符，内容空洞 |
| **测试报告误判** | 中 | 可能把 fallback 当成 LLM 质量问题 |

### 2.2 可靠性相关问题

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| **无自动重试** | 高 | LLM 超时后直接 fallback，不给机会 |
| **timeout 可能不足** | 中 | 当前 first_token_timeout=8s，token_timeout=12s |
| **Fallback 没有先存为 Candidate** | 中 | 直接覆盖正文，不安全 |

### 2.3 质量检测相关问题

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| **字数阈值未明确** | 低 | 当前没有明确的字数下限要求 |
| **低质量无警告** | 中 | 生成后如果质量低，没有明确提示 |
| **占位符未检测** | 中 | 没有检测模板占位符的逻辑 |

---

## 3. 当前代码链路

### 3.1 Fallback 触发链路（流式）

**文件位置**：`backend/api/lite.py` 第 867-887 行

```python
used_fallback = False
try:
    async for chunk in lite_llm.stream_llm_content(
        [{"role": "user", "content": prompt}],
        first_token_timeout=8,
        token_timeout=12,
        # ...
    ):
        content_parts.append(chunk)
        yield _lite_stream_event("delta", {"delta": chunk})
except Exception as e:
    logger.warning("爽文模式流式正文生成超时或失败，使用临时草稿: %s", e)
    fallback = _fallback_section_content(target_file, req.selected_card, prefs_text, story_engine)
    content_parts = [fallback]
    used_fallback = True
```

**关键观察**：
1. 有 `used_fallback` 变量记录是否使用 fallback
2. 但这个变量只在 `quality_summary` 文字描述中提到（第 919 行）
3. **没有在 SSE 的 meta/done 事件中结构化标记**

### 3.2 SSE 响应结构

**meta 事件**（第 796-801 行）：
```python
yield _lite_stream_event("meta", {
    "file_path": output_file,
    "source_file": target_file,
    "is_candidate": is_candidate,
    "label": section_label(target_file),
})
```

**done 事件**（第 958-966 行）：
```python
yield _lite_stream_event("done", {
    "file_path": output_file,
    "content": content,
    "quality_summary": quality_summary,  # 这里只有文字提到 fallback
    # ...
})
```

**关键观察**：
- `meta` 和 `done` 事件中都没有 `fallback_used` 字段
- 前端只能通过 `quality_summary` 的文字间接判断

### 3.3 fallback 模板（第 308-334 行）

```python
def _fallback_section_content(...):
    return "\n\n".join([
        f"# {label} {selected_card.title}",
        f"{selected_card.scene}里，人声原本很稳。直到门口那道身影出现，所有目光才像被一只看不见的手拨动，同时转了过去。",
        # ... 模板化内容 ...
        f"更远处，一道沉默的视线停了很久，因为{selected_card.hook}。",
    ])
```

**关键观察**：
- 完全是硬编码模板
- 没有结合故事状态
- 第 2 场问题正是这个模板

---

## 4. 方案 A：Fallback 显式标记

### 4.1 设计目标

让用户明确知道当前内容是 fallback，不是真实 LLM 生成。

### 4.2 技术方案

#### 4.2.1 后端响应修改

**文件**：`backend/api/lite.py`

**修改点 1：SSE meta 事件添加 fallback_used**
```python
yield _lite_stream_event("meta", {
    "file_path": output_file,
    "source_file": target_file,
    "is_candidate": is_candidate,
    "label": section_label(target_file),
    "fallback_used": False,  # 初始状态
})
```

**修改点 2：SSE done 事件明确标记**
```python
yield _lite_stream_event("done", {
    "file_path": output_file,
    "content": content,
    "quality_summary": quality_summary,
    "fallback_used": used_fallback,  # 新增结构化字段
    "fallback_reason": str(e) if used_fallback else None,  # 可选
    # ...
})
```

**修改点 3：非流式响应也添加**
```python
return ApiResponse.ok(LiteWriteNextResponse(
    file_path=output_file,
    content=content,
    quality_summary=quality_summary,
    fallback_used=used_fallback,  # 新增
    # ...
), message="场景已生成")
```

#### 4.2.2 前端 UI 显示

**文件**：`frontend/src/views/LiteWritingView.vue`

**设计**：
1. 编辑器顶部显示醒目的 "⚠️ 应急草稿" 标签
2. 文字颜色：橙色/红色
3. 显示建议："建议点击"重写当前场景"补成正式正文"
4. FlowPanel 中标记 fallback 节点

**示意**：
```vue
<div v-if="fallbackUsed" class="fallback-warning">
  <span class="warning-icon">⚠️</span>
  <span>应急草稿 - 建议点击"重写当前场景"</span>
</div>
```

#### 4.2.3 测试报告记录

**文件**：`docs/testing/screenshots/t3b-continuous-results.json`

新增字段：
```json
{
  "index": 2,
  "charCount": 702,
  "title": "第2场景 当场反逼",
  "fallbackUsed": true,
  "fallbackReason": "LLM timeout",
  // ...
}
```

---

## 5. 方案 B：Fallback 自动重试

### 5.1 设计目标

在直接进入 fallback 前，先给 LLM 一次重试机会。

### 5.2 技术方案

#### 5.2.1 重试策略

| 配置 | 建议值 | 说明 |
|------|--------|------|
| 重试次数 | 1 次 | 先尝试简单方案，可后续调整 |
| 退避时间 | 2s | 重试前短暂等待 |
| 超时时间（重试） | 比第一次长 50% | first_token_timeout: 12s, token_timeout: 18s |

#### 5.2.2 后端实现

**文件**：`backend/api/lite.py` 第 867-887 行

```python
used_fallback = False
retries = 0
max_retries = 1
content_parts: list[str] = []

while retries <= max_retries:
    try:
        current_first_timeout = 8 * (1 + retries * 0.5)  # 8s → 12s
        current_token_timeout = 12 * (1 + retries * 0.5)  # 12s → 18s
        
        yield _lite_stream_event("status", {
            "message": f"AI 正在写正文... (重试 {retries}/{max_retries})" if retries > 0 else "AI 正在写正文..."
        })
        
        async for chunk in lite_llm.stream_llm_content(
            [{"role": "user", "content": prompt}],
            first_token_timeout=current_first_timeout,
            token_timeout=current_token_timeout,
            # ...
        ):
            content_parts.append(chunk)
            yield _lite_stream_event("delta", {"delta": chunk})
        break  # 成功，退出循环
    except Exception as e:
        retries += 1
        if retries <= max_retries:
            logger.warning("LLM 调用失败，准备重试 (%d/%d): %s", retries, max_retries, e)
            await asyncio.sleep(2)  # 退避
        else:
            logger.warning("多次重试失败，使用 fallback: %s", e)
            fallback = _fallback_section_content(...)
            content_parts = [fallback]
            used_fallback = True
```

#### 5.2.3 前端状态显示

在生成状态中显示重试信息，让用户知道系统在努力。

---

## 6. 方案 C：Fallback 不直接覆盖正文

### 6.1 设计目标

Fallback 内容不要直接写入正式正文，而是先存为 Candidate，用户确认后才采用。

### 6.2 技术方案

#### 6.2.1 策略

- 如果 fallback 触发，自动设置 `is_candidate=True`
- 这样 fallback 内容会存为候选稿，不会直接覆盖正文
- 用户可以选择采用或重写

#### 6.2.2 后端实现

**文件**：`backend/api/lite.py` 第 791 行附近

```python
# 原有逻辑
is_candidate = _should_use_candidate(req.action, target_file, requested_content, is_blank_requested)

# 新增：如果会 fallback，强制 candidate
if is_blank_requested or target_file in [f"{_sec}" for _sec in [1, 2, 3]]:
    # 先不硬改，而是在触发 fallback 时才调整
    pass

# 在触发 fallback 时（第 884-887 行）
except Exception as e:
    logger.warning("爽文模式流式正文生成超时或失败，使用临时草稿: %s", e)
    fallback = _fallback_section_content(target_file, req.selected_card, prefs_text, story_engine)
    content_parts = [fallback]
    used_fallback = True
    # 强制使用 candidate
    if not is_candidate:
        is_candidate = True
        # 重新初始化 candidate_info
```

---

## 7. 方案 D：低质量检测

### 7.1 检测维度

| 检测项 | 阈值 | 说明 |
|--------|------|------|
| **字数不足** | < 800 字 | Phase T3-C 发现第 2 场 702 字就是 fallback |
| **占位符检测** | 检测 "（最近5章摘要，由系统自动维护）" | 这是 fallback 的典型特征 |
| **冲突推进检测** | 简单关键词匹配（可选） | 检测是否有明确冲突 |

### 7.2 技术方案

#### 7.2.1 质量检查函数

**文件**：`backend/application/lite_quality_service.py`

新增：
```python
@staticmethod
def has_template_placeholder(content: str) -> bool:
    """检测是否有模板占位符"""
    placeholder = "（最近5章摘要，由系统自动维护）"
    return placeholder in content

@staticmethod
def is_word_count_sufficient(content: str, min_words: int = 800) -> bool:
    """检查字数是否足够"""
    return len(content) >= min_words

@staticmethod
def get_quality_warnings(content: str) -> list[str]:
    """获取质量警告列表"""
    warnings = []
    if LiteQualityService.has_template_placeholder(content):
        warnings.append("发现模板占位符，可能是应急草稿")
    if not LiteQualityService.is_word_count_sufficient(content):
        warnings.append(f"字数不足（当前 {len(content)} 字，建议 800+）")
    return warnings
```

---

## 8. 方案 E：Prompt 优化方向

### 8.1 优化原则

**优先级说明**：
- 先做可靠性（方案 A/B/C）
- 再做 Prompt 优化（方案 E）
- 因为真实 LLM 生成（场次 1、3）质量已经很好了

### 8.2 字数约束优化

**建议**：在 Prompt 中明确要求字数范围

```
字数要求：
- 目标：1000-1500 字
- 最少：900 字
- 不要：少于 800 字
```

### 8.3 场景结构优化

**建议**：要求明确的三段式结构

```
结构要求：
1. 开场：具体场景 + 人物引入 + 冲突出现
2. 发展：冲突升级 + 行动链 + 转折
3. 结尾：明确兑现 + 钩子（为下一场准备）
```

### 8.4 冲突推进优化

**建议**：要求每一场必须有明确的冲突推进

```
冲突要求：
- 本场必须让冲突比前一场更紧张
- 不能只是过渡或铺垫
- 主角必须有明确行动，不能只被动接受
```

### 8.5 结尾钩子优化

**建议**：钩子要具体，不能泛泛而谈

```
钩子要求：
- 不能只写"更远处，一道沉默的视线停了很久"
- 要包含具体的细节：谁？为什么？下一场可能会发生什么？
```

### 8.6 避免 AI 腔优化

**建议**：列出常见的 AI 腔，要求避免

```
避免以下模板化表达：
- "那双眸子正缓缓睁开"
- "眼中闪过一丝慌乱"
- "那人不是别人，正是..."
- "像是被一只看不见的手拨动"
```

---

## 9. 推荐实施顺序

基于风险和收益分析，建议按以下顺序实施：

| 阶段 | 方案 | 优先级 | 预计工作量 | 说明 |
|------|------|--------|------------|------|
| **Phase T3-D1** | Fallback 显式标记 | 🔴 高 | 2h | 让用户知道这是 fallback，最重要 |
| **Phase T3-D2** | 自动重试 1 次 | 🔴 高 | 3h | 在 fallback 前先重试，减少触发 |
| **Phase T3-D3** | Fallback candidate 化 | 🟡 中 | 4h | 不要直接覆盖正文，更安全 |
| **Phase T3-D4** | 低质量检测 | 🟡 中 | 3h | 检测字数和占位符 |
| **Phase T3-D5** | Prompt 优化 | 🟢 低 | 4h | 因为真实生成质量已经很好 |

---

## 10. 风险分析

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 自动重试增加耗时 | 中 | 用户等待时间变长 | 只重试 1 次，超时时间不要太长 |
| fallback 不写正文影响流程连续 | 中 | 用户需要多一步操作 | 在 UI 上提供明确的引导 |
| 过度质量检测误判 | 低 | 把好内容当成坏内容 | 先只做字数和占位符检测，不做复杂判断 |
| Prompt 字数约束增加成本 | 低 | 可能增加 token 使用 | 先做实验，看效果再决定 |

---

## 11. 验收标准

### 11.1 Phase T3-D1 验收标准

- [ ] 后端 SSE meta/done 事件包含 `fallback_used` 字段
- [ ] 前端 UI 显示醒目的 fallback 警告
- [ ] 测试报告可以区分真实生成和 fallback
- [ ] 文档更新

### 11.2 Phase T3-D2 验收标准

- [ ] LLM 超时后自动重试 1 次
- [ ] 重试超时时间比第一次长
- [ ] UI 显示重试状态
- [ ] 重试成功后不再 fallback
- [ ] 文档更新

### 11.3 Phase T3-D3 验收标准

- [ ] Fallback 内容自动保存为 candidate
- [ ] 不会直接覆盖正式正文
- [ ] 用户可以选择采用或重写
- [ ] 文档更新

### 11.4 Phase T3-D4 验收标准

- [ ] 检测字数是否 > 800
- [ ] 检测是否有模板占位符
- [ ] 低质量时有明确警告
- [ ] 文档更新

### 11.5 Phase T3-D5 验收标准

- [ ] Prompt 包含字数要求
- [ ] Prompt 包含结构要求
- [ ] 真实生成字数稳定在 1000-1500
- [ ] 对比测试结果记录
- [ ] 文档更新

---

## 12. 结论

### 12.1 关键总结

| 问题 | 优先级 | 是否立即修 |
|------|--------|-----------|
| **Fallback 没有标记** | 🔴 高 | ✅ 是，Phase T3-D1 |
| **没有自动重试** | 🔴 高 | ✅ 是，Phase T3-D2 |
| **Fallback 直接覆盖正文** | 🟡 中 | 是，Phase T3-D3 |
| **Prompt 优化** | 🟢 低 | 暂缓，先做可靠性 |

### 12.2 为什么先不修 Prompt？

因为真实 LLM 生成（场次 1、3）的质量已经很好了：
- 场次 1：1701 字，4.6/5 分
- 场次 3：2163 字，4.7/5 分

当前主要问题是 **LLM 调用可靠性**，不是 **Prompt 质量**。

### 12.3 是否进入下一阶段？

✅ **可以进入 Phase T3-D1（Fallback 显式标记）**
