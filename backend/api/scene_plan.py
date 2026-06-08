"""墨韵 - Scene Plan API 路由

端点：
  POST /api/scene-plan/validate  校验 Scene Plan 结构
  POST /api/scene-plan/generate  生成 Scene Plan 草案
  POST /api/scene-plan/save     保存 Scene Plan 到文件
  GET  /api/scene-plan/load     从文件加载 Scene Plan
"""

import json
import logging
import re
from typing import Any
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.core.scene_plan_validator import (
    validate_scene_plan,
    ScenePlanValidationResult,
    ScenePlanValidationError,
    ScenePlanValidationWarning,
)
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.file_ops import FileService
from backend.schemas.common import ApiResponse
from backend.schemas.scene_plan import ScenePlan, CreatedBy, OutputIntent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scene-plan"], prefix="/scene-plan")


# ─── Schema ──────────────────────────────────────────────────────────

class ScenePlanValidationErrorDetail(BaseModel):
    """校验错误详情"""
    field: str
    message: str


class ScenePlanValidationWarningDetail(BaseModel):
    """校验警告详情"""
    field: str
    message: str


class ScenePlanValidateResponse(BaseModel):
    """Scene Plan 校验响应"""
    valid: bool
    errors: list[ScenePlanValidationErrorDetail] = Field(default_factory=list)
    warnings: list[ScenePlanValidationWarningDetail] = Field(default_factory=list)


class ScenePlanGenerateRequest(BaseModel):
    """Scene Plan 生成请求"""
    project_id: str = Field(..., description="项目 ID")
    target_file: str = Field(..., description="目标场景文件路径（项目内相对路径）")
    instruction: str | None = Field(default=None, description="可选生成指令")
    dry_run: bool = Field(default=True, description="是否为干运行（当前阶段仅支持 true）")
    include_raw_output: bool = Field(
        default=False,
        description="是否返回 LLM 原始输出，仅调试用，默认 false 以保护用户内容"
    )


class ScenePlanSourceSummary(BaseModel):
    """源文件摘要"""
    target_file: str
    used_story_state: bool = False
    used_style_guide: bool = False
    used_recent_context: bool = False


class ScenePlanGenerateResponse(BaseModel):
    """Scene Plan 生成响应"""
    scene_plan: ScenePlan | None = Field(default=None, description="生成的 Scene Plan")
    valid: bool = Field(default=False, description="是否通过校验")
    errors: list[ScenePlanValidationErrorDetail] = Field(default_factory=list, description="校验错误")
    warnings: list[ScenePlanValidationWarningDetail] = Field(default_factory=list, description="校验警告")
    raw_output: str | None = Field(default=None, description="LLM 原始输出（仅调试用）")
    source_summary: ScenePlanSourceSummary = Field(..., description="源文件摘要")


class ScenePlanSaveRequest(BaseModel):
    """Scene Plan 保存请求"""
    project_id: str = Field(..., description="项目 ID")
    target_file: str = Field(..., description="目标场景文件路径（用于生成 Scene Plan 文件名）")
    scene_plan: ScenePlan | dict[str, Any] = Field(..., description="要保存的 Scene Plan")
    overwrite: bool = Field(default=False, description="是否覆盖已存在的文件")
    expected_mtime: float | None = Field(default=None, description="期望的文件修改时间，用于冲突检测")


class ScenePlanSaveResponse(BaseModel):
    """Scene Plan 保存响应"""
    saved: bool = Field(default=False, description="是否保存成功")
    path: str | None = Field(default=None, description="保存的文件路径")
    valid: bool = Field(default=False, description="是否通过校验")
    errors: list[ScenePlanValidationErrorDetail] = Field(default_factory=list, description="校验错误")
    warnings: list[ScenePlanValidationWarningDetail] = Field(default_factory=list, description="校验警告")
    conflict: bool = Field(default=False, description="是否因为文件已存在而冲突")
    message: str | None = Field(default=None, description="附加消息")


class ScenePlanLoadResponse(BaseModel):
    """Scene Plan 加载响应"""
    exists: bool = Field(default=False, description="文件是否存在")
    path: str | None = Field(default=None, description="文件路径")
    scene_plan: ScenePlan | None = Field(default=None, description="加载的 Scene Plan")
    mtime: float | None = Field(default=None, description="文件修改时间")
    errors: list[ScenePlanValidationErrorDetail] = Field(default_factory=list, description="错误信息")


# ─── 辅助函数 ─────────────────────────────────────────────────────────

def _extract_json_from_output(output: str) -> str:
    """从 LLM 输出中提取 JSON

    尝试多种方式：
    1. 直接解析
    2. 提取 ```json 代码块
    3. 提取第一个 { ... } 块
    """
    # 尝试直接解析
    try:
        json.loads(output.strip())
        return output.strip()
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json 块
    json_block_match = re.search(r"```json\s*\n?(.*?)\n?```", output, re.DOTALL)
    if json_block_match:
        return json_block_match.group(1).strip()

    # 尝试提取第一个 { ... } 块
    json_obj_match = re.search(r"(\{.*\})", output, re.DOTALL)
    if json_obj_match:
        return json_obj_match.group(1).strip()

    return output.strip()


async def _load_project_context(
    project_id: str,
    target_file: str,
    file_service: FileService,
    source_summary: ScenePlanSourceSummary,
) -> dict[str, str]:
    """安全加载项目上下文

    不会抛出异常，缺失文件在 source_summary 中标记为未使用
    """
    context = {}

    # 1. 加载目标场景正文
    try:
        target_content, _, _ = await file_service.read_file(
            f"{project_id}/{target_file}"
        )
        context["target_file"] = target_content
        source_summary.target_file = target_file
    except Exception as e:
        logger.debug(f"无法读取目标文件: {e}")
        pass

    # 2. 加载 story_state（如果存在）
    try:
        story_state_content, _, _ = await file_service.read_file(
            f"{project_id}/story_state.md"
        )
        context["story_state"] = story_state_content
        source_summary.used_story_state = True
    except Exception as e:
        logger.debug(f"无法读取 story_state: {e}")
        pass

    # 3. 加载 style_guide（如果存在）
    try:
        style_guide_content, _, _ = await file_service.read_file(
            f"{project_id}/style_guide.md"
        )
        context["style_guide"] = style_guide_content
        source_summary.used_style_guide = True
    except Exception as e:
        logger.debug(f"无法读取 style_guide: {e}")
        pass

    # 4. 加载 recent_context（如果存在）
    try:
        recent_context_content, _, _ = await file_service.read_file(
            f"{project_id}/recent_context.md"
        )
        context["recent_context"] = recent_context_content
        source_summary.used_recent_context = True
    except Exception as e:
        logger.debug(f"无法读取 recent_context: {e}")
        pass

    return context


def _build_scene_plan_prompt(
    project_id: str,
    target_file: str,
    context: dict[str, str],
    instruction: str | None,
) -> str:
    """构建 Scene Plan 生成 Prompt

    要求：
    - 只输出 JSON
    - 不要 Markdown
    - 不要解释
    - candidate_policy 必须符合安全规则
    """
    prompt_parts = [
        "请根据以下信息为该场景生成一个 Scene Plan JSON。",
        "",
        "【要求】",
        "1. 只输出严格的 JSON，不要任何 Markdown、代码块标记或自然语言解释",
        "2. 必须包含以下字段：project_id, source_path, title, goal, conflict, required_beats, output_intent, candidate_policy",
        "3. candidate_policy 必须严格为：{\"require_candidate\": true, \"allow_direct_write\": false}",
        "4. output_intent 建议为 \"polish\" 或 \"rewrite\"",
        "5. required_beats 至少包含 1 条情节节拍",
        "6. 不要写任何正文内容，只做结构化规划",
        "7. 不要生成任何 candidate 相关的文件",
        "",
        f"【项目 ID】{project_id}",
        f"【源场景】{target_file}",
    ]

    if "target_file" in context:
        prompt_parts.append("")
        prompt_parts.append("【当前场景正文】")
        prompt_parts.append(context["target_file"])

    if "story_state" in context:
        prompt_parts.append("")
        prompt_parts.append("【故事状态】")
        prompt_parts.append(context["story_state"])

    if "style_guide" in context:
        prompt_parts.append("")
        prompt_parts.append("【风格指南】")
        prompt_parts.append(context["style_guide"])

    if "recent_context" in context:
        prompt_parts.append("")
        prompt_parts.append("【最近上下文】")
        prompt_parts.append(context["recent_context"])

    if instruction:
        prompt_parts.append("")
        prompt_parts.append("【用户指令】")
        prompt_parts.append(instruction)

    prompt_parts.append("")
    prompt_parts.append("【JSON 输出】")

    return "\n".join(prompt_parts)


def _map_target_file_to_scene_plan_path(target_file: str) -> str:
    r"""将 target_file 映射为 Scene Plan 文件路径

    规则：
    - 保存路径固定在 materials/scene_plans/
    - 将路径中的 / 和 \ 替换为 __
    - 去掉 .md 后缀
    - 清理危险字符（包括 .. 和 .）
    - 后缀固定为 .scene-plan.json

    例如：
    chapters/vol-01/ch-001/sec-001.md
    -> materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json
    """
    # 替换路径分隔符为双下划线
    safe_name = target_file.replace("/", "__").replace("\\", "__")
    # 去掉 .md 后缀
    if safe_name.endswith(".md"):
        safe_name = safe_name[:-3]
    # 清理危险字符（.. 和其他）
    safe_name = safe_name.replace("..", "_").replace(".", "_")
    return f"materials/scene_plans/{safe_name}.scene-plan.json"


# ─── 路由 ────────────────────────────────────────────────────────────

@router.post("/validate", response_model=ApiResponse[ScenePlanValidateResponse])
async def validate_scene_plan_api(
    scene_plan_data: ScenePlan | dict[str, Any],
) -> ApiResponse[ScenePlanValidateResponse]:
    """校验 Scene Plan

    不调用 LLM，不写文件，不创建 candidate，只做纯数据校验。

    Args:
        scene_plan_data: ScenePlan 对象或字典

    Returns:
        校验结果，包含 valid、errors、warnings
    """
    logger.debug("Scene Plan 校验请求")

    # 调用校验器
    result = validate_scene_plan(scene_plan_data)

    # 转换结果格式
    errors = [
        ScenePlanValidationErrorDetail(field=e.field, message=e.message)
        for e in result.errors
    ]
    warnings = [
        ScenePlanValidationWarningDetail(field=w.field, message=w.message)
        for w in result.warnings
    ]

    response = ScenePlanValidateResponse(
        valid=result.valid,
        errors=errors,
        warnings=warnings,
    )

    logger.debug("Scene Plan 校验完成: valid=%s, errors=%d, warnings=%d",
                 result.valid, len(errors), len(warnings))

    return ApiResponse.ok(response)


@router.post("/save", response_model=ApiResponse[ScenePlanSaveResponse])
async def save_scene_plan_api(
    request: ScenePlanSaveRequest,
) -> ApiResponse[ScenePlanSaveResponse]:
    """保存 Scene Plan 到文件

    保存路径固定在 materials/scene_plans/。
    保存前会调用 validate_scene_plan() 进行校验。
    invalid Scene Plan 默认不会保存（除非设置 save_invalid=true，本阶段不支持）。

    Args:
        request: ScenePlanSaveRequest

    Returns:
        ScenePlanSaveResponse
    """
    logger.debug("Scene Plan 保存请求: project_id=%s, target_file=%s",
               request.project_id, request.target_file)

    settings = get_settings()
    file_service = FileService(
        settings.projects_path,
        max_file_write_size=settings.max_file_write_size,
    )

    # 1. 安全检查：验证 target_file 路径
    try:
        file_service.validate_path(f"{request.project_id}/{request.target_file}")
    except Exception as e:
        logger.warning("目标文件路径危险: %s", e)
        return ApiResponse.ok(
            ScenePlanSaveResponse(
                saved=False,
                path=None,
                valid=False,
                errors=[
                    ScenePlanValidationErrorDetail(
                        field="target_file",
                        message=f"目标文件路径无效: {e}",
                    )
                ],
                warnings=[],
                conflict=False,
                message="路径验证失败",
            )
        )

    # 2. 将 scene_plan 转为 dict
    if isinstance(request.scene_plan, ScenePlan):
        scene_plan_dict = request.scene_plan.model_dump()
    else:
        scene_plan_dict = dict(request.scene_plan)

    # 3. 校验 Scene Plan
    validation_result = validate_scene_plan(scene_plan_dict)
    valid = validation_result.valid

    errors = [
        ScenePlanValidationErrorDetail(field=e.field, message=e.message)
        for e in validation_result.errors
    ]
    warnings = [
        ScenePlanValidationWarningDetail(field=w.field, message=w.message)
        for w in validation_result.warnings
    ]

    # 4. 如果校验失败，默认不保存
    if not valid:
        logger.warning("Scene Plan 校验失败，不保存: errors=%s", errors)
        return ApiResponse.ok(
            ScenePlanSaveResponse(
                saved=False,
                path=None,
                valid=False,
                errors=errors,
                warnings=warnings,
                conflict=False,
                message="校验失败，未保存",
            )
        )

    # 5. 生成 Scene Plan 文件路径
    scene_plan_relative_path = _map_target_file_to_scene_plan_path(request.target_file)
    full_path = f"{request.project_id}/{scene_plan_relative_path}"

    # 6. 检查文件是否已存在
    try:
        existing_content, existing_meta, _ = await file_service.read_file(full_path)
        file_exists = True
    except Exception:
        file_exists = False

    # 7. 如果文件已存在且不允许覆盖
    if file_exists and not request.overwrite:
        logger.warning("Scene Plan 文件已存在，禁止覆盖: %s", full_path)
        return ApiResponse.ok(
            ScenePlanSaveResponse(
                saved=False,
                path=scene_plan_relative_path,
                valid=True,
                errors=[],
                warnings=warnings,
                conflict=True,
                message="文件已存在，请设置 overwrite=true 覆盖",
            )
        )

    # 8. 保存文件（格式化 JSON）
    try:
        json_content = json.dumps(scene_plan_dict, ensure_ascii=False, indent=2)
        await file_service.write_file(
            path=full_path,
            content=json_content,
            encoding="utf-8",
        )
        logger.info("Scene Plan 保存成功: %s", full_path)

        return ApiResponse.ok(
            ScenePlanSaveResponse(
                saved=True,
                path=scene_plan_relative_path,
                valid=True,
                errors=[],
                warnings=warnings,
                conflict=False,
                message="保存成功",
            )
        )

    except Exception as e:
        logger.error("Scene Plan 保存失败: %s", e, exc_info=True)
        return ApiResponse.ok(
            ScenePlanSaveResponse(
                saved=False,
                path=None,
                valid=True,
                errors=[
                    ScenePlanValidationErrorDetail(
                        field="__root__",
                        message=f"保存失败: {e}",
                    )
                ],
                warnings=warnings,
                conflict=False,
                message="保存失败",
            )
        )


@router.get("/load", response_model=ApiResponse[ScenePlanLoadResponse])
async def load_scene_plan_api(
    project_id: str,
    target_file: str,
) -> ApiResponse[ScenePlanLoadResponse]:
    """从文件加载 Scene Plan

    加载路径固定在 materials/scene_plans/。

    Args:
        project_id: 项目 ID
        target_file: 目标场景文件路径

    Returns:
        ScenePlanLoadResponse
    """
    logger.debug("Scene Plan 加载请求: project_id=%s, target_file=%s",
               project_id, target_file)

    settings = get_settings()
    file_service = FileService(
        settings.projects_path,
        max_file_write_size=settings.max_file_write_size,
    )

    # 1. 安全检查：验证 target_file 路径
    try:
        file_service.validate_path(f"{project_id}/{target_file}")
    except Exception as e:
        logger.warning("目标文件路径危险: %s", e)
        return ApiResponse.ok(
            ScenePlanLoadResponse(
                exists=False,
                path=None,
                scene_plan=None,
                mtime=None,
                errors=[
                    ScenePlanValidationErrorDetail(
                        field="target_file",
                        message=f"目标文件路径无效: {e}",
                    )
                ],
            )
        )

    # 2. 生成 Scene Plan 文件路径
    scene_plan_relative_path = _map_target_file_to_scene_plan_path(target_file)
    full_path = f"{project_id}/{scene_plan_relative_path}"

    # 3. 读取文件
    try:
        content, meta, _ = await file_service.read_file(full_path)
        scene_plan_dict = json.loads(content)
        scene_plan_obj = ScenePlan(**scene_plan_dict)

        logger.debug("Scene Plan 加载成功: %s", full_path)

        return ApiResponse.ok(
            ScenePlanLoadResponse(
                exists=True,
                path=scene_plan_relative_path,
                scene_plan=scene_plan_obj,
                mtime=meta.get("mtime") if meta else None,
                errors=[],
            )
        )

    except json.JSONDecodeError as e:
        logger.warning("Scene Plan JSON 解析失败: %s", e)
        return ApiResponse.ok(
            ScenePlanLoadResponse(
                exists=True,
                path=scene_plan_relative_path,
                scene_plan=None,
                mtime=None,
                errors=[
                    ScenePlanValidationErrorDetail(
                        field="__root__",
                        message=f"JSON 解析失败: {e}",
                    )
                ],
            )
        )

    except Exception as e:
        # 文件不存在或其他错误
        logger.debug("Scene Plan 文件不存在: %s", full_path)
        return ApiResponse.ok(
            ScenePlanLoadResponse(
                exists=False,
                path=None,
                scene_plan=None,
                mtime=None,
                errors=[],
            )
        )


@router.post("/generate", response_model=ApiResponse[ScenePlanGenerateResponse])
async def generate_scene_plan_api(
    request: ScenePlanGenerateRequest,
) -> ApiResponse[ScenePlanGenerateResponse]:
    """生成 Scene Plan 草案

    调用 LLM 生成，然后用 validator 校验。
    不写正文文件，不创建 candidate，不执行 adopt，只读模式。

    Args:
        request: ScenePlanGenerateRequest

    Returns:
        ScenePlanGenerateResponse
    """
    logger.debug("Scene Plan 生成请求: project_id=%s, target_file=%s",
               request.project_id, request.target_file)

    settings = get_settings()
    file_service = FileService(
        settings.projects_path,
        max_file_write_size=settings.max_file_write_size,
    )

    # 1. 初始化源文件摘要
    source_summary = ScenePlanSourceSummary(target_file=request.target_file)

    # 2. 安全检查：使用公开的 validate_path 方法检查路径安全性
    try:
        file_service.validate_path(f"{request.project_id}/{request.target_file}")
    except Exception as e:
        logger.warning("目标文件路径危险: %s", e)
        return ApiResponse.ok(
            ScenePlanGenerateResponse(
            scene_plan=None,
            valid=False,
            errors=[
                ScenePlanValidationErrorDetail(
                    field="target_file",
                    message=f"目标文件路径无效: {e}",
                )
            ],
            warnings=[],
            source_summary=source_summary,
        )
    )

    # 3. 加载上下文
    context = await _load_project_context(
        project_id=request.project_id,
        target_file=request.target_file,
        file_service=file_service,
        source_summary=source_summary,
    )

    # 4. 构建 prompt
    prompt = _build_scene_plan_prompt(
        project_id=request.project_id,
        target_file=request.target_file,
        context=context,
        instruction=request.instruction,
    )

    # 5. 调用 LLM
    scene_plan_dict = None
    raw_output = ""
    errors: list[ScenePlanValidationErrorDetail] = []
    warnings: list[ScenePlanValidationWarningDetail] = []

    try:
        llm_cfg = load_llm_config_from_workspace(settings)
        llm_service = LLMService.from_workspace_config(llm_cfg)

        logger.debug("调用 LLM 生成 Scene Plan")
        raw_output = await llm_service.generate(
            prompt=prompt,
            model=llm_cfg.model,
            temperature=0.3,
        )
        logger.debug("LLM 返回: %s", raw_output[:200])

        # 6. 解析 JSON
        json_str = _extract_json_from_output(raw_output)
        try:
            scene_plan_dict = json.loads(json_str)
            logger.debug("JSON 解析成功")
        except json.JSONDecodeError as e:
            logger.warning("JSON 解析失败: %s", e)
            errors.append(
                ScenePlanValidationErrorDetail(
                    field="__root__",
                    message=f"LLM 输出无法解析为 JSON: {e}",
                )
            )

        # 7. 如果解析成功，强制设置必要字段
        if scene_plan_dict:
            # 确保 project_id 正确
            scene_plan_dict["project_id"] = request.project_id
            scene_plan_dict["source_path"] = request.target_file
            # 确保 metadata.created_by 为 LLM
            if "metadata" not in scene_plan_dict:
                scene_plan_dict["metadata"] = {}
            scene_plan_dict["metadata"]["created_by"] = "llm"
            # 确保 candidate_policy 安全
            if "candidate_policy" not in scene_plan_dict:
                scene_plan_dict["candidate_policy"] = {}
            scene_plan_dict["candidate_policy"]["require_candidate"] = True
            scene_plan_dict["candidate_policy"]["allow_direct_write"] = False

    except Exception as e:
        logger.error("LLM 调用失败: %s", e, exc_info=True)
        errors.append(
            ScenePlanValidationErrorDetail(
                field="__root__",
                message=f"LLM 调用失败: {e}",
            )
        )

    # 8. 校验 Scene Plan
    valid = False
    scene_plan_obj = None

    if scene_plan_dict and len(errors) == 0:
        validation_result = validate_scene_plan(scene_plan_dict)
        valid = validation_result.valid

        if valid:
            scene_plan_obj = ScenePlan(**scene_plan_dict)

        # 转换校验结果
        errors = [
            ScenePlanValidationErrorDetail(field=e.field, message=e.message)
            for e in validation_result.errors
        ]
        warnings = [
            ScenePlanValidationWarningDetail(field=w.field, message=w.message)
            for w in validation_result.warnings
        ]

    # 9. 构建响应
    # raw_output 只在显式请求时返回，保护用户内容安全
    response = ScenePlanGenerateResponse(
        scene_plan=scene_plan_obj,
        valid=valid,
        errors=errors,
        warnings=warnings,
        raw_output=raw_output if request.include_raw_output else None,
        source_summary=source_summary,
    )

    logger.debug(
        "Scene Plan 生成完成: valid=%s, errors=%d, warnings=%d, source_summary=%s",
        valid, len(errors), len(warnings),
        {
            "target_file": source_summary.target_file,
            "used_story_state": source_summary.used_story_state,
            "used_style_guide": source_summary.used_style_guide,
            "used_recent_context": source_summary.used_recent_context,
        },
    )

    return ApiResponse.ok(response)
