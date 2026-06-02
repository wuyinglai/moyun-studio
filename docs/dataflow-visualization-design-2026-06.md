# Moyun Studio 数据流可视化设计

## 1. 当前问题

### 问题总结：
- 用户不知道 AI 读了哪些文件？
  - 当前执行时，用户只能看到结果，看不到数据来源模糊。

- 不知道 prompt 怎么来？
  - 现有代码：
  - 不知道当前场景、故事引擎、近期上下文、写作偏好如何组合。

- 不知道候选稿写到哪里？
  - CandidatePanel 能看到候选稿，但候选稿的保存路径、base_mtime、base_hash 都不透明。

- 不知道 story memory 如何更新？
  - 写完一场景后，story engine、recent context、ch meta 都变了，但用户看不到变化的过程。

- 不知道 stream 生成中当前在哪一步？
  - 只有 workPhase/workDetail 是文字描述，没有可视化节点化。

- 不知道失败发生在哪一步？
  - 失败时，只有错误信息不清晰，不知道在哪一步卡住。

---

## 2. ComfyUI 可借鉴点

### 可借鉴的优点：
- **输入清楚：
  - 节点明确标注来源，比如 ComfyUI 每个节点输入都能看。

- **节点清楚：
  - 每个步骤单独节点显示正在做什么，比如"Load Image" / "KSampler" 都很清晰。

- **输出清楚：
  - 每个节点输出有箭头指向下个节点。

- **状态清楚：
  - 正在跑的节点高亮，失败的节点红色标红。

- **失败位置清楚：
  - 红色节点上显示错误，方便定位。

- **可重复运行：
  - 同样输入不变。

- **中间结果可查看：
  - 点一下节点可以看到节点输出。

### 明确不照搬：
- **普通作者不适合直接拖节点：
  - 目标用户是小说作者，不是程序员。
  - 第一阶段只读视图，先做可视化，别着急做可编辑工作流。
  - 第二阶段再考虑拖线编辑。

---

## 3. 目标用户分层

### 三层视图方案：
- **普通作者视图（默认）**：
  - 简单的时间线，只用文字和图标，不用箭头，不暴露内部服务，没有复杂节点，只显示：
  - "正在读取前文..."
  - "正在准备提示..."
  - "正在调用模型..."
  - "正在写正文..."
  - "正在质量检查..."
  - "正在保存..."
  - "正在更新记忆..."

- **高级作者视图**：
  - 可以展开每个节点：
  - 每个阶段都标注出的节点，但仍然不暴露服务名，换成可读文字节点化，把：
  - LiteSceneService → "确定下一场景"
  - LiteStoryMetadataService → "加载故事记忆"
  - LitePromptBuilder → "组装提示"
  - LiteLLMService → "AI 思考与模型"
  - LiteQualityService → "质量检查"
  - CandidateService → "保存候选稿"
  - FileService → "保存正文"

- **开发者/模板作者视图**：
  - 显示真实服务名，显示参数，显示 API 端点，
  - 显示提示的完整提示，
  - 显示模型参数，
  - 显示 JSON 化输出。

---

## 4. 右边栏入口设计

### 新 Tab 布局：
- 写作
- 修改
- 记忆
- 视觉
- **流程**（新增）
- 高级

### "流程" Tab 内容：
- **顶部：** 当前任务状态
  - 当前执行时间线：正在进行或上次执行。

- **中间：** 节点可视化
  - 只读节点图从上到下，从左到右。
  - 从输入 → 处理 → 输出。

- **节点：**
  - 圆角边框图标。
  - 可展开查看详情。
  - 失败时显示。

- **右下角：**
  - 查看完整日志
  - 重试（仅在失败时有。

---

## 5. 五条核心数据流

### 5.1 写下一场景（写场景）

#### 完整数据流向图：

```
┌─────────────────────────┐
│  输入：当前文件     │
│ (1.  场景：        │
│    ────────────────────
│ 2.  记忆 (LitePromptBuilder 
│    ────────────────────
│ 3.  调用LLM (LiteLLMService 
│    ────────────────────
│ 4.  质量检查质量
│    ────────────────────
│ 5.  或保存 (CandidateService 
│    ────────────────────
│ 6.  记忆更新 (LiteStoryMetadataService 
│    ────────────────────
│ 7.  (UI 刷新)
└─────────────────────────┘
```

#### 节点定义：
  - 节点 ①：当前场景（输入）
    - 来源：user 选的，
    - 输入：next_file，source_file，
  - 节点 ②：记忆
    - 来源：LiteStoryMetadataService，
    - 输出：story engine，recent context，ch meta，
  - 节点 ③：提示
    - 来源：LitePromptBuilder，
    - 输出：messages 输入：
  - 节点 ④：模型调用
    - 来源：LiteLLMService，
    - 输出：，
  - 节点 ⑤：质量检查
    - 来源：LiteQualityService，
    - 输出：质量评分，修复 prompt，
  - 节点 ⑥：保存
    - 来源：CandidateService 或 文件保存，
  - 节点 ⑦：更新记忆
    - 来源：LiteStoryMetadataService，

---

### 5.2 候选稿改稿（候选改稿）

#### 完整数据流向图：

```
┌─────────────────────────┐
│输入：当前内容    │
│(action 判断    │
│  ──────────────────
│2. 提示 LitePromptBuilder 
│  ────────────────────
│3. 调用 LiteLLMService 
│  ────────────────────
│4. 创建 CandidateCandidateService 
│  ────────────────────
│5. 展示 CandidatePanel 
│  ────────────────────
│6. 用户采用 Candidate
│  ────────────────────
│7. 原文更新、revision log 写
└─────────────────────────┘
```

---

### 5.3 故事记忆更新（记忆更新）

#### 数据流向图：

```
┌─────────────────────────┐
│1. 场景写入 新内容       │
│  ──────────────────────
│2. 提取摘要          │
│  ──────────────────────
│3. 更新 ch-meta      │
│  ──────────────────────
│4. 更新 story-engine   │
│  ──────────────────────
│5. 供下场景  用     │
└─────────────────────────┘
```

---

### 5.4 质量审查/修复（质量）

#### 数据流向图：

```
┌─────────────────────────┐
│1. 输入：生成好的内容    │
│  ──────────────────────
│2. 审稿：质量检查 LiteQualityService 
│  ──────────────────────
│3. 判断：是否需要修复？  │
│  ──────────────────────
│4. →修复：prompt 修复  │
│  ──────────────────────
│5. 替换内容或保留原内容│
│  ──────────────────────
│6. 继续后步骤继续后续
└─────────────────────────┘
```

---

### 5.5 未来视觉配图（配图）

#### 数据流向图：

```
┌─────────────────────────┐
│1. 当前场景 场景内容       │
│  ──────────────────────
│2. 视觉摘要：场景        │
│  ──────────────────────
│3. 角色视觉卡角色卡        │
│  ──────────────────────
│4. 视觉提示：视觉 prompt    │
│  ──────────────────────
│5. ComfyUI 工作流调用      │
│  ──────────────────────
│6. 图片候选：候选       │
│  ──────────────────────
│7. 设置为本场插图    │
└─────────────────────────┘
```

---

## 6. 节点模型设计

### 6.1 FlowNode

```typescript
type FlowNodeStatus = 'pending' | 'running' | 'success' | 'error' | 'skipped'

type FlowNode = {
  id: string
  label: string
  type: 'input' | 'process' | 'llm' | 'file' | 'candidate' | 'memory' | 'ui' | 'image'
  status: FlowNodeStatus
  inputs?: FlowArtifact[]
  outputs?: FlowArtifact[]
  durationMs?: number
  error?: string
  startTime?: number
  endTime?: number
}
```

### 6.2 FlowArtifact

```typescript
type FlowArtifactType = 'file' | 'text' | 'prompt' | 'candidate' | 'image' | 'json'

type FlowArtifact = {
  id: string
  label: string
  type: FlowArtifactType
  path?: string
  preview?: string
  size?: number
  content?: string
  truncated?: boolean
}
```

---

## 7. 用户友好版与开发者版

### 普通作者版（默认）

显示：
- 正在读取前文
- 正在整理故事记忆
- 正在写正文
- 正在检查质量
- 正在保存候选稿
- 已完成

### 开发者/高级作者版

显示：
- project_id
- source_path
- target_path
- prompt 预览
- model
- candidate_id
- SSE event 事件
- 执行时间
- 简化 error stack

---

## 8. MVP 实现建议

第一阶段不要做拖线节点编辑器！

### MVP 应该是：
- **1. ExecutionPanel → FlowPanel 升级：
  - 在 ExecutionPanel 加个视图模式，
  - 可以在执行（原视图和流程视图。

- **2. 只读时间线：**
  - 时间线从上到下，
  - 每个节点有图标、文字，
  - 成功、失败。

- **3. 每个节点可展开：**
  - 展开后看到输入输出。

- **4. 支持 sync / stream 两种流程：**
  - stream 可以显示实时更新。

- **5. 失败时定位节点：**
  - 错误标红、错误信息。

- **6. 完成保留最近一次 flow：**
  - 可以回顾上次写。

---

## 9. 与现有后端关系

### 现有服务节点化：
- LiteSceneService → 节点名："路径服务
- LiteStoryMetadataService → "记忆服务
- LitePromptBuilder → "提示组装"
- LiteLLMService → "模型调用
- LiteQualityService → "质量检查
- LiteOptionCardsService → "选项卡生成
- CandidateService → "候选稿服务"

---

## 10. 与 SSE 的关系

### 现在 SSE 分析：
  - 现用 SSE：
  - meta
  - status
  - delta
  - replace
  - done
  - error

### 是否要新增 SSE event？
  - 建议：暂不新增！
  - 理由：先前端根据现有 event 映射到节点，
  - 避免改后端要改很多。

### 现有前端可以先模拟节点：
  - onMeta → 可以设置节点 1-2 ，
  - onStatus → 对应质量节点 3，
  - onDelta → 节点 4，
  - onDone → 节点 5-6，
  - onError → 标红错误节点。

---

## 11. 与 CandidatePanel 的关系

### 候选稿创建后：
- Candidate 创建之后作为节点输出，
- 候选稿展示来源 flow。

### adopt 后：
- adopt 回写状态。

---

## 12. 与未来视觉分镜的关系

### 视觉也走 flow：
- 视觉分镜作为节点在流程里。
- text2image → 节点，
- image2image → 节点，
- inpaint → 节点，
- 图片候选和正文候选机制一致。

---

## 13. 推荐开发路线

### P0：
- **1. 只读 FlowPanel 界面设计
  - 不要拖节点编辑器！

- **2. sync write-next 静态模拟流程
  - 先写死节点静态 mock，
  - 不用后端 SSE 先不改先写。

- **3. stream write-next 状态映射
  - 现有 onMeta/onStatus/onDelta/onDone/onError → 对应到节点。

- **4. candidate 节点展示
  - CandidatePanel 关联。

### P1：
- **1. flow.step SSE event (可选后端)
- **2. prompt preview
- **3. artifact preview
- **4. error 定位

### P2：
- **1. 可编辑 workflow
- **2. 节点模板
- **3. ComfyUI 风格节点编辑器
- **4. 视觉配图节点

---

## 14. 不建议马上做的

### 禁项清单：
- ✗ 不要马上做拖线节点编辑器。
- ✗ 不要马上改后端 SSE。
- ✗ 不要马上接 ComfyUI。
- ✗ 不要马上重写整个 Pipeline。
- ✗ 不要马上把 Lite 模式和专业模式合并。

---

## 15. 最小下一步任务

### Phase 5B：FlowPanel 静态 UI 原型

目标：
- 只做 FlowPanel 静态 UI 原型，
- 不用接真实后端，
- 只用 mock 数据，
- 展示“写下一场景”的流程，
- 展示节点，
- 展示成功/失败，
- 展示展开查看。

验收标准：
- FlowPanel 在右边栏“流程” Tab，
- 显示写入流程，
- 点击某个流程，
- 可以展开看某个节点，
- 显示成功失败状态，
- 不要求真实后端。

---
