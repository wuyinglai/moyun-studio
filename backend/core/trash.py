"""墨韵 - 回收站服务

提供文件/目录的"软删除"：移到 .trash/ 目录而非永久删除，
支持恢复和清空。
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TrashService:
    """回收站服务

    职责：
    - 将文件/目录移到 workspace/.trash/
    - 从回收站恢复到原位置
    - 列出回收站内容
    - 清空回收站
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root).resolve()
        self.trash_dir = self.workspace_root / ".trash"
        self.trash_dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self.trash_dir / ".metadata.json"
        self._metadata = self._load_metadata()

    # ─── 元数据管理 ──────────────────────────────────────────────

    def _load_metadata(self) -> dict:
        if self._meta_path.exists():
            try:
                return json.loads(self._meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取回收站元数据失败: %s", e)
                return {}
        return {}

    def _save_metadata(self) -> None:
        self._meta_path.write_text(
            json.dumps(self._metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ─── 核心操作 ────────────────────────────────────────────────

    def move_to_trash(self, path: Path) -> dict:
        """将文件或目录移到回收站

        Args:
            path: 要删除的文件或目录的绝对路径

        Returns:
            {trash_name, original_path, timestamp}
        """
        path = Path(path).resolve()

        if not path.exists():
            logger.warning("要删除的路径不存在: %s", path)
            return {"trash_name": "", "original_path": str(path), "timestamp": ""}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        trash_name = f"{timestamp}_{path.name}"
        dest = self.trash_dir / trash_name

        is_dir = path.is_dir()

        try:
            shutil.move(str(path), str(dest))
        except OSError as e:
            logger.error("移动到回收站失败 %s -> %s: %s", path, dest, e)
            raise

        self._metadata[trash_name] = {
            "original_path": str(path),
            "trash_name": trash_name,
            "timestamp": timestamp,
            "is_dir": is_dir,
        }
        self._save_metadata()

        logger.info("已移到回收站: %s -> %s", path, dest)
        return {
            "trash_name": trash_name,
            "original_path": str(path),
            "timestamp": timestamp,
        }

    def restore(self, trash_name: str) -> Path | None:
        """从回收站恢复到原位置

        Args:
            trash_name: 回收站中的条目名（如 "20250517_120000_123456_foo.yaml"）

        Returns:
            恢复后的绝对路径，失败返回 None
        """
        meta = self._metadata.get(trash_name)
        if not meta:
            logger.warning("回收站元数据不存在: %s", trash_name)
            return None

        src = self.trash_dir / trash_name
        if not src.exists():
            logger.warning("回收站文件不存在: %s", src)
            del self._metadata[trash_name]
            self._save_metadata()
            return None

        dest = Path(meta["original_path"])
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(src), str(dest))
        except OSError as e:
            logger.error("恢复失败 %s -> %s: %s", src, dest, e)
            return None

        del self._metadata[trash_name]
        self._save_metadata()

        logger.info("已从回收站恢复: %s -> %s", trash_name, dest)
        return dest

    def list_trash(self) -> list[dict]:
        """列出回收站所有内容"""
        result = []
        for trash_name, meta in sorted(
            self._metadata.items(),
            key=lambda x: x[1].get("timestamp", ""),
        ):
            result.append({
                "trash_name": trash_name,
                "original_path": meta.get("original_path", ""),
                "timestamp": meta.get("timestamp", ""),
                "is_dir": meta.get("is_dir", False),
            })
        return result

    def empty_trash(self) -> int:
        """清空回收站

        Returns:
            删除的文件/目录数
        """
        count = 0
        for trash_name in list(self._metadata.keys()):
            path = self.trash_dir / trash_name
            if path.exists():
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    count += 1
                except OSError as e:
                    logger.warning("清空回收站失败 %s: %s", path, e)

        self._metadata = {}
        self._save_metadata()
        logger.info("回收站已清空，共删除 %d 项", count)
        return count
