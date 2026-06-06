# T4.7.1a E2E 测试结果

**执行时间**: 2026-06-06 23:50:52

---

## T4.7.1a-2a：CandidatePanel 打开机制排查

**脚本**: `tests/test_candidate_panel_probe.py`

### 诊断结果

- **诊断结论**: API 请求失败 - 502 Bad Gateway 导致前端无法设置 currentProject
- **.candidate-panel 数量**: 0
- **.candidate-card 数量**: 0
- **候选稿 tab 数量**: 0
- **URL 正确**: `http://localhost:5174/project/demo-novel/file/scenes/__e2e_test_scene.md`
- **页面显示**: "未打开项目" - 表明 `projectStore.currentProject` 为 null
- **右侧面板**: 未挂载（因为 currentProject 为 null）

### Console/Page Errors

**Console Errors (29) - 全部为 502 Bad Gateway:**
- `Failed to load resource: the server responded with a status of 502 (Bad Gateway)`
- `Failed to load resource: the server responded with a status of 502 (Bad Gateway)`
- `Failed to load resource: the server responded with a status of 502 (Bad Gateway)`
- `Failed to load resource: the server responded with a status of 502 (Bad Gateway)`
- `Failed to load resource: the server responded with a status of 502 (Bad Gateway)`

✅ 无 Page Errors

### /api/candidates 请求

❌ 未捕获到 /api/candidates 请求（因为前端连不上后端）

### 真实归因

**归因 5：API 请求失败 - 502 Bad Gateway**

后端服务返回 502 Bad Gateway，导致：
1. 前端无法获取项目信息
2. `projectStore.currentProject` 无法设置
3. RightPanel 组件未挂载
4. 候选稿 tab 和 CandidatePanel 不存在

**注意**：这不是 UI locator 错误，也不是 UI 渲染错误，而是后端连接失败。

### 截图路径

- `docs/testing/screenshots/t471a2a_probe_initial.png`
- `docs/testing/screenshots/t471a2a_after_normal_click.png`
- `docs/testing/screenshots/t471a2a_after_force_click.png`
- `docs/testing/screenshots/t471a2a_after_js_click.png`
- `docs/testing/screenshots/t471a2a_after_nav_candidate.png`

### 约束检查

- **是否修改业务逻辑**: 否
- **是否调用 LLM**: 否
- **是否修改生产 Prompt**: 否

### 结论

**T4.7.1a-2a 判定**: ✅ 排查完成，根因定位

**T4.7.1a-2 状态**: ❌ FAIL（后端 502 问题阻塞，非 UI locator 问题）

**T4.7.1a 整体状态**: ❌ FAIL（等待 adopt/conflict/SSE 验证 + 后端问题解决）

---

## 历史记录

### T4.7.1a-2 retry（简化版）

- **问题**：JavaScript 点击 tab 后 `.candidate-panel` 不出现
- **根因**：502 Bad Gateway 导致后端不可用

### T4.7.1a-2a（当前）

- **问题**：点击候选稿 tab 后 panel 不渲染
- **根因**：后端返回 502，前端无法正确初始化
- **修复建议**：需要检查后端服务状态，或等待后端恢复后重测
