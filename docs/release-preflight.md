# Release Preflight Checklist / 发布前检查

Run the preflight script before creating any release to catch common issues early.

## Quick Usage

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release-preflight.ps1 -Version v0.2.0
```

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
