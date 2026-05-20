"""墨韵 - 候选稿 API 路由"""


from fastapi import APIRouter, HTTPException

from backend.config import get_settings
from backend.core.candidate_service import CandidateService, AdoptResult
from backend.core.file_ops import FileService
from backend.schemas.candidate import (
    AdoptCandidateResponse,
    CandidateDetailResponse,
    CandidateInfo,
    CandidateListResponse,
    CandidateStatus,
    CreateCandidateRequest,
    DeleteCandidateResponse,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/{project_id}", response_model=CandidateListResponse)
async def list_candidates(
    project_id: str,
    status: CandidateStatus | None = None,
):
    """列出候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path)
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
    file_service = FileService(settings.projects_path)
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
):
    """创建候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path)
    candidate_service = CandidateService(file_service)

    candidate = await candidate_service.create_candidate(
        project_id=project_id,
        source_path=request.source_path,
        action=request.action,
        content=request.content,
        workflow_run_id=request.workflow_run_id,
    )
    return candidate


@router.post("/{project_id}/{candidate_id}/adopt", response_model=AdoptCandidateResponse)
async def adopt_candidate(
    project_id: str,
    candidate_id: str,
):
    """采用候选稿"""
    settings = get_settings()
    file_service = FileService(settings.projects_path)
    candidate_service = CandidateService(file_service)

    candidate = await candidate_service.get_candidate(project_id, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选稿不存在")

    if candidate.status != CandidateStatus.PENDING:
        raise HTTPException(status_code=400, detail="候选稿状态不允许采用")

    result = await candidate_service.adopt_candidate(project_id, candidate_id)

    if result == AdoptResult.CONFLICT:
        return AdoptCandidateResponse(
            success=False,
            message="源文件已被修改，候选稿与当前文件不一致，请重新生成",
            file_path=candidate.source_path,
            conflict=True,
        )

    if result != AdoptResult.SUCCESS:
        raise HTTPException(status_code=500, detail=f"采用候选稿失败: {result}")

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
    file_service = FileService(settings.projects_path)
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
    file_service = FileService(settings.projects_path)
    candidate_service = CandidateService(file_service)

    candidates = await candidate_service.get_candidates_for_file(project_id, source_path)
    return CandidateListResponse(candidates=candidates)
