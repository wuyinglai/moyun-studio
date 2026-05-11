# Issue tracker: Local Markdown

Issues 和需求文档以 markdown 文件形式存放在 `.scratch/` 目录中。

## 约定规范

- 每个功能一个目录：`.scratch/<功能-slug>/`
- 需求文档位于：`.scratch/<功能-slug>/PRD.md`
- 实现任务位于：`.scratch/<功能-slug>/issues/<序号>-<slug>.md`，序号从 `01` 开始
- 任务状态通过文件顶部的 `Status:` 行记录（见 `triage-labels.md`）
- 对话历史和评论追加到文件底部的 `## Comments` 标题下

## 当技能说"发布到 issue 追踪器"

在 `.scratch/<功能-slug>/` 下创建新文件（需要时创建目录）。

## 当技能说"获取相关票据"

读取指定路径的文件。用户通常会直接传递路径或 issue 编号。
