# 墨韵文档

> 导航页 — 完整文档索引见 [document-index.md](document-index.md)

## 快速导航

| 类别 | 入口 |
|------|------|
| **AI 必读** | [document-index.md → AI Must Read](document-index.md#ai-must-read) |
| **契约文档** | [contracts/](contracts/) |
| **开发者文档** | [document-index.md → Developer Docs](document-index.md#developer-docs) |
| **发布说明** | [releases/](releases/) |
| **归档文档** | [archive/](archive/) |

## 契约文档

| 契约 | 说明 |
|------|------|
| [contracts/scene-path-contract.md](contracts/scene-path-contract.md) | 场景路径规则（sec = 单场景，标准路径，默认配置） |
| [contracts/api-contract.md](contracts/api-contract.md) | 文件 API（读写、冲突检测、安全规则） |
| [contracts/event-contract.md](contracts/event-contract.md) | SSE 事件格式（file.updated 不携带 content，heartbeat 不触发业务刷新） |
| [contracts/candidate-contract.md](contracts/candidate-contract.md) | 候选稿契约（高风险动作默认 candidate，adopt 安全检查） |

## 用户文档

用户文档已迁移至 GitHub Wiki：

https://github.com/wuyinglai/moyun-studio/wiki

## 归档文档

过时或被替代的文档已移至 [archive/](archive/)。不要依赖归档文档，除非明确要求。

## 关键配置参数

```
scene_target_chars = 800          # 单场景目标字数
scenes_per_chapter = 5            # 每章节场景数
chapters_per_volume = 12          # 每卷章节数
recent_context_scene_limit = 15   # 近期上下文场景数（约覆盖3章范围）
batch_generate_max_count = 10     # 批量生成最大场景数量
max_file_write_size = 5MB         # 最大文件写入大小
unit_label = "scene"              # 单位标签
max_candidate_size = 3            # 最大候选稿数量
```
