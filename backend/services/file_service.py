"""墨韵 - 文件服务实现

封装异步文件读写操作，支持frontmatter解析。
"""

import logging
import shutil
import yaml
from pathlib import Path
from typing import Any

import aiofiles
import frontmatter

from backend.config import get_settings
from backend.core.exceptions import FileNotFoundError

logger = logging.getLogger(__name__)


class FileService:
    """文件服务实现

    封装异步文件读写操作，支持frontmatter解析。
    """

    def __init__(self):
        self.settings = get_settings()
        self.workspace = self.settings.projects_path

    def _resolve_path(self, relative_path: str) -> Path:
        """解析相对路径为绝对路径"""
        # 处理Windows路径
        normalized = relative_path.replace("\\", "/")
        return self.settings.projects_path / normalized

    async def read_file(
        self,
        relative_path: str
    ) -> tuple[str, dict | None]:
        """
        读取文件内容，解析frontmatter。

        Returns:
            tuple[内容(str), frontmatter(dict | None)]
        """
        path = self._resolve_path(relative_path)

        if not path.exists():
            raise FileNotFoundError(str(path))

        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()

        if path.suffix == ".md":
            try:
                post = frontmatter.loads(content)
                return post.content, dict(post.metadata) if post.metadata else None
            except Exception:
                return content, None

        return content, None

    async def write_file(
        self,
        relative_path: str,
        content: str,
        frontmatter: dict | None = None
    ) -> None:
        """写入文件内容，支持frontmatter"""
        path = self._resolve_path(relative_path)

        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

        # 组装内容
        if frontmatter:
            fm_content = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
            full_content = f"---\n{fm_content}---\n\n{content}"
        else:
            full_content = content

        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(full_content)

    async def create_directory(self, relative_path: str) -> None:
        """创建目录"""
        path = self._resolve_path(relative_path)
        path.mkdir(parents=True, exist_ok=True)

    async def delete_file(self, relative_path: str) -> None:
        """删除文件"""
        path = self._resolve_path(relative_path)
        if path.exists():
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)

    async def list_directory(self, relative_path: str = "") -> list[dict]:
        """列出目录内容"""
        path = self._resolve_path(relative_path) if relative_path else self.settings.projects_path

        if not path.exists():
            return []

        items = []
        for item in sorted(path.iterdir()):
            item_info = {
                "name": item.name,
                "path": item.as_posix().replace(str(self.settings.projects_path) + "/", "").replace("\\", "/"),
                "type": "directory" if item.is_dir() else "file",
            }
            if item.is_file():
                item_info["size"] = item.stat().st_size
                item_info["modified"] = item.stat().st_mtime
            items.append(item_info)

        return items

    async def exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""
        path = self._resolve_path(relative_path)
        return path.exists()

    async def get_tree(
        self,
        relative_path: str = "",
        max_depth: int = 10
    ) -> list[dict]:
        """获取文件树结构"""
        path = self._resolve_path(relative_path) if relative_path else self.settings.projects_path

        if not path.exists():
            return []

        return self._build_tree(path, max_depth)

    def _build_tree(
        self,
        path: Path,
        max_depth: int,
        current_depth: int = 0
    ) -> list[dict]:
        """递归构建文件树"""
        if current_depth >= max_depth:
            return []

        items = []
        try:
            for item in sorted(path.iterdir()):
                # 跳过隐藏文件和backup目录
                if item.name.startswith("."):
                    continue

                item_info = {
                    "name": item.name,
                    "path": item.as_posix().replace(str(self.settings.projects_path) + "/", "").replace("\\", "/"),
                    "type": "directory" if item.is_dir() else "file",
                }

                if item.is_dir():
                    children = self._build_tree(item, max_depth, current_depth + 1)
                    item_info["children"] = children
                else:
                    item_info["size"] = item.stat().st_size

                items.append(item_info)
        except PermissionError:
            pass

        return items
