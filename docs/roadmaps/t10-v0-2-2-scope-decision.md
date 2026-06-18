# T10.0 / v0.2.2 Scope Decision

## 基本信息

| 字段 | 值 |
|------|-----|
| Task Title | T10.0 / v0.2.2 Scope Decision |
| Risk Level | Risk C / Planning + Release Strategy |
| Mode | Planning Document Only, No Product Code |
| Branch | main |
| Base Commit | d9830f9 |
| Date | 2026-06-17 |

---

## 1. 当前发布状态

```text
v0.2.0 — Writing Quality Loop Developer Preview（2026-06-16, tag v0.2.0）
v0.2.1 — Writing Quality Enhancement Release（2026-06-17, tag v0.2.1 → fa99483）
archive commit: 51741e5
post-release roadmap commit: d9830f9
GitHub Release: https://github.com/wuyinglai/moyun-studio/releases/tag/v0.2.1
T9 阶段已全部完成（T9.0 - T9.5）
```

---

## 2. v0.2.1 稳定基线

### 测试基线

| 指标 | 结果 |
|------|------|
| Backend release gate | 52 passed |
| Backend 完整回归 | 115 passed |
| Frontend build | passed |
| Focused E2E（14-candidate-workflow） | 23 passed |
| Full mock E2E | 77 passed / 93 skipped / 0 failed |
| Real LLM dogfood（Agnes AI） | 8 cases passed |
| API key 安全检查 | clean |

### 已实现能力

- **Quality Metadata MVP** — 5 维度自动计算
- **Repair Candidate MVP** — 不修改 parent/source
- **Continuity Anchors metadata** — 5 类锚点 + auto-fetch
- **Safety boundaries** — adopted/discarded parent 不可 revision/repair
- **Pipeline prompt rendering cleanup** — 归档问题已不存在
- **Real LLM dogfood** — 真实中文场景验证

---

## 3. T9 已完成能力

| Priority | 状态 | 范围 |
|----------|------|------|
| T9.1 Release Candidate | ✅ | v0.2.0 发布 |
| T9.2 测试债务专项 | ✅ | focused E2E recovery |
| T9.3 Continuity Anchors | ✅ | 5 类锚点 + service |
| T9.4 写作质量增强 | ✅ | Quality Metadata + Repair |
| T9.5 Pipeline Prompt Cleanup | ✅ | 归档问题已不存在 |

---

## 4. 已知技术债

### 来自 v0.2.1 release final report

| # | 债务 | 优先级 | 影响 |
|---|------|--------|------|
| D1 | Guardrails allowlist 噪音 | P3 | 低，不影响核心 |
| D2 | T9.4 文档分散在 docs/design/ | P3 | 低，仅文档整理 |
| D3 | 93 E2E skipped | P3 | 测试债务 |
| D4 | T9.4a-b-c 实现报告缺失 | P3 | 文档缺失 |

### 来自 docs/known-issues.md

| # | 债务 | 优先级 | 来源 |
|---|------|--------|------|
| D5 | 内存端点无冲突检测 | P2 | NB1 |
| D6 | 非核心 API 同步 I/O | P3 | NB2 |
| D7 | 真实 LLM E2E 可选 | P2 | NB3 |
| D8 | 工作区 .config.json 明文 | P2 | NB4 |
| D9 | 多标签页编辑无冲突保护 | P3 | NB5 |

### 来自 T9.4-final-stage-closure.md

| # | 债务 | 优先级 | 备注 |
|---|------|--------|------|
| D10 | Pipeline prompt 模板缺失 | P3 | T9.5 已部分清理，剩余可继续 |
| D11 | T9.4a-b-c 文档 | P3 | 单独 doc 文件缺失 |

---

## 5. v0.2.2 方案

### 5.1 决策：建议做 v0.2.2

**判断**：**条件建议（推荐）** — 先做 v0.2.2 维护版，再进入 T10 新功能阶段。

**理由**：

1. **v0.2.1 已稳定** — 所有 release gate 通过，无 critical issue。
2. **有明确的技术债需要清理** — 主要是 D1, D2, D3, D11，影响维护效率和文档质量。
3. **避免在新功能基线上累积债务** — T10 新功能应基于干净的基线。
4. **维护版周期短、风险低** — 主要是文档 + 噪音清理 + 测试债务收敛。
5. **T10 新功能应独立规划** — Story State UI、Candidate Compare 是大方向，需要单独设计。

### 5.2 v0.2.2 定位

**类型**：维护版（maintenance release）— 文档整理 + 噪音清理 + 测试债务收敛。

**核心原则**：
- 不引入新功能
- 不修改 T9.4 已发布的逻辑
- 不打 performance/data structure 优化 tag
- 重点是清理 + 文档化

### 5.3 v0.2.2 候选范围

| # | 项目 | 优先级 | 风险 | 估计 |
|---|------|--------|------|------|
| V1 | Guardrails allowlist cleanup | P3 | Risk B | 小 |
| V2 | T9.4 文档合并（plan + 4 sub-reports 整理） | P3 | Risk C | 小 |
| V3 | Release notes polish（v0.2.0/v0.2.1 标题统一、链接校验） | P3 | Risk C | 极小 |
| V4 | Known issues cleanup（v0.2 → v0.2.2 标签更新） | P3 | Risk C | 小 |
| V5 | Pipeline prompt 模板补全（D10 剩余） | P3 | Risk B | 小 |
| V6 | T9.4a-b-c 实现报告补充（D4, D11） | P3 | Risk C | 小 |
| V7 | Minor smoke test improvements（部分 skipped 恢复或归档） | P3 | Risk B | 中 |

**建议 v0.2.2 范围**：V1 + V2 + V3 + V4 + V6（小范围、低风险）

**不建议放进 v0.2.2**：
- V5 Pipeline prompt 模板（影响 prompt 逻辑，应单独评估）
- V7 skipped E2E 恢复（影响测试基础设施）
- D5-D9 来自 known-issues（涉及产品代码或安全设计，应单独规划）

---

## 6. T10 方案

### 6.1 T10 定位

**T10**：候选稿质量增强 + 长文连续性深化

**核心原则**：
- 基于 v0.2.2 干净基线
- 不破坏 candidate-only 安全边界
- 不自动覆盖正式正文
- 大功能应分 MVP → 完整版 分阶段推进

### 6.2 T10 候选方向 + 优先级

| 优先级 | 方向 | 目标价值 | 风险 | 依赖 |
|--------|------|----------|------|------|
| P0 | Quality Explanation UI | 帮助用户理解 quality score | Risk B | 无 |
| P0 | Candidate Compare（基础版） | 横向对比多个 candidate | Risk B+ | 无 |
| P1 | Story State UI（最小） | 让用户查看/编辑 continuity anchors | Risk B+ | 无 |
| P1 | Repair UX refinement | 改善 repair 按钮/反馈循环 | Risk B | T9.4 |
| P2 | Dogfood workspace templates | 提供 dogfood 项目模板 | Risk C | 无 |
| P2 | Long-form project dashboard | 项目级统计/进度 | Risk B+ | 多个 |

### 6.3 T10 推荐排序理由

1. **Quality Explanation P0**：
   - 用户最大痛点：看不懂 quality score
   - 可纯前端，不影响后端
   - 为 Candidate Compare 打基础

2. **Candidate Compare P0**：
   - 用户在 v0.2.1 后已经能拿到 quality score
   - 缺少对比 → 影响 adopt 决策
   - T9.4 计划中已列为 "T10+"

3. **Story State UI P1**：
   - Continuity anchors 已在 backend 可用
   - 缺 UI 入口 → 用户看不见
   - 是 T9.3 真正落地的下一步

4. **Repair UX refinement P1**：
   - v0.2.1 已实现 repair，但 UX 未优化
   - 风险低，收益明显

5. **Dogfood workspace templates P2**：
   - 改善 dogfood 体验
   - 风险低

6. **Long-form project dashboard P2**：
   - 复杂，需设计
   - 依赖 Story State UI

---

## 7. 取舍判断

### Option A：直接进入 T10

**优点**：保持 momentum，立刻做新功能。

**缺点**：
- 文档噪音/分散问题继续恶化
- 维护效率持续下降
- 新功能可能需要修改已发布逻辑的引用

**结论**：**不推荐**。

### Option B：先 v0.2.2，再 T10

**优点**：
- 维护版时间短、风险低
- 给 T10 一个干净基线
- 可以验证 maintenance flow
- 用户/贡献者看到 v0.2.2 是一次正式维护

**缺点**：
- 节奏稍慢
- 需要先完成 v0.2.2 流程

**结论**：**推荐**。

### Option C：跳过 v0.2.2，直接进入 T10.1

**优点**：最快进入新功能。

**缺点**：
- 债务继续累积
- 失去维护版节奏

**结论**：**不推荐**。

---

## 8. 推荐路线

### 短期（v0.2.2 维护版，1-2 周）

1. v0.2.2a — Guardrails allowlist cleanup（Risk B）
2. v0.2.2b — T9.4 文档合并 + known-issues 更新（Risk C）
3. v0.2.2c — Release notes polish + minor smoke improvements（Risk C）
4. v0.2.2 — 维护版发布（tag v0.2.2 → release commit）

### 中期（T10 阶段，4-6 周）

1. T10.1 — Quality Explanation UI（Risk B）
2. T10.2 — Candidate Compare MVP（Risk B+）
3. T10.3 — Story State UI 最小版（Risk B+）
4. T10.4 — Repair UX refinement（Risk B）

### 长期（v0.3+）

- Long-form project dashboard
- Dogfood workspace templates

---

## 9. 后续 3 个任务

### Task 1：v0.2.2a — Guardrails allowlist cleanup

- **目标**：清理 guardrails allowlist 噪音，更新 solo-guardrails.ps1/sh 的 allowlist 条目
- **风险等级**：Risk B（仅修改 allowlist，不改产品逻辑）
- **是否改代码**：是（仅 guardrails allowlist 列表）
- **验收标准**：
  - `bash scripts/ai-guardrails.sh` 通过
  - `powershell -File scripts/ai-guardrails.ps1` 通过
  - 噪音 false positive 数量下降
- **为什么排第一**：技术债 D1 已知低风险，单独可做；为后续清理开路

### Task 2：v0.2.2b — T9.4 文档合并 + known-issues 更新

- **目标**：
  - 合并 T9.4 计划 + 4 子报告（final-closure, repair-safety, dogfood, fixup）为索引文档
  - 更新 docs/known-issues.md 的 v0.2 → v0.2.2 标签
  - 补充 T9.4a-b-c 缺失的实现报告（如未合并到最终报告）
- **风险等级**：Risk C（纯文档）
- **是否改代码**：否
- **验收标准**：
  - `docs/design/t9-4-index.md` 创建
  - `docs/known-issues.md` 标签更新
  - 链接全部可点
- **为什么排第二**：技术债 D2, D4, D11 文档问题；为 T10 新功能提供清晰基线文档

### Task 3：T10.1 — Quality Explanation UI MVP

- **目标**：
  - 在 `CandidatePanel` 中显示 quality score 的"为什么会这样"说明
  - 5 维度分别有简短解释（如 `continuity=PASS` → "已使用 3 个连续性锚点"）
  - 纯前端展示，不改后端 API
- **风险等级**：Risk B（前端功能）
- **是否改代码**：是（仅 frontend/src/components/right-panel/CandidatePanel.vue）
- **验收标准**：
  - 每个 quality 维度在 UI 中显示 1-2 句解释
  - E2E 测试覆盖 5 维度展示
  - 现有 23 个 focused E2E 仍通过
- **为什么排第三**：v0.2.2 维护完 → T10.1 是 T10 阶段第一个用户能立即感知的改进

---

## 10. 结论

### 是否建议 v0.2.2？

**建议：条件建议（推荐）** — 先做 v0.2.2 维护版。

### v0.2.2 范围

维护版，包含：
- Guardrails allowlist cleanup
- T9.4 文档合并
- Known issues 标签更新
- Release notes polish
- T9.4a-b-c 文档补充

不包含：
- 新功能
- Pipeline prompt 模板修改
- 大范围 skipped E2E 恢复
- 内存端点冲突检测

### T10 范围

候选稿质量增强 + 长文连续性深化：
1. Quality Explanation UI（P0）
2. Candidate Compare MVP（P0）
3. Story State UI 最小版（P1）
4. Repair UX refinement（P1）
5. Long-form dashboard / Dogfood templates（P2）

### 推荐路线

**v0.2.2a → v0.2.2b → T10.1 → ... → v0.2.2 → T10.x → v0.3.0**

短期 1-2 周完成 v0.2.2 维护，中期 4-6 周做 T10 阶段，长期规划 v0.3 大版本。

---

## 文档归档

本决策文档将作为：
- v0.2.2 维护版规划依据
- T10 阶段计划起点
- 后续 3 个任务的优先级依据

文件路径：`docs/roadmaps/t10-v0-2-2-scope-decision.md`
