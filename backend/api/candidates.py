"""墨韵 - 候选稿 API 路由"""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from backend.config import get_settings
from backend.core.candidate_service import CandidateService, AdoptResult
from backend.core.exceptions import FileConflictError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.domain.events import make_candidate_adopted_event, make_candidate_created_event
from backend.schemas.candidate import (
    AdoptCandidateResponse,
    CandidateDetailResponse,
    CandidateInfo,
    CandidateListResponse,
    CandidateStatus,
    CreateCandidateRequest,
    CandidateRevisionRequest,
    DeleteCandidateResponse,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])

ALLOWED_REVISION_SCOPES = {"full_candidate", "keep_opening", "ending_only"}
ALLOWED_QUICK_ACTIONS = {
    "fix_missing_beats",
    "preserve_mystery",
    "avoid_new_entities",
    "keep_style",
    "increase_conflict",
    "reduce_exposition",
    "enhance_imagery",
    "补上缺失信息点",
    "不要新增人物",
    "保持原文风格",
    "加强冲突",
    "减少解释",
}


def _load_revision_prompt(settings) -> str:
    relative = "pipeline/candidate-feedback/revise.md"
    user_path = settings.prompts_path / relative
    system_path = settings.system_prompts_path / relative if settings.system_prompts_path else None
    if user_path.exists():
        return user_path.read_text(encoding="utf-8")
    if system_path and system_path.exists():
        return system_path.read_text(encoding="utf-8")
    raise HTTPException(status_code=500, detail="candidate feedback revision prompt missing")


@router.get("/{project_id}", response_model=CandidateListResponse)
async def list_candidates(
    project_id: str,
    status: CandidateStatus | None = None,
):
    """列出候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)

    candidates = await candidate_service.list_candidates(project_id, status)
    return CandidateListResponse(candidates=candidates)


@router.get("/{project_id}/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    project_id: str,
    candidate_id: str,
):
    """获取候选稿详情"""
    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)

    candidate = await candidate_service.get_candidate(project_id, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选稿不存在")

    content = await candidate_service.get_candidate_content(project_id, candidate_id)
    if content is None:
        raise HTTPException(status_code=404, detail="候选稿内容不存在")

    return CandidateDetailResponse(candidate=candidate, content=content)


@router.post("/{project_id}", response_model=CandidateInfo)
async def create_candidate(
    project_id: str,
    request: CreateCandidateRequest,
    http_request: Request,
):
    """创建候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)

    candidate = await candidate_service.create_candidate(
        project_id=project_id,
        source_path=request.source_path,
        action=request.action,
        content=request.content,
        workflow_run_id=request.workflow_run_id,
        model=request.model,
        pipeline_id=request.pipeline_id,
        prompt_version=request.prompt_version,
        source_mode=request.source_mode,
        continuity=request.continuity,
        source_type=request.source_type,
        warning_message=request.warning_message,
        generation_context=request.generation_context,
        scene_plan_hash=request.scene_plan_hash,
        scene_plan_path=request.scene_plan_path,
        beat_validation=request.beat_validation,
        parent_candidate_id=request.parent_candidate_id,
        revision_group_id=request.revision_group_id,
        revision_index=request.revision_index,
    )
    event_bus = getattr(http_request.app.state, "event_bus", None)
    if event_bus:
        evt = make_candidate_created_event(
            project_id=project_id,
            candidate_id=candidate.id,
            source_path=candidate.source_path,
            action=candidate.action,
            source="api/candidates",
        )
        await event_bus.publish(evt.type, evt.to_sse_dict())
    return candidate


@router.post("/{project_id}/{candidate_id}/revise", response_model=CandidateInfo)
async def revise_candidate(
    project_id: str,
    candidate_id: str,
    body: CandidateRevisionRequest,
    request: Request,
):
    """Create a child revision candidate from user feedback."""
    feedback_text = (body.feedback_text or "").strip()
    quick_actions = [str(action).strip() for action in body.quick_actions if str(action).strip()]
    if not feedback_text and not quick_actions:
        raise HTTPException(status_code=400, detail="feedback_text or quick_actions is required")
    if len(feedback_text) > 1000:
        raise HTTPException(status_code=400, detail="feedback_text is too long")
    if body.repair_scope not in ALLOWED_REVISION_SCOPES:
        raise HTTPException(status_code=400, detail="invalid repair_scope")
    invalid_actions = [action for action in quick_actions if action not in ALLOWED_QUICK_ACTIONS]
    if invalid_actions:
        raise HTTPException(status_code=400, detail=f"invalid quick_actions: {', '.join(invalid_actions)}")

    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)
    prompt_template = _load_revision_prompt(settings)
    llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)

    try:
        child = await candidate_service.create_feedback_revision_candidate(
            project_id=project_id,
            parent_candidate_id=candidate_id,
            feedback_text=feedback_text,
            quick_actions=quick_actions,
            repair_scope=body.repair_scope,
            llm_service=llm_service,
            prompt_template=prompt_template,
            inherit_required_beats=body.inherit_required_beats,
            inherit_forbidden_beats=body.inherit_forbidden_beats,
            run_beat_validation=body.run_beat_validation,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "PARENT_NOT_FOUND":
            raise HTTPException(status_code=404, detail="parent candidate not found") from exc
        if code == "PARENT_NOT_PENDING":
            raise HTTPException(status_code=409, detail="only pending candidates can be revised") from exc
        if code == "PARENT_CONTENT_NOT_FOUND":
            raise HTTPException(status_code=404, detail="parent candidate content not found") from exc
        if code == "EMPTY_REVISION_CONTENT":
            raise HTTPException(status_code=502, detail="LLM returned empty revision content") from exc
        if code == "REVISION_LLM_FAILED":
            raise HTTPException(status_code=502, detail="LLM failed while generating revision candidate") from exc
        raise

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        evt = make_candidate_created_event(
            project_id=project_id,
            candidate_id=child.id,
            source_path=child.source_path,
            action=child.action,
            source="api/candidates/revise",
        )
        await event_bus.publish(evt.type, evt.to_sse_dict())

    return child


@router.post("/{project_id}/{candidate_id}/adopt", response_model=AdoptCandidateResponse)
async def adopt_candidate(
    project_id: str,
    candidate_id: str,
    request: Request,
):
    """采用候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)

    candidate = await candidate_service.get_candidate(project_id, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选稿不存在")

    if candidate.status != CandidateStatus.PENDING:
        raise HTTPException(status_code=400, detail="候选稿状态不允许采用")

    result = await candidate_service.adopt_candidate(project_id, candidate_id)

    if result == AdoptResult.CONFLICT:
        raise FileConflictError(
            "源文件已被其他操作修改，请重新生成候选稿后再采用。",
            {"candidate_id": candidate_id, "source_path": candidate.source_path},
        )

    if result != AdoptResult.SUCCESS:
        raise HTTPException(status_code=500, detail=f"采用候选稿失败: {result}")

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        evt = make_candidate_adopted_event(
            project_id=project_id,
            candidate_id=candidate_id,
            source_path=candidate.source_path,
            source="api/candidates",
        )
        await event_bus.publish(evt.type, evt.to_sse_dict())

    return AdoptCandidateResponse(
        success=True,
        message="候选稿已成功采用",
        file_path=candidate.source_path,
    )


@router.delete("/{project_id}/{candidate_id}", response_model=DeleteCandidateResponse)
async def delete_candidate(
    project_id: str,
    candidate_id: str,
):
    """删除候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)

    candidate = await candidate_service.get_candidate(project_id, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选稿不存在")

    success = await candidate_service.delete_candidate(project_id, candidate_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除候选稿失败")

    return DeleteCandidateResponse(
        success=True,
        message="候选稿已成功删除",
    )


@router.get("/{project_id}/file/{source_path:path}", response_model=CandidateListResponse)
async def get_candidates_for_file(
    project_id: str,
    source_path: str,
):
    """获取指定文件的候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    candidate_service = CandidateService(file_service)

    candidates = await candidate_service.get_candidates_for_file(project_id, source_path)
    return CandidateListResponse(candidates=candidates)
