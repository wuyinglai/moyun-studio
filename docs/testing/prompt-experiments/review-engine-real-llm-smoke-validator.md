# Review Engine Validator Report

- **Phase**: T3-D7.3a
- **Engine**: review_engine
- **Mode**: validation
- **Candidates Source**: llm_review_prompt_candidates_3items.json
- **Reviews Source**: review-engine-real-llm-smoke-output.json
- **Expected**: Valid
- **Actual**: Valid
- **Result**: ✅ PASS

## 验证结果

- **验证状态**: 通过
- **错误数量**: 0

### 统计信息

- **总 candidates 数**: 3
- **总 reviews 数**: 3
- **唯一 reviews 数**: 3

## 验证规则

1. **candidate_id 全覆盖**: reviews 必须包含所有 candidates 的 candidate_id
2. **无重复**: 同一个 candidate_id 不能出现多次
3. **无多余**: reviews 中的 candidate_id 必须在 candidates 中存在
4. **必填字段**: candidate_id, confirmed, confidence, severity, action
5. **confidence 范围**: 必须在 0-1 之间
6. **action 枚举**: 必须是 suggest_add_to_settings, suggest_update_settings, suggest_ignore, suggest_user_confirm, suggest_rewrite_text, unresolved
7. **severity 枚举**: 必须是 P0, P1, P2, P3