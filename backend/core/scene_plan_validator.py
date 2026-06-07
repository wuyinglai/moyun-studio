"""墨韵 - Scene Plan 校验器

校验 Scene Plan 的完整性、安全性和业务规则，包括：
- 必填字段验证
- Candidate 策略强制规则
- 路径安全检查
- 内容完整性验证
"""

import re
from dataclasses import dataclass
from typing import Any

from backend.schemas.scene_plan import ScenePlan


@dataclass
class ScenePlanValidationError:
    """Scene Plan 校验错误"""
    field: str
    message: str


@dataclass
class ScenePlanValidationWarning:
    """Scene Plan 校验警告"""
    field: str
    message: str


@dataclass
class ScenePlanValidationResult:
    """Scene Plan 校验结果"""
    valid: bool = True
    errors: list[ScenePlanValidationError] = None
    warnings: list[ScenePlanValidationWarning] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# 危险路径模式
DANGEROUS_PATH_PATTERNS = [
    r"^\.\.",              # 父目录遍历
    r"^\.env",            # 环境文件
    r"^\.git",            # Git 目录
    r"^[A-Za-z]:\\",      # Windows 绝对路径（盘符）
    r"^[A-Za-z]:/",       # Windows 绝对路径（Unix 风格）
    r"^/",                # Unix 绝对路径
]

# 危险路径正则
_dangerous_path_re = re.compile("|".join(DANGEROUS_PATH_PATTERNS))


def _is_dangerous_path(path: str) -> bool:
    """检查路径是否危险"""
    return bool(_dangerous_path_re.search(path))


def validate_scene_plan(
    scene_plan: ScenePlan | dict[str, Any],
) -> ScenePlanValidationResult:
    """校验 Scene Plan

    Args:
        scene_plan: ScenePlan 对象或字典

    Returns:
        ScenePlanValidationResult
    """
    result = ScenePlanValidationResult()
    data_dict = scene_plan if isinstance(scene_plan, dict) else None

    # 1. 如果是字典，先初步检查必填字段是否存在
    if data_dict:
        # 检查顶级必填字段
        required_fields = ["project_id", "source_path", "title", "goal", "conflict", "required_beats", "output_intent"]
        for field in required_fields:
            if field not in data_dict:
                result.valid = False
                result.errors.append(ScenePlanValidationError(
                    field=field,
                    message=f"{field} 是必填字段",
                ))

    # 2. 转换为 ScenePlan 对象（如果还没失败）
    if isinstance(scene_plan, dict) and result.valid:
        try:
            scene_plan = ScenePlan(**scene_plan)
        except Exception as e:
            result.valid = False
            result.errors.append(ScenePlanValidationError(
                field="__root__",
                message=f"Scene Plan 结构解析失败: {e}",
            ))
            return result

    # 3. 如果已经有错误，直接返回
    if not result.valid:
        return result

    # 4. 必填字段验证
    if not scene_plan.project_id or scene_plan.project_id.strip() == "":
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="project_id",
            message="project_id 不能为空",
        ))

    if not scene_plan.source_path or scene_plan.source_path.strip() == "":
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="source_path",
            message="source_path 不能为空",
        ))

    if not scene_plan.title or scene_plan.title.strip() == "":
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="title",
            message="title 不能为空",
        ))

    if not scene_plan.goal or scene_plan.goal.strip() == "":
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="goal",
            message="goal 不能为空",
        ))

    if not scene_plan.conflict or scene_plan.conflict.strip() == "":
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="conflict",
            message="conflict 不能为空",
        ))

    # 5. required_beats 至少 1 条
    if not scene_plan.required_beats or len(scene_plan.required_beats) == 0:
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="required_beats",
            message="required_beats 至少需要 1 条",
        ))

    # 6. Candidate 策略强制规则
    if not scene_plan.candidate_policy.require_candidate:
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="candidate_policy.require_candidate",
            message="candidate_policy.require_candidate 必须为 true",
        ))

    if scene_plan.candidate_policy.allow_direct_write:
        result.valid = False
        result.errors.append(ScenePlanValidationError(
            field="candidate_policy.allow_direct_write",
            message="candidate_policy.allow_direct_write 必须为 false",
        ))

    # 7. 路径安全检查 - material_paths
    for i, path in enumerate(scene_plan.references.material_paths):
        if _is_dangerous_path(path):
            result.valid = False
            result.errors.append(ScenePlanValidationError(
                field=f"references.material_paths[{i}]",
                message=f"路径 '{path}' 包含危险模式",
            ))

    # 8. 路径安全检查 - recent_context_paths
    for i, path in enumerate(scene_plan.references.recent_context_paths):
        if _is_dangerous_path(path):
            result.valid = False
            result.errors.append(ScenePlanValidationError(
                field=f"references.recent_context_paths[{i}]",
                message=f"路径 '{path}' 包含危险模式",
            ))

    # 9. Characters 为空警告
    if not scene_plan.characters or len(scene_plan.characters) == 0:
        result.warnings.append(ScenePlanValidationWarning(
            field="characters",
            message="characters 列表为空，建议至少添加 1 个人物",
        ))

    return result
