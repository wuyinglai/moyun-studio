# T7.4 Frontend Smoke Checklist

> T7.3 新增的前端流程保护项，发布前必须逐项 smoke 验证。
>
> 基线：T7.3-Final (commit `bd796cb`)
> 创建日期：2026-06-12

---

## 项目创建与选择

- [ ] 打开新建项目弹窗，确认搜索/搜索框可见
- [ ] 新建项目弹窗：未选题材时，"生成并打开"按钮为 disabled 且显示提示"请先在上方选择题材后即可创建项目"
- [ ] 选题材后，提示消失，按钮可用
- [ ] 新建项目副标题包含"生成内容仅为起点参考"提示
- [ ] 打开项目弹窗：搜索框自动聚焦
- [ ] 输入关键词后列表正确过滤
- [ ] 清空关键词后恢复全部项目
- [ ] 无匹配结果时显示"未找到匹配项目"
- [ ] 项目卡片显示最近修改时间（当 updated_at ≠ created_at 时）
- [ ] 双击项目卡片可正常打开项目

## 写下一场景 → Candidate

- [ ] 点击"写下一场景"按钮
- [ ] 生成结果进入 candidate（不直接覆盖正文）
- [ ] Candidate action badge 显示"续写"（非"重写"）
- [ ] fallback_draft 类型候选稿显示"备用草稿"标签
- [ ] Candidate source_type badge 显示"AI 生成"（蓝色）

## Preview / Adopt / Delete

- [ ] Preview 候选稿：只读展示，不修改正文
- [ ] Adopt 前弹出确认对话框
- [ ] 编辑器有未保存修改时，adopt 确认对话框包含"⚠ 该文件有未保存的修改"警告
- [ ] 取消 adopt 后，编辑器内容保留，candidate 状态不变
- [ ] Adopt 成功后，正文更新，编辑器刷新
- [ ] Delete 候选稿后，正文不受影响

## Continuity Warning

- [ ] 高严重度候选稿显示连续性警告 badge（红色）
- [ ] warning_message 在候选稿卡片上可见
- [ ] Adopt 有连续性警告的候选稿时，确认对话框包含"⚠ 该候选稿存在连续性警告"
- [ ] 无警告的候选稿不误报

## 真实 LLM 状态指示器

- [ ] EditorToolbar 工具栏末尾显示蓝色"真实 LLM" badge
- [ ] Hover badge 显示 tooltip 说明
- [ ] 开发环境下 tooltip 补充说明"模拟运行仅在执行面板测试按钮中可用"
- [ ] badge 文案始终为"真实 LLM"（不显示"开发模式"）

## 错误消息用户友好性

- [ ] 后端未启动时，notification 显示"无法连接后端服务"（非 NetworkError / fetch failed）
- [ ] FILE_CONFLICT 时显示"正文已被其他操作修改"（非 FILE_CONFLICT 错误码）
- [ ] 500 错误时显示"生成服务暂时出错"（非 Internal Server Error）
- [ ] API Key 错误时显示"LLM 配置不可用"（非 401 / unauthorized）
- [ ] 未知错误显示"操作失败，请稍后重试"（非技术堆栈信息）

## 构建与测试基线

- [ ] `frontend npm run build` 通过
- [ ] `backend pytest` 全部通过
- [ ] `git diff --check` 无 whitespace 问题
- [ ] 无 API Key 泄露到 localStorage / 日志 / 截图
