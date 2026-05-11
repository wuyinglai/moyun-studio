"""墨韵 - 文件操作服务

异步文件读写，支持frontmatter。
"""

import logging
from pathlib import Path
from typing import Any

import aiofiles
import frontmatter

from backend.core.exceptions import FileNotFoundError


class FileService:
    """文件操作服务

    职责：
    - 异步文件读写
    - frontmatter解析和写入
    - 目录管理
    - 文件树构建
    """
    logger = logging.getLogger(__name__)

    def __init__(self, workspace_path: Path | str):
        self.workspace = Path(workspace_path)

    def _resolve_path(self, relative_path: str) -> Path:
        """解析相对路径为绝对路径"""
        return self.workspace / relative_path

    async def read_file(
        self,
        relative_path: str
    ) -> tuple[str, dict | None]:
        """读取文件

        Args:
            relative_path: 相对于workspace的路径

        Returns:
            (content, frontmatter) - 文件内容和元数据
        """
        file_path = self._resolve_path(relative_path)

        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        if file_path.suffix == ".md":
            post = frontmatter.loads(content)
            return post.content, dict(post) if post.metadata else None

        return content, None

    async def write_file(
        self,
        relative_path: str,
        content: str,
        frontmatter_dict: dict | None = None
    ) -> None:
        """写入文件

        Args:
            relative_path: 相对于workspace的路径
            content: 文件内容
            frontmatter_dict: frontmatter元数据
        """
        file_path = self._resolve_path(relative_path)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        if frontmatter_dict and file_path.suffix == ".md":
            post = frontmatter.Post(content, **frontmatter_dict)
            content = frontmatter.dumps(post)

        async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
            await f.write(content)

    async def create_directory(self, relative_path: str) -> None:
        """创建目录"""
        dir_path = self._resolve_path(relative_path)
        dir_path.mkdir(parents=True, exist_ok=True)

    async def delete_file(self, relative_path: str) -> None:
        """删除文件"""
        file_path = self._resolve_path(relative_path)
        if file_path.exists():
            file_path.unlink()

    async def delete_directory(self, relative_path: str) -> None:
        """删除目录"""
        dir_path = self._resolve_path(relative_path)
        if dir_path.exists() and dir_path.is_dir():
            import shutil
            shutil.rmtree(dir_path)

    async def exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""
        return self._resolve_path(relative_path).exists()

    async def list_directory(self, relative_path: str = "") -> list[dict]:
        """列出目录内容

        Returns:
            list of {name, path, is_dir, size}
        """
        dir_path = self._resolve_path(relative_path)

        if not dir_path.exists():
            return []

        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "path": item.relative_to(self.workspace).as_posix(),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
            })

        return sorted(items, key=lambda x: (not x["is_dir"], x["name"]))

    async def get_file_tree(
        self,
        relative_path: str = "",
        max_depth: int = 3
    ) -> dict:
        """获取文件树

        Args:
            relative_path: 起始路径
            max_depth: 最大深度

        Returns:
            树形结构
        """
        return await self._build_tree(relative_path, 0, max_depth)

    async def _build_tree(
        self,
        relative_path: str,
        current_depth: int,
        max_depth: int
    ) -> dict:
        """递归构建文件树"""
        dir_path = self._resolve_path(relative_path)
        name = relative_path.split("/")[-1] if relative_path else dir_path.name

        node = {
            "name": name,
            "path": relative_path,
            "children": []
        }

        if current_depth >= max_depth:
            return node

        for item in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name.startswith("."):
                continue

            child_path = item.relative_to(self.workspace).as_posix()  # 统一正斜杠
            if item.is_dir():
                child = await self._build_tree(child_path, current_depth + 1, max_depth)
                node["children"].append(child)
            else:
                node["children"].append({
                    "name": item.name,
                    "path": child_path,
                    "children": []
                })

        return node

    async def get_project_info(self, project_path: str) -> dict | None:
        """获取项目信息"""
        info_path = self._resolve_path(f"{project_path}/.project.json")
        if info_path.exists():
            import json
            async with aiofiles.open(info_path, "r") as f:
                return json.loads(await f.read())
        return None
