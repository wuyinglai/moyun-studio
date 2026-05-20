"""墨韵 - 质量审查 API (G0112)

端点：
  POST /api/quality/review        审查单个章节
  POST /api/quality/review-batch  批量审查多个章节
"""

import logging
import uuid

from fastapi import APIRouter, Depends

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.core.quality_service import QualityService
from backend.schemas.common import ApiResponse
from backend.schemas.quality import (
    BatchReviewRequest,
    BatchReviewResponse,
    QualityReviewResult,
    ReviewItem,
    ReviewRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quality"])


class ReviewResponse:
    review_id: str
    target_file: str
    result: QualityReviewResult

    def __init__(self, review_id: str, target_file: str, result: QualityReviewResult):
        self.review_id = review_id
        self.target_file = target_file
        self.result = result


# ─── 路由 ──────────────────────────────────────────────────────────────

@router.post("/quality/review")
async def review_chapter(
    req: ReviewRequest,
    settings: Settings = Depends(get_settings),
):
    """审查单个章节的质量"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    target_path = project_dir / req.target_file
    if not target_path.exists():
        raise ResourceNotFoundError(resource="file", identifier=req.target_file)

    svc = QualityService(settings)
    review_id = str(uuid.uuid4())[:8]
    result = await svc.perform_review(req.project_id, req.target_file, req.chapter_title)

    svc.save_review_result(req.project_id, req.target_file, review_id, result)

    logger.info("质量审查完成: %s", req.target_file)

    return ApiResponse.ok({
        "review_id": review_id,
        "target_file": req.target_file,
        "result": result.model_dump(),
    })


@router.post("/quality/review-batch")
async def review_chapters_batch(
    req: BatchReviewRequest,
    settings: Settings = Depends(get_settings),
):
    """批量审查多个章节的质量"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    svc = QualityService(settings)
    reviews: list[ReviewItem] = []
    succeeded = 0
    failed = 0

    for target_file in req.target_files:
        try:
            target_path = project_dir / target_file
            if not target_path.exists():
                reviews.append(ReviewItem(
                    target_file=target_file,
                    status="error",
                    error=f"文件不存在: {target_file}",
                ))
                failed += 1
                continue

            result = await svc.perform_review(req.project_id, target_file, None)

            review_id = str(uuid.uuid4())[:8]
            svc.save_review_result(req.project_id, target_file, review_id, result)

            reviews.append(ReviewItem(
                target_file=target_file,
                status="success",
                result=result,
            ))
            succeeded += 1

        except Exception as e:
            logger.error("批量审查失败: %s - %s", target_file, str(e))
            reviews.append(ReviewItem(
                target_file=target_file,
                status="error",
                error=str(e),
            ))
            failed += 1

    return ApiResponse.ok(BatchReviewResponse(
        reviews=reviews,
        total=len(req.target_files),
        succeeded=succeeded,
        failed=failed,
    ))


@router.get("/quality/reviews/{project_id}")
async def list_reviews(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取项目的所有审查历史"""
    svc = QualityService(settings)
    items = svc.list_reviews(project_id)
    return ApiResponse.ok({"reviews": items, "total": len(items)})
