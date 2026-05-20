# 墨韵文档

## 📖 完整文档已迁移至 GitHub Wiki

完整的用户文档、教程和 API 参考现已托管在 GitHub Wiki 上：

👉 **[https://github.com/wuyinglai/moyun-studio/wiki](https://github.com/wuyinglai/moyun-studio/wiki)**

## Wiki 内容概览

### 快速开始
- **[Home](https://github.com/wuyinglai/moyun-studio/wiki/Home)** - 项目介绍和核心概念
- **[Getting Started](https://github.com/wuyinglai/moyun-studio/wiki/Getting-Started)** - 快速上手指南
- **[Installation](https://github.com/wuyinglai/moyun-studio/wiki/Installation)** - 详细安装说明
- **[Configuration](https://github.com/wuyinglai/moyun-studio/wiki/Configuration)** - 配置 AI 模型

### 核心功能
- **[Project Structure](https://github.com/wuyinglai/moyun-studio/wiki/Project-Structure)** - 项目文件结构说明
- **[Scene-Level Writing](https://github.com/wuyinglai/moyun-studio/wiki/Scene-Level-Writing)** - 场景级写作详解
- **[Story Memory](https://github.com/wuyinglai/moyun-studio/wiki/Story-Memory)** - 故事记忆系统
- **[Safe Revisions](https://github.com/wuyinglai/moyun-studio/wiki/Safe-Revisions)** - 安全候选稿机制

### AI 工作流
- **[Prompt System](https://github.com/wuyinglai/moyun-studio/wiki/Prompt-System)** - Prompt 模板系统
- **[Pipeline System](https://github.com/wuyinglai/moyun-studio/wiki/Pipeline-System)** - 管线工作流
- **[SSE Events](https://github.com/wuyinglai/moyun-studio/wiki/SSE-Events)** - 实时事件系统

### 开发者资源
- **[API Reference](https://github.com/wuyinglai/moyun-studio/wiki/API-Reference)** - API 接口文档
- **[Developer Guide](https://github.com/wuyinglai/moyun-studio/wiki/Developer-Guide)** - 开发者指南
- **[Roadmap](https://github.com/wuyinglai/moyun-studio/wiki/Roadmap)** - 开发路线图
- **[FAQ](https://github.com/wuyinglai/moyun-studio/wiki/FAQ)** - 常见问题解答

## 本仓库文档说明

本目录 (`docs/`) 保留了原始的开发文档、架构设计文档和历史参考资料，主要供开发者参考。普通用户请优先查看 GitHub Wiki。

### 开发文档（供开发者参考）

- **[技术选型速查](./技术选型速查.md)** - 技术栈和开发规范
- **[编码规范](./编码规范.md)** - 代码风格和最佳实践
- **[文件系统设计](./文件系统设计.md)** - 底层文件结构设计
- **[后端架构设计](./后端架构设计.md)** - 后端系统架构
- **[功能清单](./功能清单.md)** - 完整功能列表
- **[API契约](./API契约.md)** - API 接口规范（历史版本）
- **[Prompt模板说明](./Prompt模板说明.md)** - Prompt 模板开发指南

## 重要更新

### 场景级写作
墨韵现已采用场景级写作模式：
- 每个 `sec-*.md` 文件 = 一个完整场景（约 800 字）
- 每章默认 5 个场景
- 移除了旧的「节内容文件」「最近 5 章摘要」等表述
- 更新了相关的 Prompt 模板和文档

### 配置参数新增
```
scene_target_chars = 800          # 单场景目标字数
scenes_per_chapter = 5            # 每章场景数
chapters_per_volume = 12          # 每卷章节数
recent_context_scene_limit = 15   # 近期上下文场景数
batch_generate_max_count = 10     # 批量生成最大数
max_file_write_size = 5MB         # 最大文件写入大小
allow_lan_access = false          # 允许局域网访问
```

## 联系与反馈

- 💬 **问题反馈**：在 [GitHub Issues](https://github.com/wuyinglai/moyun-studio/issues) 提交
- 📝 **文档建议**：在 Wiki 页面留言或提交 PR
- 🤝 **贡献代码**：查看 [Developer Guide](https://github.com/wuyinglai/moyun-studio/wiki/Developer-Guide)
