# Prompt 体系重构 + 管线引擎设计

> 版本：v1（2026-05-14）
> 状态：设计定稿，待实现

## 核心变更

1. 从单次 Prompt 调用升级为管线（Pipeline）驱动的多步骤生成
2. 每条管线由 YAML 定义步骤顺序，每步独立 Prompt 模板
3. 中间步骤静默执行（不输出到前端），最终结果流式输出
4. 失败时按 fallback 链降级，而非直接报错

## 管线定义

YAML 格式：
```yaml
name: polish
label: 润色
steps:
  - id: depai
    label: 去AI味
    prompt: pipeline/polish/depai
    fallback: null
  - id: prose
    label: 提升文笔
    prompt: pipeline/polish/prose
    fallback: depai
```

## API

- POST /api/pipeline/run — SSE 流式执行
- GET /api/pipeline/list — 列出所有管线
- GET /api/pipeline/{name} — 管线详情含步骤 Prompt
- PUT /api/pipeline/{name} — 保存步骤 Prompt
- POST /api/pipeline/custom — 创建自定义管线

## 前端变更

- 工具栏从 11 个按钮精简为 5 个管线按钮
- 右侧面板新增「快捷」Tab（管线选择 + Prompt 编辑 + 运行）
- 右侧面板新增「管线编辑」Tab（步骤管理 + Prompt 编辑器）
- 删除旧的 context Tab
