# Solo Workflow

本项目通过 AutoHotkey 在 ChatGPT 和 Solo 之间传递任务和结果，因此仓库不维护 TASK.md / RESULT.md。

## 流程

1. ChatGPT 生成任务。
2. 用户通过 AutoHotkey 将任务发给 Solo。
3. Solo 阅读 AGENTS.md 和相关文档。
4. Solo 修改代码。
5. Solo 运行检查脚本。
6. Solo 按 Solo Final Response Format 输出最终结果。
7. 用户通过 AutoHotkey 将 Solo 结果发回 ChatGPT。
8. ChatGPT 通过 GitHub commit 进行验收。

## 检查脚本

```powershell
# 文档检查
powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode docs

# 后端检查
powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode backend

# 前端检查
powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode frontend

# 全部检查
powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode all

# Guardrails 检查
powershell -ExecutionPolicy Bypass -File scripts/solo-guardrails.ps1
```

Bash 版本：

```bash
bash scripts/solo-check.sh docs
bash scripts/solo-check.sh backend
bash scripts/solo-check.sh frontend
bash scripts/solo-check.sh all
bash scripts/solo-guardrails.sh
```

## AutoHotkey Integration

本工具不负责抓取 ChatGPT 网页任务。

用户使用 AutoHotkey 自动在 ChatGPT 和 Solo 之间传递任务文本和结果。

Solo 只需要按 Solo Final Response Format 输出最终回复即可。

## What NOT to Do

- 不要创建 TASK.md 或 RESULT.md
- 不要抓取 ChatGPT 网页
- 不要自动发送 ChatGPT 消息
- 不要保存 Cookie
- 不要加入 CI
