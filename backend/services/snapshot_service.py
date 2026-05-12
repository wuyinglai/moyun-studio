"""墨韵 - 快照服务实现

封装版本快照管理功能。
"""

import difflib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from backend.config import get_settings
from backend.core.exceptions import ResourceNotFoundError
from backend.services.base import SnapshotServiceInterface

logger = logging.getLogger(__name__)


class SnapshotService(SnapshotServiceInterface):
    """快照服务实现"""

    SNAPSHOT_DIR = ".snapshots"

    def __init__(self):
        self.settings = get_settings()
        self.projects_path = self.settings.projects_path

    def _resolve_project(self, project_id: str) -> Path:
        """解析项目路径"""
        return self.projects_path / project_id

    async def create_snapshot(
        self,
        project_id: str,
        file_path: str,
        content: str,
        label: str | None = None
    ) -> dict[str, Any]:
        """创建快照"""
        project_path = self._resolve_project(project_id)
        snapshot_id = str(uuid.uuid4())[:8]
        created_at = datetime.now().isoformat()

        snapshot_dir = project_path / self.SNAPSHOT_DIR / file_path
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_file = snapshot_dir / f"{snapshot_id}.json"
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "file_path": file_path,
            "content": content,
            "label": label,
            "created_at": created_at,
        }

        async with aiofiles.open(snapshot_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(snapshot_data, ensure_ascii=False, indent=2))

        # 更新索引
        await self._update_index(project_path, file_path, snapshot_data)

        return {
            "snapshot_id": snapshot_id,
            "file_path": file_path,
            "label": label,
            "created_at": created_at,
            "word_count": len(content),
        }

    async def list_snapshots(
        self,
        project_id: str,
        file_path: str
    ) -> list[dict[str, Any]]:
        """列出快照"""
        project_path = self._resolve_project(project_id)
        index_file = project_path / self.SNAPSHOT_DIR / file_path / "index.json"

        if not index_file.exists():
            return []

        async with aiofiles.open(index_file, "r", encoding="utf-8") as f:
            content = await f.read()

        try:
            index_data = json.loads(content)
            return index_data.get("snapshots", [])
        except json.JSONDecodeError:
            return []

    async def restore_snapshot(
        self,
        project_id: str,
        snapshot_id: str
    ) -> dict[str, Any]:
        """恢复快照"""
        project_path = self._resolve_project(project_id)
        snapshot_data = await self._find_snapshot(project_path, snapshot_id)

        if not snapshot_data:
            logger.warning(f"快照不存在: {snapshot_id}")
            raise ResourceNotFoundError(resource="snapshot", identifier=snapshot_id)

        file_path = snapshot_data["file_path"]
        target_file = project_path / file_path

        target_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target_file, "w", encoding="utf-8") as f:
            await f.write(snapshot_data["content"])

        return {
            "file_path": file_path,
            "snapshot_id": snapshot_id,
        }

    async def compare_versions(
        self,
        project_id: str,
        snapshot_id1: str,
        snapshot_id2: str
    ) -> str:
        """对比两个版本"""
        project_path = self._resolve_project(project_id)
        snap1 = await self._find_snapshot(project_path, snapshot_id1)
        snap2 = await self._find_snapshot(project_path, snapshot_id2)

        if not snap1:
            logger.warning(f"快照不存在: {snapshot_id1}")
            raise ResourceNotFoundError(resource="snapshot", identifier=snapshot_id1)
        if not snap2:
            logger.warning(f"快照不存在: {snapshot_id2}")
            raise ResourceNotFoundError(resource="snapshot", identifier=snapshot_id2)

        diff = difflib.unified_diff(
            snap1["content"].splitlines(),
            snap2["content"].splitlines(),
            fromfile=f"版本1 ({snap1['created_at']})",
            tofile=f"版本2 ({snap2['created_at']})",
            lineterm=""
        )
        return "\n".join(diff)

    async def _find_snapshot(
        self,
        project_path: Path,
        snapshot_id: str
    ) -> dict | None:
        """查找快照"""
        snapshot_dir = project_path / self.SNAPSHOT_DIR
        if not snapshot_dir.exists():
            return None

        for snapshot_file in snapshot_dir.rglob("*.json"):
            if snapshot_file.name == "index.json":
                continue

            try:
                async with aiofiles.open(snapshot_file, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())

                if data.get("snapshot_id") == snapshot_id:
                    return data
            except Exception:
                continue

        return None

    async def _update_index(
        self,
        project_path: Path,
        file_path: str,
        snapshot_data: dict
    ) -> None:
        """更新索引"""
        index_file = project_path / self.SNAPSHOT_DIR / file_path / "index.json"

        try:
            async with aiofiles.open(index_file, "r", encoding="utf-8") as f:
                content = await f.read()
            index_data = json.loads(content)
        except Exception:
            index_data = {"file_path": file_path, "snapshots": []}

        snapshot_info = {
            "snapshot_id": snapshot_data["snapshot_id"],
            "label": snapshot_data.get("label"),
            "created_at": snapshot_data["created_at"],
            "word_count": len(snapshot_data["content"]),
        }
        index_data["snapshots"].insert(0, snapshot_info)

        # 保留最近50个快照
        index_data["snapshots"] = index_data["snapshots"][:50]

        async with aiofiles.open(index_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(index_data, ensure_ascii=False, indent=2))
