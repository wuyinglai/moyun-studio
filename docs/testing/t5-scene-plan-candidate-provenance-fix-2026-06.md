# T5.17-H2 Scene Plan Candidate Provenance 强化

## 问题背景

在 T5.16 真实样本重建过程中，发现候选稿（candidate）缺少完整的 Scene Plan 来源追踪信息。当 pipeline 使用 Scene Plan 生成 candidate 时，无法追溯该 candidate 是使用了哪个 Scene Plan 生成的，也无法验证生成时使用的 Scene Plan 是否与当前存储的 Scene Plan 一致。

## 修复内容

### 1. Schema 扩展（`backend/schemas/candidate.py`）

在 `CandidateInfo` 和 `CreateCandidateRequest` 中新增三个字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `generation_context` | `Dict[str, Any]` | 生成上下文，包含 `scene_plan_used` 标记 |
| `scene_plan_hash` | `str` | 生成时使用的 Scene Plan 内容哈希 |
| `scene_plan_path` | `str` | 生成时使用的 Scene Plan 文件路径（项目内相对路径） |

### 2. Service 层支持（`backend/core/candidate_service.py`）

在 `create_candidate` 方法中添加三个新参数：
- `generation_context: dict | None = None`
- `scene_plan_hash: str = ""`
- `scene_plan_path: str = ""`

这些参数会被保存到 candidate metadata 中。

### 3. Pipeline 集成（`backend/core/pipeline.py`）

当 pipeline 生成 candidate 时，自动计算并传递 provenance 信息：

```python
# 构建 Scene Plan provenance 信息
generation_context = {}
scene_plan_hash = ""
scene_plan_path = ""

if scene_plan:
    generation_context["scene_plan_used"] = True
    if isinstance(scene_plan, dict):
        scene_plan_str = json.dumps(scene_plan, ensure_ascii=False, sort_keys=True)
        scene_plan_hash = hashlib.md5(scene_plan_str.encode("utf-8")).hexdigest()
    if "source_path" in scene_plan:
        scene_plan_path = scene_plan["source_path"]
else:
    generation_context["scene_plan_used"] = False
```

### 4. 新增测试（`tests/test_candidate_provenance.py`）

覆盖以下场景：
- 创建候选稿时正确记录 Scene Plan provenance
- 创建候选稿时不使用 Scene Plan 的情况
- CandidateInfo schema 包含 provenance 字段
- pipeline 创建候选稿时 provenance 与输入一致
- CandidateInfo 默认值验证

## 验证方法

### 测试覆盖

```bash
python -m pytest tests/test_candidate_provenance.py -v
```

### 现有测试回归

```bash
python -m pytest tests/test_scene_plan_pipeline_integration.py -v
python -m pytest tests/test_scene_plan_generate_api.py -v
```

## 安全说明

- **未调用真实 LLM**：本次修复仅涉及 metadata 字段的添加和传递，不涉及任何 LLM 调用
- **未生成新的 Scene Plan**：所有修改都是向后兼容的，不改变现有数据
- **未修改 workspace 原始数据**：只修改代码和测试文件
- **未覆盖 scoring/final/multi-score/errata/gap-analysis 产物**：不影响现有评分和文档

## 向后兼容性

- 新增字段均有默认值（空字符串或空字典），不影响现有 candidate 数据
- 现有 API 调用无需修改，新增字段为可选参数
- 旧版 candidate metadata 读取时会自动使用默认值

## 溯源验证

通过 `scene_plan_hash` 字段，可以验证 candidate 声称使用的 Scene Plan 是否与当前存储的 Scene Plan 一致：

```python
import hashlib
import json

# 验证 candidate 的 scene_plan_hash
def verify_provenance(candidate, current_scene_plan):
    scene_plan_str = json.dumps(current_scene_plan, ensure_ascii=False, sort_keys=True)
    computed_hash = hashlib.md5(scene_plan_str.encode("utf-8")).hexdigest()
    return computed_hash == candidate.scene_plan_hash
```

---

**文档版本**: 1.0  
**创建日期**: 2026-06-09  
**关联任务**: T5.17-H2