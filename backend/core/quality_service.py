"""墨韵 - 质量审查服务

职责：
- 对章节执行 LLM 质量审查
- 审查结果持久化
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from backend.config import Settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.prompt_engine import PromptEngine
from backend.schemas.quality import QualityReviewResult

logger = logging.getLogger(__name__)


class QualityService:
    """质量审查服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.file_service = FileService(
            settings.projects_path,
            max_file_write_size=settings.max_file_write_size,
        )

    # ─── 路径辅助 ────────────────────────────────────────

    def _get_reviews_dir(self, project_dir: Path) -> Path:
        path = project_dir / "materials" / "reviews"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save_review(self, project_dir: Path, review_id: str, target_file: str, result: QualityReviewResult) -> None:
        reviews_dir = self._get_reviews_dir(project_dir)
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

    async def _read_project_file(self, project_id: str, rel_path: str) -> str:
        """安全读取项目文件，不存在则返回空字符串"""
        try:
            content, _, _ = await self.file_service.read_file(f"{project_id}/{rel_path}")
            return content
        except Exception:
            return ""

    # ─── 审查逻辑 ────────────────────────────────────────

    async def perform_review(
        self,
        project_id: str,
        target_file: str,
        chapter_title: str | None,
    ) -> QualityReviewResult:
        """对单个章节执行 LLM 质量审查"""
        project_dir = self.settings.projects_path / project_id

        # 读取目标章节内容
        content = await self._read_project_file(project_id, target_file)
        if not content:
            raise ResourceNotFoundError(resource="file", identifier=target_file)

        # 读取辅助上下文
        story_state = await self._read_project_file(project_id, "story-state.md")
        style_guide = await self._read_project_file(project_id, "style-guide.md")

        # 读取角色档案（合并所有角色文件）
        characters_dir = project_dir / "characters"
        characters_text = ""
        if await asyncio.to_thread(characters_dir.exists):
            char_files = await asyncio.to_thread(
                lambda: sorted(characters_dir.glob("*.json"))
            )
            parts: list[str] = []
            for f in char_files:
                try:
                    parts.append(await asyncio.to_thread(f.read_text, encoding="utf-8"))
                except Exception:
                    logger.debug("读取审查结果失败", exc_info=True)
            if parts:
                characters_text = "\n---\n".join(parts)

        # 渲染审查 prompt
        prompt_engine = PromptEngine(self.settings.prompts_path, self.file_service)
        variables = {
            "content": content,  # AI_GUARDRAIL_ALLOW: prompt variable, not SSE
            "chapter_title": chapter_title or Path(target_file).stem,
            "story_state": story_state,
            "style_guide": style_guide,
            "characters": characters_text,
        }
        prompt_text = await prompt_engine.render("review/quality", variables)

        # 调用 LLM（审查使用较低温度以求精准）
        llm_cfg = load_llm_config_from_workspace(self.settings)
        svc = LLMService.from_workspace_config(llm_cfg)

        logger.info("质量审查中", extra={
            "target": target_file,
            "text_length": len(content),
        })

        raw = await svc.complete_sync(
            [{"role": "user", "content": prompt_text}],
            temperature=0.2,
            max_tokens=16000,
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
            return QualityReviewResult(
                summary=raw[:500] if raw else "审查失败：LLM 返回格式异常",
                issues=[],
            )

    def save_review_result(self, project_id: str, target_file: str, review_id: str, result: QualityReviewResult):
        """保存审查结果"""
        project_dir = self.settings.projects_path / project_id
        self._save_review(project_dir, review_id, target_file, result)

    def list_reviews(self, project_id: str) -> list[dict]:
        """获取项目的所有审查历史"""
        project_dir = self.settings.projects_path / project_id
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        reviews_dir = self._get_reviews_dir(project_dir)
        if not reviews_dir.exists():
            return []

        items: list[dict] = []
        for f in sorted(reviews_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items.append(data)
            except Exception as e:
                logger.warning("读取审查记录失败: %s - %s", f.name, str(e))
        return items
