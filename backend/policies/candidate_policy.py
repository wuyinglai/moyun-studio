"""墨韵 - 候选稿策略

判断某种操作是否必须生成候选稿，而非直接覆盖正式正文。

规则来源：
- AGENTS.md "Non-negotiable Product Rules" 第 5-6 条
- docs/contracts/scene-path-contract.md
"""

from __future__ import annotations

import re


# 高风险操作：默认必须生成 candidate
HIGH_RISK_ACTIONS = frozenset({
    "rewrite",
    "polish",
    "chat_edit",
    "chat",
    "more_exciting",
    "more_reasonable",
    "expand",
    "shrink",
    "modify",
    "rewrite_current_scene",
    "polish_current_scene",
    "chat_edit_current_scene",
})

# 安全操作：默认直接写入
SAFE_ACTIONS = frozenset({
    "extract",
    "write_new_scene",
    "continue",
    "append",
})

# 场景文件正则
_SCENE_PATTERN = re.compile(r"^chapters/vol-\d+/ch-\d+/sec-\d+\.md$")

# 核心状态文件（直接覆盖需要显式 safe flag）
CORE_STATE_FILES = frozenset({
    "story-state.md",
    "recent-context.md",
    "style-guide.md",
    "outline.md",
    "story-engine.md",
    "meta.json",
})


def is_scene_file(path: str) -> bool:
    """判断路径是否为场景文件（chapters/vol-XX/ch-XXX/sec-XXX.md）"""
    return bool(_SCENE_PATTERN.match(path))


def is_core_state_file(path: str) -> bool:
    """判断路径是否为核心状态文件"""
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    return filename in CORE_STATE_FILES


def should_create_candidate(
    action: str,
    target_path: str,
    file_exists: bool,
    file_has_content: bool,
) -> bool:
    """判断是否应该生成候选稿而非直接写入。

    Args:
        action: 操作类型（rewrite, polish, write_new_scene 等）
        target_path: 目标文件相对路径
        file_exists: 目标文件是否存在
        file_has_content: 目标文件是否有实质内容

    Returns:
        True 表示应该生成 candidate，False 表示可以直接写入
    """
    action_lower = action.lower().strip()

    # 规则 1：高风险操作 → candidate
    if action_lower in HIGH_RISK_ACTIONS:
        return True

    # 规则 2：场景文件已有内容 → candidate
    if is_scene_file(target_path) and file_has_content:
        return True

    # 规则 3：核心状态文件已有内容 → candidate
    if is_core_state_file(target_path) and file_has_content:
        return True

    # 规则 4：write_new_scene / write_next_scene / write_current_scene 且目标为空 → 直接写入
    if action_lower in ("write_new_scene", "write", "write_next_scene", "write_current_scene") and not file_has_content:
        return False

    # 规则 5：extract → 直接写入
    if action_lower == "extract":
        return False

    # 规则 6：continue/append 且目标为空 → 直接写入
    if action_lower in ("continue", "append") and not file_has_content:
        return False

    # 兜底：有内容就 candidate
    return file_has_content
