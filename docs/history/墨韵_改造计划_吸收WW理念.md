# 墨韵 × Webnovel Writer 理念融合改造计划

> 目标：吸收 Webnovel Writer 的核心优势，改造墨韵，保留墨韵独立 Web UI 的产品优势
> 制定时间：2026-05-12

---

## 改造原则

1. **保留墨韵底色**：独立 Web 应用、三栏 UI、Prompt 管理中台、"导演+演员"模式
2. **吸收 WW 精华**：合同机制、多 Agent 协作链、结构化审查、创意约束包
3. **不推翻重来**：在现有架构上增量改造，每个改进可独立验证

---

## 第一阶段：基础设施（1-2 周）

### 1.1 合同机制（Contract）—— 防幻觉核心

**WW 借鉴点**：`MASTER_SETTING.json` + `volume_{N}.json` + `chapter_{N}.review.json` 三层合同，写作前强制加载，违反即不通过。

**墨韵改造方案**：

在 `workspace/projects/{name}/` 下新增文件：

```
contract.json          # 全局合同（替代部分 story-state.md 功能）
chapters/vol-xx/ch-xxx/contract.json  # 章级合同（新增）
```

`contract.json` 结构：
```json
{
  "project_id": "",
  "version": "1.0",
  "rules": {
    "hard_constraints": ["主角不能突然获得未铺垫的能力", "..."],
    "forbidden_zones": ["某角色已死不能复活", "..."],
    "must_cover_nodes": ["某伏笔必须在本卷回收", "..."]
  },
  "chapter_directive": {
    "goal": "",
    "time_anchor": "",
    "chapter_span": "",
    "countdown": "",
    "chapter_end_open_question": ""
  },
  "anti_patterns": ["避免AI味表达：'突然明白了'", "..."]
}
```

**后端改动**：
- 新增 `backend/services/contract_service.py`：加载/更新/验证合同
- 写作前强制调用合同验证，违反则返回错误，不执行生成

**前端改动**：
- 设置面板新增"故事规则" Tab，可编辑 `hard_constraints` 和 `forbidden_zones`
- 右侧 Prompt 面板显示当前生效的合同内容（透明化）

---

### 1.2 充分性闸门（Hard Gate）—— 防跳步核心

**WW 借鉴点**：初始化分 Step 1-7，每步有"充分性闸门"，未满足前禁止进入下一步。

**墨韵改造方案**：

改造现有的三阶段引导流程（`前端的主要功能`），增加闸门检查：

```
阶段1（书名创意）闸门：
  ✅ 书名已确认（用户点击确认）
  ✅ 一句话故事已填写

阶段2（大纲生成）闸门：
  ✅ 卷纲已生成且用户确认
  ✅ 章节结构已计算（总字数 / 1800 = 总节数）
  ✅ 创意约束包已生成（见 2.2）

阶段3（开始写作）闸门：
  ✅ contract.json 已初始化
  ✅ 至少一个角色档案已创建
```

前端用 `Promise` + 闸门检查函数实现，未通过则按钮置灰并显示提示。

---

## 第二阶段：写作质量提升（2-3 周）

### 2.1 多 Agent 协作链 —— 替代当前"单 Prompt → LLM"

**WW 借鉴点**：
```
context-agent → 写章 → reviewer → 润色 → data-agent → CHAPTER_COMMIT
```

**墨韵改造方案**：

保留"导演+演员"模式，但把"演员"（LLM 调用）拆成多步：

后端新增 Agent 链（`backend/agents/`）：

```
context_agent.py    # 生成写作任务书（读取 contract.json + story-state.md + recent-context.md）
draft_agent.py      # 按任务书起草正文
review_agent.py     # 结构化审查（输出 JSON，含 evidence）
polish_agent.py    # 润色（风格适配 + 排版 + Anti-AI 检查）
commit_agent.py     # 提交（更新 contract + story-state + recent-context）
```

前端右侧面板新增"Agent 执行链"可视化：
```
[context-agent] ✅ 任务书已生成
[draft_agent]    ✅ 正文已起草（2345字）
[review_agent]   ✅ 审查通过（0 blocking issues）
[polish_agent]   ✅ 润色完成
[commit_agent]   ✅ 已提交，story-state 已更新
```

---

### 2.2 创意约束包 —— 反套路 + 差异化

**WW 借鉴点**：Step 6 生成 2-3 套创意包，每套含：一句话卖点、反套路规则 1 条、硬约束 2-3 条、主角缺陷驱动、反派镜像、开篇钩子。

**墨韵改造方案**：

新建项目时，阶段 2（大纲生成前）新增"创意约束包"生成步骤：

后端新增 `backend/services/creativity_service.py`：
- 输入：题材、一句话故事、核心冲突
- 输出：2-3 个创意约束包（JSON 格式）
- 用户选择后写入 `contract.json` 的 `rules` 字段

前端新增"创意约束包"选择界面（模态框，在阶段 2 和阶段 3 之间）：

```
┌─────────────────────────────────┐
│  选择你的创意约束包            │
├─────────────────────────────────┤
│  ○ 方案A                     │
│    卖点：...                  │
│    反套路：...                │
│    硬约束：...                │
│                             │
│  ● 方案B（推荐）             │
│    卖点：...                  │
│    反套路：...                │
│    硬约束：...                │
│                             │
│  ○ 方案C                     │
│    卖点：...                  │
│    反套路：...                │
│    硬约束：...                │
├─────────────────────────────────┤
│        [确认选择]            │
└─────────────────────────────────┘
```

---

### 2.3 Anti-AI 强制检查

**WW 借鉴点**：Step 4 润色最后一步 `anti_ai_force_check`，fail 则不进 Step 5（提交）。

**墨韵改造方案**：

在 `polish_agent.py` 中加入 Anti-AI 检查步骤：

检查项（可配置）：
```
1. 是否出现 AI 高频套话（"突然明白了"、"心中一震"、"不禁感叹"...）
2. 是否句式过于整齐（排比句过多）
3. 是否缺少感官细节（视觉/听觉/触觉/嗅觉）
4. 对话是否自然（是否像真人说话）
```

检查 fail → 自动触发重写（最多 2 次）→ 仍 fail 则提示用户手动修改。

---

## 第三阶段：RAG 检索增强（3-4 周）

### 3.1 轻量级 RAG 系统

**WW 借鉴点**：嵌入模型 + 重排序模型，精准召回相关上下文。

**墨韵改造方案**（考虑到墨韵定位，做轻量级，不强制依赖外部 API）：

方案 A——**纯本地方案**（推荐，无额外成本）：
- 使用 `rank_bm25`（已验证可用）做关键词检索
- 对 `chapters/` 所有已写章节建立 BM25 索引
- 写作前检索 top-5 相关段落，注入 Prompt

方案 B——**嵌入模型方案**（高质量，需配置）：
- 使用 LiteLLM 的嵌入接口（支持多模型）
- 用户配置嵌入模型 API Key（可选）
- 无配置时 fallback 到方案 A

后端新增 `backend/services/rag_service.py`：
```python
class RAGService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.bm25_index = self._build_bm25_index()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """检索与 query 最相关的 top_k 个段落"""
        ...
```

---

## 第四阶段：结构化审查与指标落库（1-2 周）

### 4.1 审查 Agent + 结构化 JSON

**WW 借鉴点**：reviewer Agent 输出严格 JSON，每个 issue 必须有 `evidence`；`blocking=true` 必须修复。

**墨韵改造方案**：

后端新增 `backend/agents/review_agent.py`：
- 输入：章节文件内容 + contract.json + story-state.md
- 输出：结构化 JSON
```json
{
  "chapter": 42,
  "overall_score": 0.85,
  "issues": [
    {
      "type": "continuity",
      "severity": "blocking",
      "description": "主角在上一章受伤，本章未提及伤势",
      "evidence": "第41章末尾：'肋骨断裂三根'；第42章：主角正常奔跑",
      "suggestion": "在章节开头加入伤势描写"
    }
  ],
  "blocking_count": 1,
  "passed": false
}
```

前端新增"审查"按钮和审查报告面板：
```
┌─────────────────────────────────┐
│  第42章审查报告              │
├─────────────────────────────────┤
│  总分：0.85 / 1.0            │
│  状态：❌ 未通过               │
│                             │
│  🔴 Blocking Issues (1)      │
│  - 主角伤势未提及            │
│    证据：...                  │
│                             │
│  🟡 Warnings (2)            │
│  - AI 味表达 detected        │
│  - 伏笔未回收                │
├─────────────────────────────────┤
│  [自动修复]  [稍后处理]     │
└─────────────────────────────────┘
```

---

### 4.2 审查指标落库

**WW 借鉴点**：`review-pipeline` 生成 `review_metrics.json` 并写入 `index.db`，作为后续写作的避雷模式。

**墨韵改造方案**：

后端新增 `review_metrics.json` 存储（可放在项目根目录或 `chapters/` 下）：
```json
{
  "chapter": 42,
  "review_time": "2026-05-12T08:00:00",
  "scores": {"continuity": 0.8, "character_consistency": 0.9, ...},
  "blocking_issues": [...],
  "anti_patterns_hit": ["avoided_ai_phrase_1", ...],
  "lessons_for_future": ["下次写作时注意伤势连续性", ...]
}
```

`contract.json` 的 `anti_patterns` 字段会根据审查结果自动更新（累加新发现的 AI 味表达）。

---

## 改造优先级总表

| 阶段 | 改造项 | 工期 | 价值 |
|------|--------|------|------|
| **第一阶段** | 合同机制（Contract） | 1 周 | ⭐⭐⭐⭐⭐ 防幻觉核心 |
| 第一阶段 | 充分性闸门 | 3 天 | ⭐⭐⭐⭐ 防跳步 |
| **第二阶段** | 多 Agent 协作链 | 2 周 | ⭐⭐⭐⭐⭐ 质量提升核心 |
| 第二阶段 | 创意约束包 | 1 周 | ⭐⭐⭐⭐ 差异化核心 |
| 第二阶段 | Anti-AI 强制检查 | 3 天 | ⭐⭐⭐⭐ 去 AI 味 |
| **第三阶段** | 轻量级 RAG | 3 周 | ⭐⭐⭐ 上下文精度 |
| **第四阶段** | 结构化审查 + 指标落库 | 1-2 周 | ⭐⭐⭐⭐ 质量保障 |

---

## 第一步建议

**从"合同机制（Contract）"开始**。理由：

1. 它是 WW 防幻觉的核心设计，价值最高
2. 改造量可控（新增 1 个后端服务 + 1 个前端 Tab）
3. 不依赖其他改造项，可独立验证
4. 与墨韵现有 `story-state.md` 可以平滑融合

---

## 附录：文件变动清单（合同机制）

### 新增文件
```
backend/services/contract_service.py   # 合同加载/验证/更新
backend/api/contract.py              # /api/contract GET/POST
frontend/src/components/ContractTab.js # 合同编辑 Tab（右侧面板）
```

### 修改文件
```
backend/api/generate.py   # 写作前调用 contract_service 验证
frontend/src/App.js      # 右侧面板新增 Contract Tab
docs/API契约.md          # 新增 /api/contract 端点文档
```

### 新增用户文件
```
workspace/projects/{name}/contract.json  # 项目合同文件
```
