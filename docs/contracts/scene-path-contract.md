# Scene Path Contract / 场景路径契约

本文档定义了 `sec-*.md` 场景文件的路径规则，前端 `scenePath.ts` 和后端 `SceneService` 必须共同遵守。

---

## 核心定义

| 术语 | 含义 | 示例 |
|------|------|------|
| `sec-*.md` | 单场景文件 | `sec-001.md` |
| `ch-*` | 章目录 | `ch-001/` |
| `vol-*` | 卷目录 | `vol-01/` |

## 标准路径格式

```
chapters/vol-{VV}/ch-{CCC}/sec-{SSS}.md
```

- `VV` — 卷号，2 位零填充
- `CCC` — 章号，3 位零填充
- `SSS` — 场景号，3 位零填充

示例：`chapters/vol-01/ch-001/sec-003.md`

## 默认配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scenes_per_chapter` | 5 | 每章场景数 |
| `chapters_per_volume` | 12 | 每卷章数 |
| `target_chars` | 800 | 场景目标字数（中文字） |

## 进位规则

### 场景进位

```
sec-001 → sec-002 → ... → sec-005 → 下一章 sec-001
```

当 `scene < scenes_per_chapter` 时，`scene + 1`。
当 `scene == scenes_per_chapter` 时，进位到下一章 `scene = 1`。

### 章进位

```
ch-001/sec-005 → ch-002/sec-001
ch-011/sec-005 → ch-012/sec-001
ch-012/sec-005 → vol-02/ch-001/sec-001
```

当 `chapter < chapters_per_volume` 时，`chapter + 1, scene = 1`。
当 `chapter == chapters_per_volume` 时，进位到下一卷 `chapter = 1, scene = 1`。

### 卷进位

```
vol-01/ch-012/sec-005 → vol-02/ch-001/sec-001
```

当达到当前卷最后一章最后一场景时，进位到下一卷 `volume + 1, chapter = 1, scene = 1`。

## 正则表达式

```
chapters/vol-(\d+)/ch-(\d+)/sec-(\d+)\.md$
```

前后端必须使用相同的正则模式。

## 路径构建规则

- 卷号：`str(volume).zfill(2)` / `String(volume).padStart(2, '0')`
- 章号：`str(chapter).zfill(3)` / `String(chapter).padStart(3, '0')`
- 场景号：`str(scene).zfill(3)` / `String(scene).padStart(3, '0')`

## 非法路径

以下路径必须被拒绝（返回 `null` / `None`）：

- 不匹配正则的路径：`foo/bar.md`
- 缺少层级：`chapters/vol-01/sec-001.md`
- 非场景文件：`chapters/vol-01/ch-001/ch-plan.md`
- 路径中间有额外层级：`chapters/vol-01/extra/ch-001/sec-001.md`

## 章规划路径

```
chapters/vol-{VV}/ch-{CCC}/ch-plan.md
```

示例：`chapters/vol-01/ch-001/ch-plan.md`

## 辅助解析函数

| 函数 | 输入 | 输出 |
|------|------|------|
| `parseVolumeDir` | `vol-01` | `1` |
| `parseChapterDir` | `ch-001` | `1` |
| `parseSceneFileName` | `sec-003.md` | `3` |

## 实现位置

| 端 | 文件 |
|----|------|
| Frontend | `frontend/src/modules/scene/scenePath.ts` |
| Backend | `backend/application/scene_service.py` |
| Domain | `backend/domain/scene.py` |

## 测试覆盖

| 端 | 文件 |
|----|------|
| Frontend | `frontend/src/modules/scene/__tests__/scenePath.spec.ts` |
| Backend | `backend/tests/test_scene_path_contract.py` |
