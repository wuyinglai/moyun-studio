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

from backend.core.exceptions import MoyunFileNotFoundError
from backend.core.file_ops import FileService
from backend.schemas.candidate import (
    CandidateAction,
    CandidateInfo,
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
        full_source_path = self._project_path(project_id, source_path)
        try:
            source_content, _, mtime = await self.file_service.read_file(full_source_path)
            base_hash = self._compute_hash(source_content)
            base_mtime = mtime
        except Exception:
            logger.debug("读取源文件失败，跳过 base_hash 记录", exc_info=True)

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
            word_count=len(content),
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
        )

        metadata = await self._load_metadata(project_id)
        metadata[candidate_id] = candidate_info.model_dump(mode="json")
        await self._save_metadata(project_id, metadata)

        return candidate_info

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
