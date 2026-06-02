# Lite 连续生成流程故障定位报告

## 1. 背景
Phase T3-B-2 和 T3-B-3 连续生成 3 场补测失败，第 2、3 场未找到选项卡。

## 2. 当前复现结果
- 第 1 场：成功生成真实内容，字符数符合要求
- 第 2、3 场：测试脚本报告“未找到选这个按钮”

## 3. 期望流程
1. 开局卡 → 自动生成第 1 场
2. 第 1 场生成完成后，刷新下一场景爽点卡
3. UI 渲染爽点卡选项
4. 点击爽点卡 → 生成第 2 场
5. 重复直到生成第 3 场

## 4. 实际流程
- 后端：第 1 场生成完成后，调用 `refreshOptions`
- 前端：`refreshOptions` 调用 `/lite/next-options` API
- UI：爽点卡渲染为 class="option-card" 的 button 元素

## 5. 前端代码链路

### 5.1 useLiteGeneration.ts
- 第 368-370 行：第 1 场生成完成后，调用 `refreshOptions`
- `refreshOptions` 调用 `fetchLiteNextOptions` API，将结果存入 `nextCards`

### 5.2 LiteWritingView.vue
- **第 265-271 行：爽点卡渲染为 `<button class="option-card">`
- **第 299 行：按钮内部 `<em>{{ optionActionLabel }}</em> 显示“选这个，自动写...”

## 6. 后端 API 链路
- `/lite/next-options`：返回 option cards 数据
- `/lite/write-next/stream`：写入场景

## 7. 关键发现

**核心问题：测试脚本选择器理解错误！**

- 爽点卡本身是一个大按钮元素，不是爽点卡内部有 `<em>` 标签显示“选这个，自动写...”，而不是单独的按钮文字。

正确的 UI 结构是：
- `<button class="option-card"> <!-- 整个卡片本身就是可点击的按钮 -->
  - 包含各种卡片内容...
  - `<em>选这个，自动写...</em>`
`</button>`

不是：
- 有一个包含“选这个”文字的按钮。

## 8. 根因判断
**D. UI 渲染了，但测试选择器找错**

## 9. 最小修复建议
修改连续生成测试脚本：
- 选择器改为定位 `class="option-card"` 的按钮
- 点击的是整个卡片按钮，而不是查找包含“选这个”的子元素

## 10. 不建议做的事情
- 不要修改后端业务代码
- 不要修改前端业务代码
