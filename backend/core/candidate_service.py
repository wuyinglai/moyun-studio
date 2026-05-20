"""墨韵 - 候选稿服务

管理候选稿的创建、查询、采用和删除操作。
"""

from datetime import datetime
import json
import uuid

from backend.core.exceptions import MoyunFileNotFoundError
from backend.core.file_ops import FileService
from backend.schemas.candidate import (
    CandidateAction,
    CandidateInfo,
    CandidateStatus,
)


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
        self.file_service._resolve_path(self._get_candidates_dir(project_id)).mkdir(parents=True, exist_ok=True)

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

    async def create_candidate(
        self,
        project_id: str,
        source_path: str,
        action: CandidateAction,
        content: str,
        workflow_run_id: str | None = None,
    ) -> CandidateInfo:
        """创建候选稿"""
        await self._ensure_candidates_dir(project_id)

        candidate_id = await self.generate_candidate_id(project_id)
        candidate_path = await self._build_candidate_path(project_id, candidate_id, action)

        # 写入候选稿内容
        await self.file_service.write_file(candidate_path, content)

        # 记录元数据
        candidate_info = CandidateInfo(
            id=candidate_id,
            source_path=source_path,
            candidate_path=candidate_path,
            action=action,
            status=CandidateStatus.PENDING,
            created_at=datetime.now(),
            word_count=len(content),
            workflow_run_id=workflow_run_id,
        )

        metadata = await self._load_metadata(project_id)
        metadata[candidate_id] = candidate_info.model_dump(mode="json")
        await self._save_metadata(project_id, metadata)

        return candidate_info

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

    async def adopt_candidate(self, project_id: str, candidate_id: str) -> bool:
        """采用候选稿（覆盖源文件前创建修改日志）"""
        import re

        candidate_info = await self.get_candidate(project_id, candidate_id)
        if not candidate_info:
            return False

        if candidate_info.status != CandidateStatus.PENDING:
            return False

        # 读取候选稿内容
        content = await self.get_candidate_content(project_id, candidate_id)
        if content is None:
            return False

        source_path = self._project_path(project_id, candidate_info.source_path)

        # 读取源文件原文（用于创建修改日志）
        original_content = ""
        try:
            orig, _, _ = await self.file_service.read_file(source_path)
            original_content = orig
        except Exception:
            pass

        # 计算字数
        def _wc(text: str) -> int:
            return len(re.findall(r'[一-鿿]', text)) + len(re.findall(r'[a-zA-Z]+', text))

        # 在覆盖前创建修改日志
        revision_id = f"rev-{uuid.uuid4().hex[:8]}"

        # 推导 revision-log 目录路径
        source_parts = candidate_info.source_path.split("/")
        revision_log_dir = "/".join(source_parts[:-1]) + "/revision-log"

        revision_entry = {
            "id": revision_id,
            "candidate_id": candidate_id,
            "chapter_path": candidate_info.source_path,
            "revision_type": "candidate_adopt",
            "description": f"采用候选稿: {candidate_info.action.value}",
            "word_count_before": _wc(original_content),
            "word_count_after": _wc(content),
            "adopted_at": datetime.now().isoformat(),
        }

        # 如果有 diff 库，生成 unified diff
        try:
            import difflib
            before_lines = original_content.splitlines(keepends=True)
            after_lines = content.splitlines(keepends=True)
            diff = "".join(difflib.unified_diff(
                before_lines, after_lines,
                fromfile="采用前", tofile="采用后", lineterm=""
            ))
            revision_entry["diff"] = diff
        except Exception:
            pass

        # 保存修改日志
        try:
            revision_log_path = f"{project_id}/{revision_log_dir}/{revision_id}.json"
            await self.file_service.write_file(
                revision_log_path,
                json.dumps(revision_entry, ensure_ascii=False, indent=2)
            )
        except Exception:
            # 修改日志创建失败不影响采用操作
            pass

        # 写入源文件
        await self.file_service.write_file(source_path, content)

        # 更新状态
        candidate_info.status = CandidateStatus.ADOPTED
        candidate_info.adopted_at = datetime.now()

        metadata = await self._load_metadata(project_id)
        metadata[candidate_id] = candidate_info.model_dump(mode="json")
        await self._save_metadata(project_id, metadata)

        return True

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
