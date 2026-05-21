# 示例项目：黑塔信号

近未来悬疑小说示例项目，展示墨韵的标准项目结构和场景级写作模型。

## 项目结构

```
demo-novel/
├─ meta.json              # 项目元信息
├─ style-guide.md         # 文风指南
├─ story-state.md         # 故事全局状态（长期记忆）
├─ recent-context.md      # 近期上下文（短期场景记忆）
├─ outline.md             # 大纲
├─ characters/            # 角色档案
│  ├─ lin-che.json
│  └─ shen-zhixia.json
└─ chapters/              # 章节与场景
   └─ vol-01/
      └─ ch-001/
         ├─ ch-meta.json  # 章节元数据（含场景卡片）
         ├─ sec-001.md    # 场景 1
         └─ sec-002.md    # 场景 2
```

## 关键概念

- **场景（sec）是写作和生成的最小单位**，不是传统章节。每个场景文件约 600-1000 中文字。
- **每章默认 5 个场景**，由 `ch-meta.json` 中的场景卡片规划。
- **story-state.md** 保存长期全局状态（世界观、主线冲突、人物关系），不是逐场景复述。
- **recent-context.md** 保存近期场景的结构化记忆（时间、地点、人物、事件、线索、未解问题）。
- **高风险修改**（润色、改写、对话编辑）默认生成候选稿，不直接覆盖正文。

## 使用方式

将此目录复制到 `workspace/projects/` 下即可在墨韵中打开：

```bash
cp -r examples/demo-novel workspace/projects/demo-novel
```
