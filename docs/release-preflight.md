# Release Preflight Checklist / 发布前检查

Run the preflight script before creating any release to catch common issues early.

## Quick Usage

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release-preflight.ps1 -Version v0.2.0
```

---

## Smoke Checklist (发布前最小验证)

### 1. Git 状态检查

```powershell
cd d:\newmoyun
git status --short              # 必须为空（clean）
git rev-parse HEAD
git rev-parse origin/main
git ls-remote origin refs/heads/main  # 三者必须相等
git diff --check                # 必须无输出
```

**通过条件**：工作区 clean，HEAD == origin/main == ls-remote，无冲突

---

### 2. 环境变量安全检查

```powershell
# 确认未启用真实 LLM smoke（必须返回空）
Get-ChildItem Env:ALLOW_REAL_LLM_SMOKE,Env:MOYUN_ALLOW_REAL_LLM_SMOKE,Env:LLM_SMOKE_MAX_TOKENS,Env:MOYUN_LLM_SMOKE_MAX_TOKENS -ErrorAction SilentlyContinue
```

**通过条件**：无输出（所有 smoke 变量均未设置）

---

### 3. 端口占用检查

```powershell
# 检查前端端口（如被占用需先释放）
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue

# 检查后端端口（如被占用需先释放）
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

**端口占用处理**：
```powershell
# 查找占用进程
netstat -ano | findstr :5173

# 终止进程（替换 <PID> 为实际进程 ID）
taskkill /PID <PID> /F
```

---

### 4. 后端启动验证

```powershell
# 启动后端（新开终端）
cd d:\newmoyun\backend
$env:PYTHONPATH="d:\newmoyun"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 验证后端可访问
Invoke-WebRequest http://127.0.0.1:8000/api/projects -UseBasicParsing -TimeoutSec 5
```

**通过条件**：返回 JSON 项目列表

---

### 5. 前端 E2E 关键测试

```powershell
cd d:\newmoyun\frontend

# Candidate workflow 测试（含 T6.9.2 新增安全文案断言）
npx playwright test tests/e2e/14-candidate-workflow.spec.ts --project=chromium --reporter=line

# Dry-run UI 入口测试（含 T6.9.2 新增 dev-tools 副标题断言）
npx playwright test tests/e2e/24-dry-run-ui-entry.spec.ts --project=chromium --reporter=line
```

**通过条件**：全部测试通过

---

### 6. 前端构建验证

```powershell
cd d:\newmoyun\frontend
npm run build
```

**通过条件**：build 成功完成，无 fatal 错误

---

### 7. 禁止事项

| 禁止行为 | 说明 |
|---------|------|
| 调用真实 LLM | 发布前 smoke 默认不得调用真实 LLM，仅用 mock |
| 使用真实 API Key | 不得在测试环境使用真实 API Key |
| 提交测试产物 | 不得提交 Playwright 截图、trace、临时文件 |
| 提交 .env | `.env` 必须保持 gitignored，不得提交 |

---

## Preflight Checks

| # | Check | What it verifies | Fix if failed |
|---|-------|-----------------|---------------|
| 1 | Current branch | Must be `main` | `git checkout main` |
| 2 | Clean working tree | No uncommitted changes | Commit or stash changes |
| 3 | Local tag not exists | Tag `vX.Y.Z` must not already exist locally | `git tag -d vX.Y.Z` to remove old tag |
| 4 | Remote tag not exists | Tag must not already exist on origin | `git push origin :refs/tags/vX.Y.Z` to remove remote tag |
| 5 | Release notes exist | `docs/releases/vX.Y.Z.md` must exist | Create the release notes file |
| 6 | `gh` CLI available | GitHub CLI must be installed and authenticated | Install `gh` or use Python fallback below |

## Fallback: Creating GitHub Release without `gh`

If `gh` CLI is unavailable, use the GitHub REST API with a personal access token:

```powershell
python -c "
import json, urllib.request, ssl, sys

version = 'vX.Y.Z'  # replace with actual version
with open('docs/releases/' + version + '.md', 'r', encoding='utf-8') as f:
    body = f.read()

data = json.dumps({
    'tag_name': version,
    'target_commitish': 'main',
    'name': 'Moyun Studio ' + version,
    'body': body,
    'draft': False,
    'prerelease': False
}).encode('utf-8')

req = urllib.request.Request(
    'https://api.github.com/repos/wuyinglai/moyun-studio/releases',
    data=data,
    headers={
        'Authorization': 'token YOUR_TOKEN_HERE',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json; charset=utf-8'
    },
    method='POST'
)

resp = urllib.request.urlopen(req, context=ssl.create_default_context())
result = json.loads(resp.read().decode('utf-8'))
print('Release: ' + result['html_url'])
"
```

## Release Workflow

1. Run preflight checks: `scripts/release-preflight.ps1 -Version vX.Y.Z`
2. Fix any failures
3. Push to main: `git push origin main`
4. Create local tag: `git tag vX.Y.Z`
5. Push tag: `git push origin vX.Y.Z`
6. Create GitHub Release:
   - Preferred: `gh release create vX.Y.Z --title "Moyun Studio vX.Y.Z" --notes-file docs/releases/vX.Y.Z.md`
   - Fallback: Use the Python script above
7. Run post-release verification: `scripts/verify-release.ps1`

## Tag Management

If a tag was created on the wrong commit:

```powershell
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin :refs/tags/vX.Y.Z

# Recreate on current HEAD
git tag vX.Y.Z
git push origin vX.Y.Z
```
