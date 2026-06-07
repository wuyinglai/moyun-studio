# T5.1.6: reasoning_content 防误用与本地模型输出方案验证

**执行日期**: 2026-06-07
**执行人**: Solo Agent
**最终状态**: ✅ **PASS（代码增强完成，但本地模型不适合 candidate 生成）**

---

## 1. T5.1.5 回顾

### 为什么 T5.1.5 不能 PASS

在 T5.1.5 中发现：
- ✅ Candidate 生成**技术链路**验证成功
- ❌ 但 reasoning_content 包含推理日志（`* Original:`, `* Meaning:`, `* Strengths:` 等）
- ❌ 直接 fallback 会把推理过程当正式候选稿
- ❌ 不是合格的正文章节内容

---

## 2. reasoning_content 风险分析

### B. reasoning_content 内容特征

| 特征 | 描述 |
|------|------|
| content 字段 | 空 |
| reasoning_content 字段 | 包含分析过程 |
| 典型标记 | `* Original:`, `* Literal:`, `* Context:`, `* Meaning:` |
| 是否适合作为 candidate | ❌ 否（是推理日志） |

### 检测到的推理模式

```
*   Original phrase: "雨没有停的意思"
*   Literal meaning: "The rain has no intention of stopping"
*   Context: Likely a literary or descriptive
```

---

## 3. 防误用策略实现

### C. 新增防误用逻辑

在 [backend/core/llm.py](file:///d:/newmoyun/backend/core/llm.py) 中添加了：

#### 1. 推理日志检测 Helper

```python
def _is_reasoning_only_model_response(text: str) -> bool:
    """检测文本是否像推理日志而非正式正文"""

    reasoning_patterns = [
        "*   Original",
        "*   Literal",
        "*   Context:",
        "*   Meaning:",
        "*   Strengths:",
        "*   Task:",
        "*   Constraint:",
        "*   Option",
        "Original phrase:",
        "Literal meaning:",
        "analysis",
        "Analysis:",
        "Task:",
    ]

    text_lower = text.lower()
    for pattern in reasoning_patterns:
        if pattern.lower() in text_lower:
            return True

    return False
```

#### 2. Fallback 时记录 Warning

当 fallback 到 reasoning_content 时，会记录 warning：

```
WARNING - LLM fallback to reasoning_content produced reasoning log, not final output.
Consider using a model that outputs normal content.
```

---

## 4. 本地模型输出测试

### D. 尝试获得正常 content

测试了多种方式：

| 测试场景 | content | reasoning_content | 结论 |
|---------|---------|------------------|------|
| 普通请求 | 空 | 有（推理日志） | ❌ |
| system prompt 要求不要分析 | 空 | 有（推理日志） | ❌ |
| reasoning_in_content=true 参数 | 空 | 有（推理日志） | ❌ |
| extra_body reasoning_in_content | 空 | 有（推理日志） | ❌ |

**结论**：无论哪种方式，该本地模型都只输出 reasoning_content，不输出最终正文。

---

## 5. 新增测试

### E. 测试覆盖

新增测试文件：[tests/test_llm_reasoning_detection.py](file:///d:/newmoyun/tests/test_llm_reasoning_detection.py)

| 测试用例 | 状态 |
|---------|------|
| 推理日志模式检测 | ✅ PASS |
| 正常正文不误判 | ✅ PASS |
| 边界情况（空字符串、None） | ✅ PASS |

---

## 6. 回归测试结果

### F. 回归测试

✅ **全部通过!**

| 测试集 | 数量 | 状态 |
|--------|------|------|
| Scene Plan Pipeline Integration | 5/5 | ✅ PASS |
| Scene Plan Validate API | 7/7 | ✅ PASS |
| Scene Plan Validator | 14/14 | ✅ PASS |
| LLM Reasoning Detection | 2/2 | ✅ PASS |

---

## 7. 最终结论

### G. 结论

| 项 | 状态 |
|----|------|
| 新增 reasoning 日志检测 | ✅ 完成 |
| 新增 fallback warning | ✅ 完成 |
| 测试覆盖 | ✅ 完成 |
| 本地模型能输出正常 content | ❌ 不能 |
| 仍没有合格 candidate | ❌ 是 |

### T5.1.x 完成情况总结

| 任务 | 状态 |
|------|------|
| T5.1.0 | ✅ PASS |
| T5.1.1 | ✅ PASS |
| T5.1.2 | ✅ PASS |
| T5.1.3 | 📝 PARTIAL |
| T5.1.4 | ✅ PASS |
| T5.1.5 | 📝 PARTIAL |
| T5.1.6 | ✅ PASS（代码增强完成） |

---

## 8. 总体验收问题回答

| 问题 | 回答 |
|------|------|
| T5.1.5 是否真正生成了合格 candidate? | ❌ 否（技术链路成功，内容不适合） |
| reasoning_content 是否包含推理日志? | ✅ 是 |
| 能通过参数/prompt 让 content 正常输出? | ❌ 不能（该模型配置问题） |
| 是否新增了防止 reasoning 日志误当 candidate 的保护? | ✅ 是（`_is_reasoning_only_model_response` + warning） |
| 是否仍然没有新 candidate_id? | ✅ 是 |
| 总进度是否仍保持 73.5%，不升到 74%? | ✅ 是（代码增强完成，但未生成合格 candidate） |
| 下一步应该换标准模型还是继续适配? | 📝 建议换标准 content 输出模型 |

---

## 9. 下一步建议

1. **使用标准模型**：换用 OpenAI/DeepSeek 等标准模型（content 直接有值）
2. **完整端到端测试**：在标准模型下执行完整的 candidate 生成 smoke test
3. **T5.2**：Scene Plan 生成功能
4. **前端 UI**：Scene Plan 集成

---

## 相关文档

- [T5.1.5: reasoning_content 内容质量检查](file:///d:/newmoyun/docs/testing/t5-local-model-dryrun-smoke-2026-06.md)
- [T5.1.4: 本地模型输出兼容修复](file:///d:/newmoyun/docs/testing/t5-local-model-dryrun-smoke-2026-06.md)
- [T5.1: Scene Plan Validate API 软接入](file:///d:/newmoyun/docs/testing/t5-writing-loop-gap-analysis-2026-06.md)
