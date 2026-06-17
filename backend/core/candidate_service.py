"""墨韵 - 候选稿服务

管理候选稿的创建、查询、采用和删除操作。
候选稿作为安全修改事务处理：创建时记录 base_hash/base_mtime，采用时校验一致性。
"""

from datetime import datetime
import asyncio
import difflib
import hashlib
import json
import logging
import re
import uuid

from jinja2 import Environment, FileSystemLoader

from backend.core.beat_validator import RequiredBeatValidator
from backend.core.continuity_anchor_service import ContinuityAnchorService
from backend.core.exceptions import MoyunFileNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService
from backend.schemas.candidate import (
    CandidateAction,
    CandidateInfo,
    CandidateQuality,
    CandidateQualityMetadata,
    CandidateStatus,
)

logger = logging.getLogger(__name__)


class AdoptResult:
    """采用候选稿的结果"""
    SUCCESS = "success"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    NOT_PENDING = "not_pending"
    NO_CONTENT = "no_content"


class CandidateService:
    """候选稿服务"""

    CANDIDATES_DIR = ".candidates"
    METADATA_FILE = "metadata.json"

    def __init__(self, file_service: FileService):
        self.file_service = file_service

    def _project_path(self, project_id: str, path: str) -> str:
        return f"{project_id}/{path}".replace("\\", "/").strip("/")

    def _get_candidates_dir(self, project_id: str) -> str:
        """获取候选稿目录路径"""
        return self._project_path(project_id, self.CANDIDATES_DIR)

    def _get_metadata_path(self, project_id: str) -> str:
        """获取元数据文件路径"""
        return self._project_path(project_id, f"{self.CANDIDATES_DIR}/{self.METADATA_FILE}")

    async def _ensure_candidates_dir(self, project_id: str) -> None:
        """确保候选稿目录存在"""
        await asyncio.to_thread(self.file_service._resolve_path(self._get_candidates_dir(project_id)).mkdir, parents=True, exist_ok=True)

    async def _load_metadata(self, project_id: str) -> dict:
        """加载候选稿元数据"""
        metadata_path = self._get_metadata_path(project_id)
        try:
            content, _, _ = await self.file_service.read_file(metadata_path)
            return json.loads(content)
        except (MoyunFileNotFoundError, FileNotFoundError):
            return {}

    async def _save_metadata(self, project_id: str, metadata: dict) -> None:
        """保存候选稿元数据"""
        await self._ensure_candidates_dir(project_id)
        metadata_path = self._get_metadata_path(project_id)
        await self.file_service.write_file(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))

    async def generate_candidate_id(self, project_id: str) -> str:
        """生成唯一的候选稿ID"""
        metadata = await self._load_metadata(project_id)
        while True:
            candidate_id = f"cand_{uuid.uuid4().hex[:8]}"
            if candidate_id not in metadata:
                return candidate_id

    async def _build_candidate_path(self, project_id: str, candidate_id: str, action: CandidateAction) -> str:
        """构建候选稿文件路径"""
        return self._project_path(project_id, f"{self.CANDIDATES_DIR}/{candidate_id}.{action.value}.md")

    @staticmethod
    def _compute_hash(content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_word_count(text: str) -> int:
        """计算中文字数和英文单词数"""
        cn = len(re.findall(r'[一-鿿]', text))
        en = len(re.findall(r'[a-zA-Z]+', text))
        return cn + en

    @classmethod
    def generate_quality_metadata(
        cls,
        action: CandidateAction,
        beat_validation: dict | None,
        continuity_anchors: dict | None,
        source_word_count: int,
        candidate_word_count: int,
    ) -> CandidateQualityMetadata:
        """生成5个维度的quality metadata（规则计算，不用LLM）"""
        # 1. instruction_following: 基于 beat_validation.status
        bv = beat_validation or {}
        bv_status = bv.get("status", "unknown")
        if bv_status == "pass":
            instruction_following = CandidateQuality.PASS
        elif bv_status == "warning":
            instruction_following = CandidateQuality.WARNING
        else:
            instruction_following = CandidateQuality.UNKNOWN

        # 2. continuity: 基于 continuity_anchors.used_count > 0
        ca = continuity_anchors or {}
        used_count = ca.get("used_count", 0)
        if used_count > 0:
            continuity = CandidateQuality.PASS
        else:
            continuity = CandidateQuality.UNKNOWN

        # 3. style_preservation: polish → pass, 其他 → unknown
        if action == CandidateAction.POLISH:
            style_preservation = CandidateQuality.PASS
        else:
            style_preservation = CandidateQuality.UNKNOWN

        # 4. change_scope: 基于长度变化
        if source_word_count > 0 and candidate_word_count > 0:
            delta = abs(candidate_word_count - source_word_count) / source_word_count
            if delta < 0.10:
                change_scope = CandidateQuality.SMALL
            elif delta <= 0.40:
                change_scope = CandidateQuality.MEDIUM
            else:
                change_scope = CandidateQuality.LARGE
        else:
            change_scope = CandidateQuality.UNKNOWN

        # 5. forbidden_check: 基于 beat_validation 是否有 forbidden violation
        forbidden_beats = bv.get("forbidden_beats") or []
        has_forbidden_warning = False
        if isinstance(forbidden_beats, list):
            has_forbidden_warning = any(
                item.get("violated") is not False
                for item in forbidden_beats
            )
        if has_forbidden_warning:
            forbidden_check = CandidateQuality.WARNING
        else:
            forbidden_check = CandidateQuality.PASS

        return CandidateQualityMetadata(
            instruction_following=instruction_following,
            continuity=continuity,
            style_preservation=style_preservation,
            change_scope=change_scope,
            forbidden_check=forbidden_check,
            notes=[],
        )

    # ─── 创建候选稿 ──────────────────────────────────────

    async def create_candidate(
        self,
        project_id: str,
        source_path: str,
        action: CandidateAction,
        content: str,
        workflow_run_id: str | None = None,
        model: str | None = None,
        pipeline_id: str | None = None,
        prompt_version: str | None = None,
        source_mode: str | None = None,
        continuity: dict | None = None,
        source_type: str | None = None,
        warning_message: str | None = None,
        generation_context: dict | None = None,
        scene_plan_hash: str = "",
        scene_plan_path: str = "",
        beat_validation: dict | None = None,
        continuity_anchors: dict | None = None,
        parent_candidate_id: str | None = None,
        revision_group_id: str | None = None,
        revision_index: int = 0,
    ) -> CandidateInfo:
        """创建候选稿

        1. 读取源文件，记录 base_hash 和 base_mtime
        2. 保存候选正文
        3. 保存 metadata

        source_path 永远是项目内相对路径，不带 project_id。
        """
        await self._ensure_candidates_dir(project_id)

        candidate_id = await self.generate_candidate_id(project_id)
        candidate_path = await self._build_candidate_path(project_id, candidate_id, action)

        # 1. 读取源文件，记录 base_hash 和 base_mtime
        base_hash = ""
        base_mtime = None
        source_content = ""
        full_source_path = self._project_path(project_id, source_path)
        try:
            source_content, _, mtime = await self.file_service.read_file(full_source_path)
            base_hash = self._compute_hash(source_content)
            base_mtime = mtime
        except Exception:
            logger.debug("读取源文件失败，跳过 base_hash 记录", exc_info=True)

        # 生成 quality metadata
        source_word_count = self._compute_word_count(source_content)
        candidate_word_count = self._compute_word_count(content)
        quality = self.generate_quality_metadata(
            action=action,
            beat_validation=beat_validation,
            continuity_anchors=continuity_anchors,
            source_word_count=source_word_count,
            candidate_word_count=candidate_word_count,
        )

        # 2. 保存候选正文
        await self.file_service.write_file(candidate_path, content)

        # 3. 保存 metadata
        candidate_info = CandidateInfo(
            id=candidate_id,
            project_id=project_id,
            source_path=source_path,
            candidate_path=candidate_path,
            action=action,
            base_hash=base_hash,
            base_mtime=base_mtime,
            status=CandidateStatus.PENDING,
            created_at=datetime.now(),
            word_count=candidate_word_count,
            workflow_run_id=workflow_run_id,
            model=model,
            pipeline_id=pipeline_id,
            prompt_version=prompt_version,
            source_mode=source_mode,
            continuity=continuity or {},
            source_type=source_type,
            warning_message=warning_message,
            generation_context=generation_context or {},
            scene_plan_hash=scene_plan_hash,
            scene_plan_path=scene_plan_path,
            beat_validation=beat_validation or {},
            continuity_anchors=continuity_anchors or {},
            parent_candidate_id=parent_candidate_id,
            revision_group_id=revision_group_id,
            revision_index=revision_index,
            quality=quality,
        )

        metadata = await self._load_metadata(project_id)
        metadata[candidate_id] = candidate_info.model_dump(mode="json")
        await self._save_metadata(project_id, metadata)

        return candidate_info

    # ─── Feedback Revision ────────────────────────────────────────────────

    @staticmethod
    def _normalize_beat_items(value, prefix: str) -> list[dict]:
        """Normalize stored beat metadata into id/text objects."""
        if not value:
            return []
        raw_items = value if isinstance(value, list) else [value]
        result: list[dict] = []
        for index, item in enumerate(raw_items, start=1):
            text = ""
            beat_id = f"{prefix}-{index}"
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = str(item.get("text") or item.get("beat") or item.get("description") or "").strip()
                beat_id = str(item.get("id") or beat_id)
            elif item is not None:
                text = str(item).strip()
            if text:
                result.append({"id": beat_id, "text": text})
        return result

    @classmethod
    def _extract_inherited_beats(
        cls,
        parent: CandidateInfo,
        inherit_required_beats: bool = True,
        inherit_forbidden_beats: bool = True,
    ) -> tuple[list[dict], list[dict]]:
        """Extract required/forbidden beats from parent generation context first, then validator metadata."""
        generation_context = parent.generation_context or {}
        beat_validation = parent.beat_validation or {}

        required: list[dict] = []
        forbidden: list[dict] = []

        if inherit_required_beats:
            required = cls._normalize_beat_items(generation_context.get("required_beats_input"), "beat")
            if not required:
                required = cls._normalize_beat_items(generation_context.get("inherited_required_beats"), "beat")
            if not required:
                required = cls._normalize_beat_items(beat_validation.get("required_beats"), "beat")

        if inherit_forbidden_beats:
            forbidden = cls._normalize_beat_items(generation_context.get("forbidden_beats_input"), "forbid")
            if not forbidden:
                forbidden = cls._normalize_beat_items(generation_context.get("inherited_forbidden_beats"), "forbid")
            if not forbidden:
                forbidden = cls._normalize_beat_items(
                    beat_validation.get("forbidden_beats") or beat_validation.get("forbidden_violations"),
                    "forbid",
                )

        return required, forbidden

    async def _next_revision_index(self, project_id: str, revision_group_id: str) -> int:
        metadata = await self._load_metadata(project_id)
        max_index = 0
        for data in metadata.values():
            generation_context = data.get("generation_context") or {}
            if data.get("revision_group_id") != revision_group_id and generation_context.get("revision_group_id") != revision_group_id:
                continue
            raw_index = data.get("revision_index") or generation_context.get("revision_index") or 0
            try:
                max_index = max(max_index, int(raw_index))
            except (TypeError, ValueError):
                continue
        return max_index + 1

    async def create_feedback_revision_candidate(
        self,
        project_id: str,
        parent_candidate_id: str,
        feedback_text: str,
        quick_actions: list[str],
        repair_scope: str,
        llm_service: LLMService,
        prompt_template: str,
        inherit_required_beats: bool = True,
        inherit_forbidden_beats: bool = True,
        run_beat_validation: bool = True,
        prompt_search_paths: list[str] | None = None,
    ) -> CandidateInfo:
        """Create a child candidate from user feedback without changing the source scene."""
        parent = await self.get_candidate(project_id, parent_candidate_id)
        if not parent:
            raise ValueError("PARENT_NOT_FOUND")
        if parent.status != CandidateStatus.PENDING:
            raise ValueError("PARENT_NOT_PENDING")

        parent_content = await self.get_candidate_content(project_id, parent_candidate_id)
        if parent_content is None:
            raise ValueError("PARENT_CONTENT_NOT_FOUND")

        source_content = ""
        try:
            source_content, _, _ = await self.file_service.read_file(
                self._project_path(project_id, parent.source_path)
            )
        except Exception:
            logger.debug("读取 parent source failed for feedback revision", exc_info=True)

        required_beats, forbidden_beats = self._extract_inherited_beats(
            parent,
            inherit_required_beats=inherit_required_beats,
            inherit_forbidden_beats=inherit_forbidden_beats,
        )
        required_texts = [item["text"] for item in required_beats]
        forbidden_texts = [item["text"] for item in forbidden_beats]

        parent_validation = parent.beat_validation or {}
        active_anchors = await ContinuityAnchorService(self.file_service).list_active(project_id)
        continuity_anchor_items = ContinuityAnchorService.prompt_items(active_anchors)
        continuity_anchor_metadata = ContinuityAnchorService.metadata(active_anchors)
        if prompt_search_paths:
            env = Environment(loader=FileSystemLoader(prompt_search_paths), autoescape=False)
            tpl = env.from_string(prompt_template)
        else:
            from jinja2 import Template as _Template
            tpl = _Template(prompt_template)
        prompt = tpl.render(
            official_source_text=source_content,
            parent_candidate_text=parent_content,
            feedback_text=feedback_text,
            quick_actions=quick_actions,
            repair_scope=repair_scope,
            required_beats=required_beats,
            forbidden_beats=forbidden_beats,
            parent_beat_validation_summary=parent_validation.get("summary", ""),
            parent_beat_validation_status=parent_validation.get("status", ""),
            parent_beat_validation=parent_validation,
            continuity_anchor_items=continuity_anchor_items,
            source_path=parent.source_path,
        )

        try:
            revised_content = await llm_service.complete_sync(
                [
                    {
                        "role": "system",
                        "content": "你是小说候选稿修订助手。只输出完整修订后的候选稿正文，不输出解释。",
                    },
                    {"role": "user", "content": prompt},
                ],
                timeout=180,
                max_tokens=3000,
            )
        except Exception as exc:
            logger.warning("feedback revision LLM failed: %s", type(exc).__name__)
            raise ValueError("REVISION_LLM_FAILED") from exc
        revised_content = (revised_content or "").strip()
        if not revised_content:
            raise ValueError("EMPTY_REVISION_CONTENT")

        beat_validation = {}
        if run_beat_validation and (required_texts or forbidden_texts):
            validator = RequiredBeatValidator(llm_service)
            beat_validation = await validator.validate(
                revised_content,
                required_beats=required_texts,
                forbidden_beats=forbidden_texts,
            )

        revision_group_id = (
            parent.revision_group_id
            or (parent.generation_context or {}).get("revision_group_id")
            or f"revgrp_{uuid.uuid4().hex[:8]}"
        )
        revision_index = await self._next_revision_index(project_id, revision_group_id)
        generation_context = {
            "revision_type": "feedback_revision",
            "parent_candidate_id": parent_candidate_id,
            "feedback_text": feedback_text,
            "quick_actions": quick_actions,
            "repair_scope": repair_scope,
            "source_candidate_action": parent.action.value,
            "source_candidate_status_at_revision": parent.status.value,
            "source_candidate_beat_validation_status": parent_validation.get("status", ""),
            "parent_validation_summary": parent_validation,
            "inherited_required_beats": bool(required_beats),
            "inherited_forbidden_beats": bool(forbidden_beats),
            "required_beats_input": required_beats,
            "forbidden_beats_input": forbidden_beats,
            "revision_group_id": revision_group_id,
            "revision_index": revision_index,
        }
        if continuity_anchor_metadata.get("used_count", 0) > 0:
            generation_context["continuity_anchor_ids"] = continuity_anchor_metadata.get("anchor_ids", [])

        return await self.create_candidate(
            project_id=project_id,
            source_path=parent.source_path,
            action=CandidateAction.FEEDBACK_REVISION,
            content=revised_content,
            workflow_run_id=parent.workflow_run_id,
            model=getattr(getattr(llm_service, "config", None), "model", None),
            pipeline_id=parent.pipeline_id,
            prompt_version=parent.prompt_version,
            source_mode=parent.source_mode,
            continuity=parent.continuity,
            source_type="llm",
            warning_message=None,
            generation_context=generation_context,
            scene_plan_hash=parent.scene_plan_hash,
            scene_plan_path=parent.scene_plan_path,
            beat_validation=beat_validation,
            continuity_anchors=continuity_anchor_metadata,
            parent_candidate_id=parent_candidate_id,
            revision_group_id=revision_group_id,
            revision_index=revision_index,
        )

    # ─── 查询 ────────────────────────────────────────────

    async def get_candidate(self, project_id: str, candidate_id: str) -> CandidateInfo | None:
        """获取候选稿信息"""
        metadata = await self._load_metadata(project_id)
        data = metadata.get(candidate_id)
        if data:
            return CandidateInfo(**data)
        return None

    async def get_candidate_content(self, project_id: str, candidate_id: str) -> str | None:
        """获取候选稿内容"""
        candidate_info = await self.get_candidate(project_id, candidate_id)
        if not candidate_info:
            return None
        try:
            content, _, _ = await self.file_service.read_file(candidate_info.candidate_path)
            return content
        except (MoyunFileNotFoundError, FileNotFoundError):
            return None

    async def list_candidates(self, project_id: str, status: CandidateStatus | None = None) -> list[CandidateInfo]:
        """列出候选稿"""
        metadata = await self._load_metadata(project_id)
        candidates = [CandidateInfo(**data) for data in metadata.values()]

        if status:
            candidates = [c for c in candidates if c.status == status]

        # 按创建时间降序排序
        candidates.sort(key=lambda c: c.created_at, reverse=True)

        return candidates

    async def get_candidates_for_file(self, project_id: str, source_path: str) -> list[CandidateInfo]:
        """获取指定文件的候选稿"""
        metadata = await self._load_metadata(project_id)
        candidates = [
            CandidateInfo(**data)
            for data in metadata.values()
            if data.get("source_path") == source_path and data.get("status") == CandidateStatus.PENDING
        ]
        candidates.sort(key=lambda c: c.created_at, reverse=True)
        return candidates

    # ─── 采用候选稿（安全修改事务）─────────────────────────

    async def adopt_candidate(self, project_id: str, candidate_id: str) -> str:
        """采用候选稿

        1. 读取当前源文件
        2. 对比当前 hash/mtime 和 base_hash/base_mtime
        3. 如果源文件已变化，返回 conflict，不直接覆盖
        4. 如果一致，先写 revision-log
        5. 再覆盖正式文件
        6. 更新 candidate status = adopted

        Returns:
            AdoptResult 常量
        """
        candidate_info = await self.get_candidate(project_id, candidate_id)
        if not candidate_info:
            return AdoptResult.NOT_FOUND

        if candidate_info.status != CandidateStatus.PENDING:
            return AdoptResult.NOT_PENDING

        # 读取候选稿内容
        content = await self.get_candidate_content(project_id, candidate_id)
        if content is None:
            return AdoptResult.NO_CONTENT

        full_source_path = self._project_path(project_id, candidate_info.source_path)

        # 1. 读取当前源文件
        original_content = ""
        current_hash = ""
        current_mtime = None
        try:
            original_content, _, mtime = await self.file_service.read_file(full_source_path)
            current_hash = self._compute_hash(original_content)
            current_mtime = mtime
        except Exception:
            logger.debug("读取源文件失败", exc_info=True)

        # 2. 对比当前 hash/mtime 和 base_hash/base_mtime
        # base_hash 为空时无法验证源文件未变化，必须拒绝 adopt
        if not candidate_info.base_hash:
            logger.warning(
                "候选稿 base_hash 为空，无法验证源文件未变化，拒绝 adopt: candidate_id=%s",
                candidate_id,
            )
            candidate_info.status = CandidateStatus.REJECTED
            metadata = await self._load_metadata(project_id)
            metadata[candidate_id] = candidate_info.model_dump(mode="json")
            await self._save_metadata(project_id, metadata)
            return AdoptResult.CONFLICT

        if current_hash != candidate_info.base_hash:
            logger.warning(
                "候选稿冲突: candidate_id=%s, base_hash=%s, current_hash=%s",
                candidate_id, candidate_info.base_hash, current_hash,
            )
            # 更新状态为 rejected
            candidate_info.status = CandidateStatus.REJECTED
            metadata = await self._load_metadata(project_id)
            metadata[candidate_id] = candidate_info.model_dump(mode="json")
            await self._save_metadata(project_id, metadata)
            return AdoptResult.CONFLICT

        if candidate_info.base_mtime is not None and current_mtime is not None:
            if abs(current_mtime - candidate_info.base_mtime) > 0.001:
                logger.warning(
                    "候选稿 mtime 冲突: candidate_id=%s, base_mtime=%s, current_mtime=%s",
                    candidate_id, candidate_info.base_mtime, current_mtime,
                )
                candidate_info.status = CandidateStatus.REJECTED
                metadata = await self._load_metadata(project_id)
                metadata[candidate_id] = candidate_info.model_dump(mode="json")
                await self._save_metadata(project_id, metadata)
                return AdoptResult.CONFLICT

        # 4. 先写 revision-log
        await self._write_revision_log(
            project_id, candidate_id, candidate_info.source_path,
            original_content, content,
        )

        # 5. 再覆盖正式文件
        await self.file_service.write_file(full_source_path, content)

        # 6. 更新 candidate status = adopted
        candidate_info.status = CandidateStatus.ADOPTED
        candidate_info.adopted_at = datetime.now()

        metadata = await self._load_metadata(project_id)
        metadata[candidate_id] = candidate_info.model_dump(mode="json")
        await self._save_metadata(project_id, metadata)

        return AdoptResult.SUCCESS

    async def _write_revision_log(
        self,
        project_id: str,
        candidate_id: str,
        source_path: str,
        original_content: str,
        new_content: str,
    ) -> None:
        """写入 revision-log"""
        try:
            revision_id = f"rev-{uuid.uuid4().hex[:8]}"

            # 推导 revision-log 目录路径
            source_parts = source_path.split("/")
            revision_log_dir = "/".join(source_parts[:-1]) + "/revision-log"

            def _wc(text: str) -> int:
                return len(re.findall(r'[一-鿿]', text)) + len(re.findall(r'[a-zA-Z]+', text))

            revision_entry = {
                "id": revision_id,
                "candidate_id": candidate_id,
                "source_path": source_path,
                "revision_type": "candidate_adopt",
                "word_count_before": _wc(original_content),
                "word_count_after": _wc(new_content),
                "adopted_at": datetime.now().isoformat(),
            }

            # 生成 diff 摘要
            try:
                before_lines = original_content.splitlines(keepends=True)
                after_lines = new_content.splitlines(keepends=True)
                diff = "".join(difflib.unified_diff(
                    before_lines, after_lines,
                    fromfile="采用前", tofile="采用后", lineterm=""
                ))
                revision_entry["diff"] = diff
            except Exception:
                logger.debug("生成 diff 失败", exc_info=True)

            revision_log_path = f"{project_id}/{revision_log_dir}/{revision_id}.json"
            await self.file_service.write_file(
                revision_log_path,
                json.dumps(revision_entry, ensure_ascii=False, indent=2),
            )
        except Exception as e:
            logger.warning("写入 revision-log 失败: %s", e)

    # ─── 删除候选稿 ──────────────────────────────────────

    async def delete_candidate(self, project_id: str, candidate_id: str) -> bool:
        """删除候选稿"""
        candidate_info = await self.get_candidate(project_id, candidate_id)
        if not candidate_info:
            return False

        # 删除候选稿文件
        try:
            await self.file_service.delete_file(candidate_info.candidate_path)
        except (MoyunFileNotFoundError, FileNotFoundError):
            pass

        # 更新状态
        candidate_info.status = CandidateStatus.DISCARDED
        candidate_info.adopted_at = datetime.now()

        metadata = await self._load_metadata(project_id)
        metadata[candidate_id] = candidate_info.model_dump(mode="json")
        await self._save_metadata(project_id, metadata)

        return True

    # ─── 清理 ────────────────────────────────────────────

    async def cleanup_old_candidates(self, project_id: str, days_to_keep: int = 30) -> int:
        """清理过期的候选稿"""
        metadata = await self._load_metadata(project_id)
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        deleted_count = 0

        for candidate_id, data in list(metadata.items()):
            created_at = data.get("created_at")
            if created_at:
                created_timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                if created_timestamp < cutoff_time:
                    # 删除文件
                    candidate_path = data.get("candidate_path")
                    if candidate_path:
                        try:
                            await self.file_service.delete_file(candidate_path)
                        except (MoyunFileNotFoundError, FileNotFoundError):
                            pass
                    # 从元数据中移除
                    del metadata[candidate_id]
                    deleted_count += 1

        if deleted_count > 0:
            await self._save_metadata(project_id, metadata)

        return deleted_count
