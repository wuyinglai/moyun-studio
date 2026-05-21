"""墨韵 - 生成输出策略

决定生成结果应该写入（write）、生成候选稿（candidate）、追加（append）、还是拒绝（reject）。

规则来源：
- AGENTS.md "Non-negotiable Product Rules" 第 5-6, 9-11 条
- docs/contracts/scene-path-contract.md
- pipeline.py _normalize_output_mode / _is_dangerous_output
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


OutputMode = Literal["write", "candidate", "append", "reject"]


# 场景文件正则
_SCENE_PATTERN = re.compile(r"^chapters/vol-\d+/ch-\d+/sec-\d+\.md$")

# 安全路径前缀白名单
_SAFE_PREFIXES = (
    "materials/extracted/",
    "materials/drafts/",
    ".candidates/",
    "revision-log/",
    "logs/",
)

# 危险路径模式
_DANGEROUS_PATTERNS = (
    "/sec-",
    "style-guide.md",
    "story-state.md",
    "recent-context.md",
    "outline.md",
    "meta.json",
    "ch-meta.json",
    "story-engine.md",
)

# 高风险管线名
_HIGH_RISK_PIPELINES = frozenset({
    "polish", "rewrite",
})

# 高风险管线名后缀
_HIGH_RISK_SUFFIXES = ("-polish", "-rewrite")


@dataclass
class OutputDecision:
    """输出决策结果"""
    mode: OutputMode
    reason: str


def is_scene_file(path: str) -> bool:
    """判断路径是否为场景文件"""
    return bool(_SCENE_PATTERN.match(path))


def is_dangerous_output(path: str) -> bool:
    """判断输出路径是否为危险路径（需要候选稿保护）

    安全路径白名单：
    - materials/extracted/
    - materials/drafts/
    - .candidates/
    - revision-log/
    - logs/

    危险路径检测：
    - 章节文件（/sec-）
    - 核心状态文件（style-guide.md, story-state.md 等）
    """
    path_lower = path.lower()

    # 安全路径白名单
    for prefix in _SAFE_PREFIXES:
        if path_lower.startswith(prefix):
            return False

    # 危险路径检测
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in path_lower:
            return True

    return False


def decide_output(
    action: str,
    target_path: str,
    output_mode: str | None = None,
    file_exists: bool = False,
    file_has_content: bool = False,
    require_candidate: bool = False,
    pipeline_name: str | None = None,
) -> OutputDecision:
    """决定生成结果的输出方式。

    Args:
        action: 操作类型（rewrite, polish, write_new_scene, extract 等）
        target_path: 目标文件相对路径
        output_mode: 显式指定的输出模式（overwrite, write_scene, candidate, append, rewrite, none）  # AI_GUARDRAIL_ALLOW: docstring
        file_exists: 目标文件是否存在
        file_has_content: 目标文件是否有实质内容
        require_candidate: 是否强制生成候选稿
        pipeline_name: 管线名称（用于推断高风险管线）

    Returns:
        OutputDecision 包含 mode 和 reason
    """

    # 规则 0：强制 candidate
    if require_candidate:
        return OutputDecision(mode="candidate", reason="require_candidate=True 强制候选稿")

    action_lower = action.lower().strip()

    # 规则 1：高风险管线 → candidate
    if pipeline_name:
        pipeline_lower = pipeline_name.lower()
        if pipeline_lower in _HIGH_RISK_PIPELINES or pipeline_lower.endswith(_HIGH_RISK_SUFFIXES):
            return OutputDecision(
                mode="candidate",
                reason=f"高风险管线 {pipeline_name} 默认生成候选稿",
            )

    # 规则 2：高风险操作 → candidate
    high_risk_actions = {"rewrite", "polish", "chat_edit", "chat", "more_exciting", "more_reasonable", "modify"}
    if action_lower in high_risk_actions:
        return OutputDecision(
            mode="candidate",
            reason=f"高风险操作 {action} 默认生成候选稿",
        )

    # 规则 3：显式 output_mode 处理
    if output_mode:
        mode_lower = output_mode.lower()

        if mode_lower == "candidate":
            return OutputDecision(mode="candidate", reason="output_mode=candidate 显式指定")

        if mode_lower == "none":
            return OutputDecision(mode="reject", reason="output_mode=none 不写入")

        if mode_lower == "append":
            return OutputDecision(mode="append", reason="output_mode=append 追加模式")

        if mode_lower == "write_scene":
            if file_has_content:
                return OutputDecision(
                    mode="candidate",
                    reason=f"write_scene 但目标 {target_path} 已有内容，转为候选稿",
                )
            return OutputDecision(mode="write", reason="write_scene 且目标为空，直接写入")

        if mode_lower in ("overwrite", "rewrite"):
            # overwrite/rewrite 对危险路径 → candidate
            if is_dangerous_output(target_path):
                return OutputDecision(
                    mode="candidate",
                    reason=f"overwrite/rewrite 对危险路径 {target_path}，转为候选稿",
                )
            if is_scene_file(target_path):
                return OutputDecision(
                    mode="candidate",
                    reason=f"overwrite/rewrite 对场景文件 {target_path}，转为候选稿",
                )
            return OutputDecision(mode="write", reason=f"output_mode={output_mode} 且路径安全，直接写入")

    # 规则 4：场景文件已有内容 → candidate
    if is_scene_file(target_path) and file_has_content:
        return OutputDecision(
            mode="candidate",
            reason=f"场景文件 {target_path} 已有内容，生成候选稿",
        )

    # 规则 5：核心状态文件已有内容 → candidate
    if is_dangerous_output(target_path) and file_has_content:
        return OutputDecision(
            mode="candidate",
            reason=f"危险路径 {target_path} 已有内容，生成候选稿",
        )

    # 规则 6：extract → write
    if action_lower == "extract":
        return OutputDecision(mode="write", reason="extract 操作直接写入")

    # 规则 7：新空场景 → write
    if action_lower in ("write_new_scene", "write") and not file_has_content:
        return OutputDecision(mode="write", reason="新空场景，直接写入")

    # 规则 8：continue/append 且目标为空 → write
    if action_lower in ("continue", "append") and not file_has_content:
        return OutputDecision(mode="write", reason="追加模式且目标为空，直接写入")

    # 兜底：有内容就 candidate
    if file_has_content:
        return OutputDecision(mode="candidate", reason="目标已有内容，生成候选稿")

    return OutputDecision(mode="write", reason="默认直接写入")
