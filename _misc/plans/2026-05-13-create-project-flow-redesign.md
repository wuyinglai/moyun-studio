# 新建项目流程改造 Implementation Plan

**Goal:** 将新建项目的多步骤弹窗改为「弹窗选参数 → 直接创建项目 + 跳转编辑器 + 流式写入文件」的单步流程

**Architecture:**
- CreateProjectModal 从5步向导精简为单页参数表单
- 点击「生成并打开」后创建 project → 关闭弹窗 → router.push 到编辑器
- 新建 `useFileGeneration` composable 处理编辑器内的流式生成
- 右侧面板通过 SSE 订阅生成事件，显示当前 prompt 和进度

## 任务分解

1. 精简 useProjectWizard.ts — 去掉多步骤状态，只保留 params 表单
2. 重写 CreateProjectModal.vue — 单页表单 +「生成并打开」按钮
3. projectStore 添加 pendingGeneration 状态
4. 创建 useFileGeneration composable（fetch streaming → editorStore.appendContent）
5. App.vue 监听 pendingGeneration 自动触发流式生成
6. 右侧面板显示生成状态和当前 prompt
