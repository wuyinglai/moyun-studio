"""墨韵 - 版本快照管理

创建、恢复快照，对比版本差异。
"""

from datetime import datetime
import difflib
import json
from pathlib import Path
from typing import TYPE_CHECKING
import uuid

import aiofiles

from backend.core.exceptions import ResourceNotFoundError

if TYPE_CHECKING:
    from backend.core.file_ops import FileService


class Snapshot:
    """快照数据"""

    def __init__(
        self,
        snapshot_id: str,
        file_path: str,
        content: str,
        label: str | None,
        created_at: str
    ):
        self.snapshot_id = snapshot_id
        self.file_path = file_path
        self.content = content
        self.label = label
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "file_path": self.file_path,
            "label": self.label,
            "created_at": self.created_at,
            "word_count": len(self.content)
        }


class SnapshotManager:
    """快照管理器

    职责：
    - 创建文件快照
    - 列出/恢复快照
    - 生成版本差异
    """

    SNAPSHOT_DIR = "backup/snapshots"

    def __init__(self, file_service: "FileService"):
        self.file_service = file_service

    async def create_snapshot(
        self,
        file_path: str,
        label: str | None = None
    ) -> Snapshot:
        """创建快照"""
        content, metadata = await self.file_service.read_file(file_path)

        snapshot_id = str(uuid.uuid4())[:8]
        created_at = datetime.now().isoformat()

        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            file_path=file_path,
            content=content,
            label=label,
            created_at=created_at
        )

        snapshot_file = f"{self.SNAPSHOT_DIR}/{file_path}/{snapshot_id}.json"
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "file_path": file_path,
            "content": content,
            "metadata": metadata,
            "label": label,
            "created_at": created_at
        }

        await self.file_service.write_file(
            snapshot_file,
            json.dumps(snapshot_data, ensure_ascii=False, indent=2),
            None  # 没有frontmatter
        )

        await self._update_index(file_path, snapshot.to_dict())

        return snapshot

    async def list_snapshots(self, file_path: str) -> list[dict]:
        """列出文件的快照"""
        index_file = f"{self.SNAPSHOT_DIR}/{file_path}/index.json"

        try:
            content, _ = await self.file_service.read_file(index_file)
            return json.loads(content).get("snapshots", [])
        except Exception:
            return []

    async def restore_snapshot(self, snapshot_id: str) -> None:
        """恢复快照"""
        snapshot_data = await self._find_snapshot(snapshot_id)
        if not snapshot_data:
            raise ResourceNotFoundError(resource="快照", resource_id=snapshot_id)

        await self.file_service.write_file(
            snapshot_data["file_path"],
            snapshot_data["content"],
            frontmatter_dict=snapshot_data.get("metadata")
        )

    async def compare_versions(
        self,
        snapshot_id1: str,
        snapshot_id2: str
    ) -> str:
        """对比两个快照"""
        snap1 = await self._find_snapshot(snapshot_id1)
        snap2 = await self._find_snapshot(snapshot_id2)

        if not snap1 or not snap2:
            raise ResourceNotFoundError(resource="快照", resource_id=f"{snapshot_id1}或{snapshot_id2}")

        diff = difflib.unified_diff(
            snap1["content"].splitlines(),
            snap2["content"].splitlines(),
            fromfile=f"版本1 ({snap1['created_at']})",
            tofile=f"版本2 ({snap2['created_at']})",
            lineterm=""
        )
        return "\n".join(diff)

    async def _find_snapshot(self, snapshot_id: str) -> dict | None:
        """查找快照"""
        index_path = Path(self.file_service.workspace) / self.SNAPSHOT_DIR

        for index_file in index_path.rglob("*.json"):
            if index_file.name == "index.json":
                continue

            try:
                async with aiofiles.open(index_file, encoding="utf-8") as f:
                    data = json.loads(await f.read())

                if data.get("snapshot_id") == snapshot_id:
                    return data
            except Exception:
                continue

        return None

    async def _update_index(self, file_path: str, snapshot_info: dict) -> None:
        """更新索引"""
        index_file = f"{self.SNAPSHOT_DIR}/{file_path}/index.json"

        try:
            content, _ = await self.file_service.read_file(index_file)
            index_data = json.loads(content)
        except Exception:
            index_data = {"file_path": file_path, "snapshots": []}

        index_data["snapshots"].insert(0, snapshot_info)

        index_data["snapshots"] = index_data["snapshots"][:50]

        await self.file_service.write_file(
            index_file,
            json.dumps(index_data, ensure_ascii=False, indent=2),
            None  # 没有frontmatter
        )
