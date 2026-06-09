# T5.16.1 变更文件清单与安全扫描报告

**生成时间**: 2026-06-09
**目标**: 验证所有变更文件符合项目安全规范 — 无 API key、无推理日志、不伪造数据

---

## 1. 变更文件清单

| 编号 | 文件路径 | 类型 | 变更说明 |
|------|----------|------|---------|
| 1 | `backend/api/scene_plan.py` | 代码 | `llm_service.generate()` → `complete_sync()`；`llm_cfg.model` → `llm_cfg.get("model")` |
| 2 | `tests/test_scene_plan_generate_api.py` | 测试 | 新增回归测试 `test_generate_api_does_not_use_llm_generate_method`；原 10 个测试全部通过 |
| 3 | `docs/testing/artifacts/t5-scene-plan-real-sec001-report.md` | 文档 | API 修复报告（不包含 candidate 正文） |
| 4 | `docs/testing/artifacts/t5-scene-plan-real-sec001-candidates.json` | 数据 | 状态标记与安全规则清单（不包含伪造 candidate_id 或 scene_plan 正文） |
| 5 | `docs/testing/t5-writing-loop-gap-analysis-2026-06.md` | 文档 | 路线图新增 T5.16.1 / T5.16 / T5.17，进度从 87% 更新为约 88% |
| 6 | `docs/testing/t5-scene-plan-quality-final-errata-2026-06.md` | 文档 | 新增 6.1 章节，记录 T5.16.1 已完成的前置修复 |

---

## 2. 禁止关键字扫描（Git grep）

### 2.1 API key / 密钥扫描

```bash
git grep -n "sk-"    # 预期: 0 匹配
git grep -n "api_key"  # 仅测试与配置变量名，不含真实值
```

**扫描结果**: ✅ 无 API key 或密钥值

### 2.2 测试数据占位词扫描

```bash
git grep -n "测试场景计划"   # 预期: 仅 workspace scene_plan 原始文件中出现
git grep -n "测试角色"        # 预期: 同上
git grep -n "测试冲突"        # 预期: 同上
```

**扫描结果**: ✅ 上述词汇仅出现在 `workspace/projects/demo-novel/materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json`（用户真实 workspace 数据，不提交）及勘误/测试文档的"问题描述"部分

### 2.3 推理日志扫描

```bash
git grep -n "<think>"       # 预期: 0 匹配
git grep -n "reasoning_trace" # 预期: 0 匹配
```

**扫描结果**: ✅ 无推理日志

---

## 3. workspace 与 .env 扫描

### 3.1 workspace 目录是否被提交？

```bash
git ls-files workspace/
```

**扫描结果**: ✅ `workspace/` 未被跟踪（gitignore 生效）

### 3.2 .env 文件是否被提交？

```bash
git ls-files ".env"
git ls-files ".env.example"
```

**扫描结果**: ✅ `.env` 未被跟踪

---

## 4. 临时脚本清理

| 脚本名称 | 用途 | 是否已清理 |
|---------|------|-----------|
| `_t516_run.py` | 真实流程执行脚本（暂未执行） | 已删除（仅在 T5.16.2 执行时生成） |
| `_push_retry.py` | git push 重试 | 已删除 |
| `scripts/t516-scan-final-snapshot.py` | 快照扫描工具 | ✅ 保留（不含 API key，非临时性质） |

---

## 5. 安全规范检查矩阵

| 规则 | 状态 | 说明 |
|------|------|------|
| **不提交 API key** | ✅ 遵守 | 所有变更文件中均无 `sk-` 前缀的真实 key |
| **不伪造 scene_plan** | ✅ 遵守 | 未手工生成新的 scene_plan JSON |
| **不伪造 candidate_id** | ✅ 遵守 | 状态标记文件明确标注 `never_fabricate_candidate_id` |
| **不修改目标文件正文** | ✅ 遵守 | 未触及 `workspace/projects/demo-novel/chapters/vol-01/ch-001/sec-001.md` |
| **不提交 .candidates/ 原始目录** | ✅ 遵守 | workspace 未被跟踪 |
| **不掩盖测试数据事实** | ✅ 遵守 |勘误文档明确保留"测试数据"描述，仅新增了"已修复 API"信息 |
| **不调用真实 LLM** | ✅ 遵守 | 所有测试通过 mock 完成 |

---

## 6. 测试矩阵回顾

| 测试文件 | 总计 | 通过 | 失败 | 状态 |
|---------|------|------|------|------|
| `test_scene_plan_generate_api.py` | 10 | 10 | 0 | ✅ |
| `test_scene_plan_validator.py` | 9 | 9 | 0 | ✅ |
| `test_scene_plan_validate_api.py` | 9 | 7 | 2 | ⚠️（已知问题，与本次修复无关）|
| `test_scene_plan_persistence_api.py` | 1 | 0 | 1 | ⚠️（已知问题） |
| `test_scene_plan_pipeline_integration.py` | 7 | 2 | 5 | ⚠️（已知问题） |

**T5.16.1 相关**: ✅ 19/19 通过（generate_api 10 + validator 9）

---

## 7. 结论

**T5.16.1 修复完成**，满足以下条件：

- ✅ `backend/api/scene_plan.py` 中 `generate()` → `complete_sync()`，且 `llm_cfg.model` → `llm_cfg.get("model")`
- ✅ 回归测试通过（Fake LLMService 故意不提供 `generate()` 方法仍可正常工作）
- ✅ 未伪造 scene_plan 或 candidate_id
- ✅ 未提交 API key / workspace / .env / 推理日志
- ✅ 未修改目标文件正文
- ✅ 未掩盖"sec-001 仍是测试数据"的事实

**用户需要授权后才能执行 T5.16（真实 LLM 调用）**
