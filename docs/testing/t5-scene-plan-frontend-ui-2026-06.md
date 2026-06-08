# T5.4：Scene Plan 前端 UI 最小集成测试报告

**执行日期**: 2026-06-08
**执行人**: Solo Agent
**当前进度**: 约 77%

---

## 1. UI 入口位置

**新增入口**: 右侧面板 → "场景计划" (scene-plan) 标签页

**入口路径**: `frontend/src/components/scene-plan/ScenePlanPanel.vue`

**集成位置**: `frontend/src/components/right-panel/RightPanel.vue`

---

## 2. 用户操作流程

### 2.1 最小操作流程

1. 用户打开项目
2. 打开场景文件 `chapters/vol-01/ch-001/sec-001.md`
3. 在右侧面板切换到 "场景计划" 标签页
4. **加载已保存**: 点击"加载"按钮加载已保存的 Scene Plan
5. **生成**: 点击"生成"按钮，调用 `POST /api/scene-plan/generate`
6. **保存**: 生成成功后，点击"保存"按钮，调用 `POST /api/scene-plan/save`

### 2.2 非场景文件提示

当打开的不是场景文件（如 `style-guide.md`、`story-state.md` 等），面板显示：
> "当前文件不是场景文件，Scene Plan 仅支持 sec-*.md 场景文件"

---

## 3. 调用的 API

### 3.1 生成 Scene Plan
- **端点**: `POST /api/scene-plan/generate`
- **参数**:
  ```json
  {
    "project_id": "demo-novel",
    "target_file": "chapters/vol-01/ch-001/sec-001.md",
    "dry_run": true,
    "include_raw_output": false
  }
  ```

### 3.2 保存 Scene Plan
- **端点**: `POST /api/scene-plan/save`
- **参数**:
  ```json
  {
    "project_id": "demo-novel",
    "target_file": "chapters/vol-01/ch-001/sec-001.md",
    "scene_plan": { ... },
    "overwrite": false
  }
  ```

### 3.3 加载 Scene Plan
- **端点**: `GET /api/scene-plan/load?project_id=...&target_file=...`
- **返回**:
  ```json
  {
    "exists": true,
    "path": "materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json",
    "scene_plan": { ... },
    "mtime": 1234567890
  }
  ```

---

## 4. 生成结果展示

### 4.1 校验状态
- 显示 `valid` / `invalid` 状态徽章
- 显示 `errors` 列表（红色）
- 显示 `warnings` 列表（黄色）

### 4.2 JSON 预览
- 格式化显示 `scene_plan` JSON 内容
- 最大高度 300px，可滚动

---

## 5. 保存与加载行为

### 5.1 保存规则
- `overwrite=false`（默认）
- 如果文件已存在，返回 `conflict=true`，提示用户确认覆盖
- 用户点击"覆盖"按钮后，`overwrite=true` 强制覆盖

### 5.2 加载规则
- 加载时显示加载中状态
- 加载成功回显已保存的 Scene Plan
- 文件不存在时显示"暂无保存的 Scene Plan"

---

## 6. overwrite=false 冲突处理

当用户尝试保存已存在的 Scene Plan 时：
1. 显示警告消息：`"文件已存在，是否覆盖？"`
2. 显示两个按钮："覆盖" / "取消"
3. 用户点击"覆盖"后重新调用 save API，`overwrite=true`
4. 用户点击"取消"后关闭提示，保留原状态

---

## 7. 无副作用验证

✅ **保证不执行**:
- ❌ 不修改 target_file 正文
- ❌ 不创建 candidate
- ❌ 不执行 adopt
- ❌ 不触发 `/api/generate`
- ❌ 不触发 `/api/candidates/*`

✅ **只调用**:
- `POST /api/scene-plan/generate`
- `POST /api/scene-plan/save`
- `GET /api/scene-plan/load`

---

## 8. 测试结果

### 8.1 前端构建
```
✓ built in 3.40s
```

### 8.2 后端回归测试 (44 tests)
```
44 passed
```

### 8.3 Professional Regression Smoke
```
7/7 项通过
✅ T4.7.5 验收通过！
```

---

## 9. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/shared/api/routes.ts` | 修改 | 新增 Scene Plan API 路由 |
| `frontend/src/composables/useScenePlan.ts` | 新增 | Scene Plan API 封装 |
| `frontend/src/components/scene-plan/ScenePlanPanel.vue` | 新增 | Scene Plan 面板组件 |
| `frontend/src/components/right-panel/RightPanel.vue` | 修改 | 集成 ScenePlanPanel |

---

## 10. 剩余问题

1. ❌ **未实现 Scene Plan 编辑器** - 只显示 JSON 预览，无法可视化编辑
2. ❌ **未实现自动加载** - 打开场景文件时不会自动加载已保存的 Scene Plan
3. ❌ **未实现多版本管理** - 每次保存直接覆盖
4. ❌ **未强制接入 Professional dry-run** - Scene Plan 不会自动应用到生成流程

---

## 11. 下一步建议

### T5.4.1 (推荐)
**标题**: Scene Plan 面板自动加载优化

**目标**:
1. 打开场景文件时自动检查是否有已保存的 Scene Plan
2. 如果有，自动加载并显示

**预计工作量**: 小

### T5.4.2
**标题**: Scene Plan 面板编辑器化

**目标**:
1. 将 JSON 预览改为可视化编辑器
2. 支持手动编辑 scene_plan 字段
3. 支持拖拽排序 required_beats

**预计工作量**: 大

---

## 12. 路线图更新

| 阶段 | 状态 | 说明 |
|------|------|------|
| T4.7.x | ✅ 完成 | Candidate 链路收口 |
| T4.8 | ✅ 完成 | Scene Plan schema + validator |
| T4.9 | ✅ 完成 | Scene Plan validate API 后端 |
| T5.0 | ✅ 完成 | 写作闭环盘点 |
| T5.1 | ✅ 完成 | Scene Plan validate API 软接入 |
| T5.2 | ✅ 完成 | Scene Plan generate API 最小版本 |
| T5.2.1 | ✅ 完成 | raw_output 安全修正 |
| T5.2.2 | ✅ 完成 | 全量回归补票 |
| T5.3 | ✅ 完成 | Scene Plan 持久化 API |
| **T5.4** | **✅ 完成** | **Scene Plan 前端 UI 最小集成** |
| T5.5 | 📋 规划中 | Scene Plan 自动加载优化 |

**预计 T5.4 完成后进度**: 约 77%
