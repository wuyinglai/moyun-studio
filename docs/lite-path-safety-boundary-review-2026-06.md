# Lite Path Safety Boundary Review

## 1. 背景

Phase 3.4E 已完成两个低风险 helper 清理（`_prefs_to_text` 和 `_lite_action_to_candidate_action`），当前 `backend/api/lite.py` 中仍有两个与路径安全相关的 helper：
- `_safe_project_path()`
- `_validate_project_id()`

这两个函数涉及路径安全边界，不能像普通 helper 一样直接迁移。本报告旨在分析它们的职责、与其他组件的关系、现有测试覆盖，并给出迁移建议。

## 2. 当前 `_safe_project_path()` 职责

### 2.1 函数签名与位置
```python
def _safe_project_path(project_dir: Path, rel_path: str) -> Path:
```
位置：`backend/api/lite.py` 第 203-243 行

### 2.2 输入输出
- **输入**：`project_dir: Path` - 项目根目录；`rel_path: str` - 相对于项目的路径
- **输出**：`Path` - 解析后的安全绝对路径

### 2.3 安全检查清单
| 检查项 | 规则 | 错误消息 |
|--------|------|----------|
| 空路径 | `not rel_path` | "相对路径不能为空" |
| 绝对路径 | `normalized.startswith("/")` | "不允许绝对路径" |
| Windows 盘符 | `len(normalized) >= 2 and normalized[1] == ":"` | "不允许 Windows 盘符路径" |
| 路径遍历 | `seg == ".."` | "路径包含遍历段 '..'" |
| 禁止段 | `.git`, `node_modules`, `__pycache__`, `.env`, `.config.json` | "路径包含禁止段" |
| 路径逃逸 | 解析后路径不在 project_dir 内 | "路径逃逸出项目目录" |

### 2.4 调用位置
根据代码分析，`_safe_project_path` 主要在 Lite API 内部被调用，用于验证用户输入的文件路径。

## 3. 当前 `_validate_project_id()` 职责

### 3.1 函数签名与位置
```python
def _validate_project_id(project_id: str) -> str:
```
位置：`backend/api/lite.py` 第 170-181 行

### 3.2 输入输出
- **输入**：`project_id: str` - 用户提供的项目 ID
- **输出**：`str` - 验证通过的 project_id（原样返回）

### 3.3 安全检查清单
| 检查项 | 规则 | 错误消息 |
|--------|------|----------|
| 空值 | `not project_id or not project_id.strip()` | "project_id 不能为空" |
| 路径分隔符 | `"/" in project_id or "\\" in project_id` | "project_id 包含非法路径分隔符" |
| 点号开头 | `project_id.startswith(".")` | "project_id 不能以点号开头" |
| 路径遍历 | `".." in project_id` | "project_id 包含路径遍历" |

### 3.4 调用位置
在 `backend/api/lite.py` 中被以下路由调用：
- 第 493 行：`/api/lite/{project_id}/write-next-options`
- 第 555 行：`/api/lite/{project_id}/write-next`
- 第 769 行：`/api/lite/{project_id}/write-next-stream`

## 4. 与 FileService / Path Policy 的关系

### 4.1 FileService 的路径安全机制

`backend/core/file_ops.py` 中的 `FileService._resolve_path()` 方法也实现了路径安全检查：

| 检查项 | FileService._resolve_path | Lite._safe_project_path |
|--------|--------------------------|------------------------|
| 空路径检查 | ✓ | ✓ |
| 绝对路径拒绝 | ✓ | ✓ |
| Windows 盘符拒绝 | ✓ | ✓ |
| 路径遍历 `..` 拒绝 | ✓ | ✓ |
| 禁止段检查 | 部分（`.git`, `node_modules`, `__pycache__`） | ✓（`.git`, `node_modules`, `__pycache__`, `.env`, `.config.json`） |
| 路径越界检查 | ✓（相对于 workspace） | ✓（相对于 project_dir） |

### 4.2 重复分析

**存在部分重复，但职责边界不同：**

1. **作用域不同**：
   - `FileService`：相对于 `workspace` 根目录
   - `Lite`：相对于具体 `project_dir`

2. **调用时机不同**：
   - `FileService`：在文件操作时检查
   - `Lite`：在路由入口处提前检查，提供更明确的错误信息

3. **错误类型不同**：
   - `FileService`：抛出 `ValidationError`
   - `Lite`：抛出 `LitePathError`（继承自 `ValueError`）

4. **禁止段列表**：
   - `FileService`：通过 `prefix` 参数检查
   - `Lite`：硬编码 `_FORBIDDEN_SEGMENTS`

### 4.3 `_validate_rel_path()` 的角色

位于 `_validate_project_id` 和 `_safe_project_path` 之间，提供纯路径字符串验证，不涉及路径解析：
- 被 `_safe_project_path` 内部调用
- 不直接暴露给路由层

## 5. 现有测试覆盖

### 5.1 `test_lite_path_safety.py` 测试覆盖

| 函数 | 测试数 | 覆盖场景 |
|------|--------|----------|
| `_validate_project_id` | 9 | 正常 ID、UUID 风格、空值、空白、`..`、路径分隔符、点号开头 |
| `_validate_rel_path` | 14 | 正常路径、空值、None、路径遍历、绝对路径、Windows 盘符、禁止段（`.git`, `node_modules`, `__pycache__`, `.env`, `.config.json`）、允许路径（`.candidates/`, `chapters/`, `style-guide.md`） |
| `_safe_project_path` | 12 | 正常路径、空路径、路径遍历、绝对路径、Windows 盘符、禁止段、路径逃逸检测、`.` 段规范化 |

### 5.2 测试覆盖评估

**已覆盖：**
- ✓ 空值/空白 project_id
- ✓ 路径分隔符攻击（`/`, `\`）
- ✓ 路径遍历攻击（`..`）
- ✓ 点号开头（隐藏目录攻击）
- ✓ 绝对路径攻击
- ✓ Windows 盘符攻击
- ✓ 禁止段访问（`.git`, `node_modules`, `__pycache__`, `.env`, `.config.json`）
- ✓ 路径逃逸检测
- ✓ `.candidates/` 路径允许
- ✓ `chapters/` 路径允许

**潜在缺口：**
- ✗ Unicode 编码攻击（如 UTF-8 编码的 `..`）
- ✗ 大小写变体攻击（如 `.GIT`, `NODE_MODULES`）
- ✗ 符号链接攻击（虽然 `resolve()` 会跟随符号链接，但未明确处理）
- ✗ 超长路径攻击
- ✗ 非 ASCII 字符路径处理

## 6. 风险缺口

### 6.1 P0 风险（立即修复）
- 无直接 P0 风险，现有检查已覆盖主要攻击向量

### 6.2 P1 风险（建议修复）
1. **大小写敏感性**：`_FORBIDDEN_SEGMENTS` 使用 `.lower()` 转换，但文件名比较在 Windows 上不区分大小写，在 Linux 上区分大小写
2. **符号链接**：`resolve()` 会跟随符号链接，可能导致路径逃逸

### 6.3 P2 风险（可后续处理）
1. **Unicode 编码攻击**：某些 Unicode 字符可能被解释为路径分隔符
2. **超长路径**：可能导致 DoS 或解析错误

## 7. 是否建议迁移

### 7.1 结论：**暂不迁移**

### 7.2 理由

**为什么不建议迁移 `_safe_project_path()`：**
1. **边界明确**：该函数是 Lite 路由层的安全边界，与 `FileService` 的边界不同（project_dir vs workspace）
2. **错误语义**：`LitePathError` 提供 Lite 特有的错误消息，更适合 API 响应
3. **禁止段差异**：Lite 有自己的禁止段列表（包含 `.env`, `.config.json`）
4. **性能考虑**：在路由层提前检查可以避免不必要的 `FileService` 调用
5. **测试覆盖**：现有测试直接依赖 `backend/api/lite.py` 的导入

**为什么不建议迁移 `_validate_project_id()`：**
1. **路由层职责**：project_id 验证是路由入口的第一道防线
2. **错误响应**：在路由层抛出错误可以提供更及时的用户反馈
3. **Lite 特有**：验证逻辑与 Lite 的项目结构紧密相关
4. **简化调用**：直接在路由中调用比注入 service 更简单

### 7.3 如果未来考虑迁移

**推荐方案：**

1. **新建 `backend/application/lite_path_policy.py`**：
   - 包含 `validate_project_id()`
   - 包含 `validate_rel_path()`
   - 包含 `safe_project_path()`
   - 保持 `LitePathError` 在 `lite.py` 中或移到 `schemas/`

2. **保留 `_validate_project_id` 作为路由层入口**：
   - 路由层仍调用 `_validate_project_id()`
   - 但内部实现委托给新的 policy 模块

## 8. 推荐下一步最小任务

> **Phase 3.4G-A：补全路径安全文档与注释**

**任务范围：**
1. 为 `_validate_project_id()` 添加详细 docstring，说明每个检查的安全目的
2. 为 `_validate_rel_path()` 添加详细 docstring
3. 为 `_safe_project_path()` 添加详细 docstring
4. 添加 `_FORBIDDEN_SEGMENTS` 的注释说明选择理由
5. 更新 `test_lite_path_safety.py` 的文档说明测试覆盖范围

**不涉及代码逻辑修改，只添加文档和注释。**

## 9. 不建议做的事情

1. **不要立即删除或迁移** `_safe_project_path()` 和 `_validate_project_id()`
2. **不要合并** Lite 的路径安全与 `FileService` 的路径安全（边界不同）
3. **不要依赖** `FileService` 作为唯一的安全边界（防御深度原则）
4. **不要**在没有完整测试覆盖的情况下进行迁移

---

## 附录：代码位置参考

| 组件 | 文件 | 行号 |
|------|------|------|
| `_validate_project_id` | `backend/api/lite.py` | L170-181 |
| `_validate_rel_path` | `backend/api/lite.py` | L184-200 |
| `_safe_project_path` | `backend/api/lite.py` | L203-243 |
| `_FORBIDDEN_SEGMENTS` | `backend/api/lite.py` | L163 |
| `FileService._resolve_path` | `backend/core/file_ops.py` | L44-99 |
| 路径安全测试 | `backend/tests/test_lite_path_safety.py` | 完整文件 |

---

**审查日期**：2026-06-02  
**审查版本**：commit `958fc28fb1545c5331ec9645c5e6b9c0da621d26`