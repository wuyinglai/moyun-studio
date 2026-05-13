"""墨韵 - 质量审查 API (G0112)

端点：
  POST /api/quality/review        审查单个章节
  POST /api/quality/review-batch  批量审查多个章节
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.prompt_engine import PromptEngine
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


class ReviewResponse(BaseModel):
    """审查响应"""
    review_id: str
    target_file: str
    result: QualityReviewResult


# ─── 工具函数 ──────────────────────────────────────────────────────────

def _get_reviews_dir(project_dir: Path) -> Path:
    """获取审查结果存储目录"""
    path = project_dir / "materials" / "reviews"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_review(project_dir: Path, review_id: str, target_file: str, result: QualityReviewResult) -> None:
    """保存审查结果到文件"""
    reviews_dir = _get_reviews_dir(project_dir)
    safe_name = target_file.replace("/", "_").replace("\\", "_")
    file_path = reviews_dir / f"{safe_name}.{review_id}.json"
    file_path.write_text(
        json.dumps({
            "review_id": review_id,
            "target_file": target_file,
            "result": result.model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _read_project_file(file_service: FileService, project_id: str, rel_path: str) -> str:
    """安全读取项目文件，不存在则返回空字符串"""
    try:
        content, _ = await file_service.read_file(f"{project_id}/{rel_path}")
        return content
    except Exception:
        return ""


async def _perform_review(
    project_id: str,
    target_file: str,
    chapter_title: str | None,
    settings: Settings,
) -> QualityReviewResult:
    """对单个章节执行 LLM 质量审查"""
    file_service = FileService(settings.projects_path)
    project_dir = settings.projects_path / project_id

    # 读取目标章节内容
    content = await _read_project_file(file_service, project_id, target_file)
    if not content:
        raise ResourceNotFoundError(resource="file", identifier=target_file)

    # 读取辅助上下文
    story_state = await _read_project_file(file_service, project_id, "story-state.md")
    style_guide = await _read_project_file(file_service, project_id, "style-guide.md")

    # 读取角色档案（合并所有角色文件）
    characters_dir = project_dir / "characters"
    characters_text = ""
    if characters_dir.exists():
        parts: list[str] = []
        for f in sorted(characters_dir.glob("*.json")):
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except Exception:
                pass
        if parts:
            characters_text = "\n---\n".join(parts)

    # 渲染审查 prompt
    prompt_engine = PromptEngine(settings.prompts_path, file_service)
    variables = {
        "content": content,
        "chapter_title": chapter_title or Path(target_file).stem,
        "story_state": story_state,
        "style_guide": style_guide,
        "characters": characters_text,
    }
    prompt_text = await prompt_engine.render("review/quality", variables)

    # 调用 LLM（审查使用较低温度以求精准）
    llm_cfg = load_llm_config_from_workspace(settings)
    svc = LLMService.from_workspace_config(llm_cfg)

    logger.info("质量审查中", extra={
        "target": target_file,
        "text_length": len(content),
    })

    raw = await svc.complete_sync(
        [{"role": "user", "content": prompt_text}],
        temperature=0.2,
        max_tokens=4000,
        timeout=180,
    )
    raw = raw.strip()

    # 提取 JSON（LLM 可能用 ```json 包裹）
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(raw)
        return QualityReviewResult(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("LLM 返回格式异常，尝试直接解析", extra={"raw": raw[:200], "error": str(e)})
        # 兜底：返回原始文本作为摘要
        return QualityReviewResult(
            summary=raw[:500] if raw else "审查失败：LLM 返回格式异常",
            issues=[],
        )


# ─── 路由 ──────────────────────────────────────────────────────────────

@router.post("/quality/review")
async def review_chapter(
    req: ReviewRequest,
    settings: Settings = Depends(get_settings),
):
    """审查单个章节的质量

    调用 LLM 对指定章节进行多维度质量评估，返回评分和问题列表。
    """
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    target_path = project_dir / req.target_file
    if not target_path.exists():
        raise ResourceNotFoundError(resource="file", identifier=req.target_file)

    review_id = str(uuid.uuid4())[:8]
    result = await _perform_review(
        req.project_id,
        req.target_file,
        req.chapter_title,
        settings,
    )

    # 保存结果
    _save_review(project_dir, review_id, req.target_file, result)

    logger.info("质量审查完成: %s, 总分: %d/%d",
                req.target_file,
                sum(v for v in result.scores.model_dump().values()),
                60)

    return ApiResponse.ok(ReviewResponse(
        review_id=review_id,
        target_file=req.target_file,
        result=result,
    ))


@router.post("/quality/review-batch")
async def review_chapters_batch(
    req: BatchReviewRequest,
    settings: Settings = Depends(get_settings),
):
    """批量审查多个章节的质量

    最多同时审查 20 个章节。
    """
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

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

            result = await _perform_review(
                req.project_id,
                target_file,
                None,
                settings,
            )

            review_id = str(uuid.uuid4())[:8]
            _save_review(project_dir, review_id, target_file, result)

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
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    reviews_dir = _get_reviews_dir(project_dir)
    if not reviews_dir.exists():
        return ApiResponse.ok({"reviews": [], "total": 0})

    items: list[dict] = []
    for f in sorted(reviews_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append(data)
        except Exception as e:
            logger.warning("读取审查记录失败: %s - %s", f.name, str(e))

    return ApiResponse.ok({"reviews": items, "total": len(items)})
