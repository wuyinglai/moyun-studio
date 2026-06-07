# T5.1.2：本地模型 Professional dry-run smoke test

**执行日期**: 2026-06-07
**执行人**: Solo Agent
**最终状态**: ⚠️ 环境不可用（PARTIAL）

---

## 1. 模型配置

| 配置项 | 值 |
|--------|-----|
| Base URL | `http://10.214.203.226:1238/v1` |
| Model Name | gemma-4-12b-it-uncensored-Q4_K_M |
| API Key | `test` (测试用) |

**说明**: 配置已写入 `.env` 文件，不提交到代码仓库。

---

## 2. 连通性检查

### 测试结果：❌ 不可达

**测试命令**:
```python
import requests
r = requests.post('http://10.214.203.226:1238/v1/chat/completions', json={
    'model': 'gemma-4-12b-it-uncensored-Q4_K_M',
    'messages': [{'role': 'user', 'content': 'OK'}],
    'temperature': 0.1,
    'max_tokens': 16
}, timeout=30)
```

**错误**:
```
requests.exceptions.ReadTimeout: HTTPConnectionPool(host='10.214.203.226', port=1238): Read timed out
```

**结论**: 本地模型服务 `10.214.203.226:1238` 无法访问，可能是：
1. 服务未启动
2. 网络不可达
3. 防火墙阻止

**按任务要求**: "如果本地模型服务不可达，任务不算代码失败，记录为环境不可用即可。"

---

## 3. 基础回归测试

尽管本地模型不可用，以下测试仍然执行并全部通过：

### 3.1 Scene Plan Pipeline 集成测试

```bash
python -m pytest tests/test_scene_plan_pipeline_integration.py -v
```

**结果**: ✅ 5/5 passed

| 测试 | 状态 |
|------|------|
| test_pipeline_without_scene_plan | ✅ PASS |
| test_pipeline_with_valid_scene_plan | ✅ PASS |
| test_pipeline_with_invalid_scene_plan | ✅ PASS |
| test_pipeline_with_candidate_policy_violation | ✅ PASS |
| test_pipeline_scene_plan_soft_integration | ✅ PASS |

### 3.2 Scene Plan Validator + API 测试

```bash
python -m pytest tests/test_scene_plan_validate_api.py tests/test_scene_plan_validator.py -v
```

**结果**: ✅ 21/21 passed

- 7 个 API 测试全部通过
- 14 个 Validator 测试全部通过

### 3.3 Professional Regression Smoke Test

```bash
python tests/test_professional_regression_smoke.py
```

**结果**: ✅ 7/7 passed

| 测试项 | 状态 |
|--------|------|
| 项目打开 | ✅ |
| 文件读写 | ✅ |
| 文件保存 | ✅ |
| CandidatePanel | ✅ |
| Story State | ✅ |
| Materials | ✅ |
| 测试清理 | ✅ |

### 3.4 前端构建

```bash
cd frontend && npm run build
```

**结果**: ✅ 构建成功

```
vite v8.0.12 building client environment for production...
✓ built in 3.86s
dist/index.html                   1.50 kB
dist/assets/index-DUk2NLUc.js   415.91 kB
dist/assets/codemirror-*.js     662.52 kB
```

---

## 4. Professional Dry-run 结果

**状态**: ⚠️ 无法测试（环境不可用）

由于本地模型服务不可达，无法执行真实的 Professional dry-run smoke test。

### 无法验证项

1. ❌ 真实模型下 Professional dry-run 是否返回 candidate
2. ❌ candidate 是否不会直接覆盖正文
3. ❌ CandidatePanel 是否能看到候选稿
4. ❌ adopt 前后的安全机制

### 已验证项（Mock/单元测试）

1. ✅ Scene Plan validate API 软接入 pipeline
2. ✅ pipeline 接收可选 scene_plan 参数
3. ✅ 非法 scene_plan 会阻止 pipeline 执行
4. ✅ candidate 机制在代码层面正确实现

---

## 5. 风险与剩余问题

### 环境问题（已记录）

| 问题 | 说明 | 处理方式 |
|------|------|----------|
| 本地模型不可达 | `10.214.203.226:1238` 超时 | 记录为环境不可用，不算代码失败 |

### 代码层面已验证

| 验证项 | 状态 |
|--------|------|
| Scene Plan 软接入 pipeline | ✅ 通过 |
| Candidate 机制代码结构 | ✅ 通过 |
| API schema 正确性 | ✅ 通过 |
| 前端构建完整性 | ✅ 通过 |

---

## 6. 结论

**总体状态**: ⚠️ **PARTIAL** (环境不可用)

### 评估

1. **本地模型连通性**: ❌ 不可达
2. **代码质量**: ✅ 所有测试通过
3. **Professional dry-run 真实测试**: ⚠️ 因环境问题无法执行
4. **Candidate 安全机制**: ✅ 在代码层面验证通过

### 下次行动

当本地模型服务恢复后，建议执行以下真实测试：

```bash
# 1. 确认模型服务在线
curl -X POST "http://10.214.203.226:1238/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma-4-12b-it-uncensored-Q4_K_M", "messages": [{"role": "user", "content": "OK"}]}'

# 2. 启动后端
cd backend && uvicorn backend.main:app --reload

# 3. 触发 dry-run
POST /api/pipeline/run
{
  "pipeline": "polish",
  "project_id": "test-project",
  "target_file": "chapters/vol-01/ch-001/sec-001.md",
  "output_mode": "candidate"
}

# 4. 验证 candidate 生成
GET /api/candidates/list?project_id=test-project
```

---

## 7. 测试命令汇总

```bash
# 本地模型连通性检查
python -c "import requests; r = requests.post('http://10.214.203.226:1238/v1/chat/completions', json={'model': 'gemma-4-12b-it-uncensored-Q4_K_M', 'messages': [{'role': 'user', 'content': 'OK'}], 'temperature': 0.1, 'max_tokens': 16}, timeout=30); print(r.status_code, r.text[:200])"

# Scene Plan 集成测试
python -m pytest tests/test_scene_plan_pipeline_integration.py -v

# Scene Plan API + Validator 测试
python -m pytest tests/test_scene_plan_validate_api.py tests/test_scene_plan_validator.py -v

# Professional 回归测试
python tests/test_professional_regression_smoke.py

# 前端构建
cd frontend && npm run build
```

---

## 8. 相关文档

- [T5.1：Scene Plan validate API 软接入](./t5-writing-loop-gap-analysis-2026-06.md)
- [Professional Candidate Flow E2E](./professional-candidate-flow-e2e-result-2026-06.md)
