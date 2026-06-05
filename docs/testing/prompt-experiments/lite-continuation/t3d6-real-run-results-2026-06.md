# Phase T3-D6.3.1 — Lite Prompt Variant 真实实验采集记录

> **创建时间**：2026-06-05
> **阶段**：Phase T3-D6.3.1
> **状态**：环境限制，无法完成真实 LLM 实验采集

---

## 1. 实验意图

本实验旨在采集 Baseline / Variant A / Variant B / Variant C / Variant D 的真实生成结果，对比各 variant 的：
- 自动指标：字数、too_short、template_leak、fallback_used、retry_count、write_skipped、quality_flags、quality_score
- 人工评分：连贯性、可读性、画面感、冲突推进、人物行动、节奏、AI腔、结尾钩子

---

## 2. 环境限制说明

### 2.1 无法完成真实实验的原因

1. **缺少测试项目**：workspace/projects/ 目录下没有现成的测试项目
2. **需要完整项目配置**：Lite API 需要有效的 project_id、选卡数据、故事引擎等
3. **后端服务未启动**：当前没有运行中的后端服务
4. **需要 GUI 环境**：现有测试脚本使用 Playwright，需要浏览器环境

### 2.2 已验证的环境状态

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Python 版本 | ✅ 3.14.4 | 可用 |
| FastAPI | ✅ 0.136.1 | 已安装 |
| LiteLLM | ✅ 1.83.7 | 已安装 |
| LLM API Key | ⚠️ 存在 | 但未验证可用性 |
| 测试项目 | ❌ 无 | workspace/projects/ 为空 |
| 后端服务 | ❌ 未启动 | 需要手动启动 |
| Playwright | ⚠️ 未确认 | 需单独检查 |

### 2.3 重要声明

**本记录不是伪造结果**。

由于环境限制，以下实验记录均为占位结构，待后续在完整环境中执行：

1. 不修改生产 Prompt
2. 不修改生成逻辑
3. 不伪造实验数据
4. 如实记录环境限制

---

## 3. 实验方案（待执行）

### 3.1 前置条件

执行真实实验需要：

1. **创建测试项目**：
   - 在 workspace/projects/ 下创建测试项目
   - 配置 story-engine.md、story-state.md、style-guide.md
   - 准备初始场景文件

2. **启动后端服务**：
   ```bash
   cd backend
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **使用现有测试脚本**：
   - 参考 tests/phase-t3b-continuous-scenes.py
   - 调整为 variant 对比模式

4. **准备 Variant Prompt 补丁**：
   - 读取 docs/testing/prompt-experiments/lite-continuation/*.md
   - 运行时临时合成实验 Prompt
   - **严禁写回 prompts/generate/continuation/main.md**
   - **Variant patch 只用于实验请求上下文或临时 prompt renderer，不落盘到生产 Prompt**

### 3.2 实验执行步骤

#### 步骤 1：创建测试项目

```python
# 创建测试项目结构
test_project = {
    "project_id": "test-variant-001",
    "files": {
        "story-engine.md": "...",
        "story-state.md": "...",
        "style-guide.md": "...",
        "recent-context.md": "...",
    }
}
```

#### 步骤 2：合成实验 Prompt（仅用于实验，不写回生产）

```python
# 读取 variant 文件
variant_c_patch = Path("docs/testing/prompt-experiments/lite-continuation/variant-c-action-conflict-hook.md").read_text()

# 运行时临时合成实验 Prompt
# **不修改、不覆盖、不写入生产 Prompt 文件**
# 只在实验请求内存中或临时 prompt renderer 使用
production_prompt_content = Path("prompts/generate/continuation/main.md").read_text()
experimental_prompt = production_prompt_content + "\n\n" + variant_c_patch
```

#### 步骤 3：调用 Lite API

```python
import requests

response = requests.post("http://localhost:8000/api/lite/write-next", json={
    "project_id": "test-variant-001",
    "action": "write",
    "selected_card": {
        "title": "测试场景",
        "beat": "...",
        "scene": "...",
        "protagonist_desire": "...",
        "obstacle": "...",
        "payoff": "...",
        "hook": "...",
        "advancement": "..."
    },
    "prefs": {...}
})
```

#### 步骤 4：记录结果

```python
result = response.json()["data"]
record = {
    "variant": "variant-c",
    "run_id": "run_001",
    "word_count": len(result["content"]),
    "too_short": "too_short" in result.get("quality_flags", []),
    "template_leak": "template_leak" in result.get("quality_flags", []),
    "fallback_used": result.get("fallback_used", False),
    "retry_count": result.get("retry_count", 0),
    "write_skipped": result.get("write_skipped", False),
    "quality_flags": result.get("quality_flags", []),
    "quality_score": result.get("quality_score"),
}
```

---

## 4. 实验记录表（占位，待真实实验填写）

### 4.1 Baseline 实验结果

| Run ID | 字数 | too_short | template_leak | fallback_used | retry_count | write_skipped | quality_score |
|--------|------|-----------|--------------|--------------|-------------|---------------|---------------|
| run_001 | | | | | | | |
| run_002 | | | | | | | |
| run_003 | | | | | | | |

### 4.2 Variant A 实验结果

| Run ID | 字数 | too_short | template_leak | fallback_used | retry_count | write_skipped | quality_score |
|--------|------|-----------|--------------|--------------|-------------|---------------|---------------|
| run_001 | | | | | | | |
| run_002 | | | | | | | |
| run_003 | | | | | | | |

### 4.3 Variant B 实验结果

| Run ID | 字数 | too_short | template_leak | fallback_used | retry_count | write_skipped | quality_score |
|--------|------|-----------|--------------|--------------|-------------|---------------|---------------|
| run_001 | | | | | | | |
| run_002 | | | | | | | |
| run_003 | | | | | | | |

### 4.4 Variant C 实验结果

| Run ID | 字数 | too_short | template_leak | fallback_used | retry_count | write_skipped | quality_score |
|--------|------|-----------|--------------|--------------|-------------|---------------|---------------|
| run_001 | | | | | | | |
| run_002 | | | | | | | |
| run_003 | | | | | | | |

### 4.5 Variant D 实验结果

| Run ID | 字数 | too_short | template_leak | fallback_used | retry_count | write_skipped | quality_score |
|--------|------|-----------|--------------|--------------|-------------|---------------|---------------|
| run_001 | | | | | | | |
| run_002 | | | | | | | |
| run_003 | | | | | | | |

---

## 5. 人工评分表（占位，待真实实验填写）

### 5.1 Baseline 人工评分

| Run ID | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 结尾钩子 | 建议接入 |
|--------|--------|--------|--------|----------|----------|------|------|----------|----------|
| run_001 | | | | | | | | | |
| run_002 | | | | | | | | | |
| run_003 | | | | | | | | | |

### 5.2 Variant A 人工评分

| Run ID | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 结尾钩子 | 建议接入 |
|--------|--------|--------|--------|----------|----------|------|------|----------|----------|
| run_001 | | | | | | | | | |
| run_002 | | | | | | | | | |
| run_003 | | | | | | | | | |

### 5.3 Variant B 人工评分

| Run ID | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 结尾钩子 | 建议接入 |
|--------|--------|--------|--------|----------|----------|------|------|----------|----------|
| run_001 | | | | | | | | | |
| run_002 | | | | | | | | | |
| run_003 | | | | | | | | | |

### 5.4 Variant C 人工评分

| Run ID | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 结尾钩子 | 建议接入 |
|--------|--------|--------|--------|----------|----------|------|------|----------|----------|
| run_001 | | | | | | | | | |
| run_002 | | | | | | | | | |
| run_003 | | | | | | | | | |

### 5.5 Variant D 人工评分

| Run ID | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 结尾钩子 | 建议接入 |
|--------|--------|--------|--------|----------|----------|------|------|----------|----------|
| run_001 | | | | | | | | | |
| run_002 | | | | | | | | | |
| run_003 | | | | | | | | | |

---

## 6. 综合分析（待真实实验后填写）

### 6.1 自动指标汇总

| Variant | 平均字数 | too_short 次数 | template_leak 次数 | fallback 次数 | 平均 quality_score |
|---------|----------|----------------|-------------------|--------------|-------------------|
| Baseline | | | | | |
| Variant A | | | | | |
| Variant B | | | | | |
| Variant C | | | | | |
| Variant D | | | | | |

### 6.2 决策结论

**当前状态**：环境限制，无法完成真实实验

**待决策**：
- 是否在完整环境中执行真实实验？
- 是否使用模拟数据先完成框架，后续补充真实数据？

---

## 7. 下一步

### 7.1 立即可执行

1. **手动创建测试项目**：
   - 在 workspace/projects/ 下创建测试项目
   - 准备必要文件

2. **启动后端并执行实验**：
   ```bash
   cd backend
   uvicorn backend.main:app --reload
   ```

3. **执行 Variant 对比实验**：
   - 使用实验 harness 合成实验 Prompt（不修改生产文件）
   - 调用 /api/lite/write-next
   - 记录结果

### 7.2 推荐执行顺序

1. 先执行 Baseline 实验（3 次）
2. 再执行 Variant C 实验（3 次）- dry-run 推荐
3. 对比结果后再决定是否执行其他 variant

---

## 8. 相关文档

| 文档 | 说明 |
|------|------|
| `docs/testing/lite-prompt-optimization-variant-analysis-2026-06.md` | 分析框架 |
| `docs/testing/prompt-experiments/lite-continuation/t3d6-variant-dryrun-results.json` | dry-run 结果 |
| `docs/testing/lite-prompt-optimization-variant-run-template-2026-06.md` | 实验记录模板 |
| `tests/phase-t3b-continuous-scenes.py` | 现有测试脚本参考 |