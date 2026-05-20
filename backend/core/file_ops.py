"""墨韵 - 文件操作服务

异步文件读写，支持frontmatter。
"""

import logging
import os
from pathlib import Path
from typing import Any
import shutil
import json

import aiofiles
import frontmatter

from backend.core.exceptions import MoyunFileNotFoundError, ValidationError
from backend.core.trash import TrashService


class FileService:
    """文件操作服务

    职责：
    - 异步文件读写
    - frontmatter解析和写入
    - 目录管理
    - 文件树构建
    - 路径安全验证
    """
    logger = logging.getLogger(__name__)

    # 禁止的路径段（任何层级出现都拦截）
    FORBIDDEN_SEGMENTS = {'.env', '.config.json', '.git', 'node_modules', '__pycache__'}
    FORBIDDEN_PREFIXES = ('..', '/', '\\')
    FORBIDDEN_SUFFIXES = ('.py', '.pyc', '.sh', '.bat', '.exe')

    def __init__(self, workspace_path: Path | str):
        self.workspace = Path(workspace_path).resolve()

    def _resolve_path(self, relative_path: str, check_write_suffix: bool = False) -> Path:
        """解析相对路径为绝对路径，包含安全检查

        Args:
            relative_path: 相对路径
            check_write_suffix: 是否检查写入文件的后缀（用于写操作）
        """
        if not relative_path:
            raise ValidationError("路径不能为空")

        # 检查绝对路径或越界路径
        for prefix in self.FORBIDDEN_PREFIXES:
            if relative_path.startswith(prefix):
                raise ValidationError(f"非法路径: {relative_path}")

        # 检查路径中的 ..
        parts = relative_path.split('/')
        parts += relative_path.split('\\')
        if '..' in parts:
            raise ValidationError(f"路径不能包含 '..': {relative_path}")

        # 检查路径中任何段是否包含禁止的名称
        path_parts = Path(relative_path).parts
        for part in path_parts:
            if part in self.FORBIDDEN_SEGMENTS:
                raise ValidationError(f"禁止操作: 路径包含 '{part}'")

        # 写入操作时检查禁止的后缀
        if check_write_suffix:
            suffix = Path(relative_path).suffix.lower()
            if suffix in self.FORBIDDEN_SUFFIXES:
                raise ValidationError(f"禁止写入 {suffix} 类型文件")

        # 解析并规范化路径
        target = (self.workspace / relative_path).resolve()

        # 检查是否在workspace内
        if not str(target).startswith(str(self.workspace) + os.sep) and target != self.workspace:
            raise ValidationError(f"路径越界: {relative_path}")

        return target

    @property
    def _trash(self) -> TrashService:
        """懒初始化的回收站服务（指向 workspace 的父级）"""
        if not hasattr(self, "_trash_service"):
            self._trash_service = TrashService(self.workspace.parent)
        return self._trash_service

    async def read_file(
        self,
        relative_path: str
    ) -> tuple[str, dict | None, float | None]:
        """读取文件

        Args:
            relative_path: 相对于workspace的路径

        Returns:
            (content, frontmatter, mtime) - 文件内容、元数据和修改时间
        """
        file_path = self._resolve_path(relative_path)

        if not file_path.exists():
            raise MoyunFileNotFoundError(str(file_path))

        async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        mtime = file_path.stat().st_mtime if file_path.exists() else None

        if file_path.suffix == ".md":
            post = frontmatter.loads(content)
            return post.content, dict(post.metadata) if post.metadata else None, mtime

        return content, None, mtime

    async def write_file(
        self,
        relative_path: str,
        content: str,
        frontmatter_dict: dict | None = None,
        expected_mtime: float | None = None,
        expected_hash: str | None = None,
    ) -> None:
        """写入文件（支持并发控制）

        Args:
            relative_path: 相对于workspace的路径
            content: 文件内容
            frontmatter_dict: frontmatter元数据
            expected_mtime: 期望的文件修改时间（用于并发控制）
            expected_hash: 期望的文件内容哈希（用于并发控制）

        Raises:
            FileConflictError: 文件已被其他操作修改
        """
        file_path = self._resolve_path(relative_path, check_write_suffix=True)

        # 并发控制：检查文件是否已被修改
        if file_path.exists():
            if expected_mtime is not None:
                current_mtime = file_path.stat().st_mtime
                if abs(current_mtime - expected_mtime) > 0.001:  # 允许浮点数误差
                    from backend.core.exceptions import FileConflictError
                    raise FileConflictError(
                        f"文件已被修改: {relative_path}",
                        details={
                            "current_mtime": current_mtime,
                            "expected_mtime": expected_mtime,
                        }
                    )

            if expected_hash is not None:
                import hashlib
                current_content, _, _ = await self.read_file(relative_path)
                current_hash = hashlib.md5(current_content.encode()).hexdigest()
                if current_hash != expected_hash:
                    from backend.core.exceptions import FileConflictError
                    raise FileConflictError(
                        f"文件内容已变更: {relative_path}",
                        details={"current_hash": current_hash, "expected_hash": expected_hash}
                    )

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

    async def delete_file(self, relative_path: str) -> dict | None:
        """删除文件（移到回收站）

        Returns:
            回收站记录，若文件不存在返回 None
        """
        file_path = self._resolve_path(relative_path)
        if not file_path.exists():
            return None
        return self._trash.move_to_trash(file_path)

    async def delete_directory(self, relative_path: str) -> dict | None:
        """删除目录（移到回收站）

        Returns:
            回收站记录，若目录不存在返回 None
        """
        dir_path = self._resolve_path(relative_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return None
        return self._trash.move_to_trash(dir_path)

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
            async with aiofiles.open(info_path, "r") as f:
                return json.loads(await f.read())
        return None

    async def search_files(
        self,
        project_id: str,
        query: str,
        case_sensitive: bool = False,
        regex: bool = False,
    ) -> list[dict]:
        """在项目中搜索文件内容

        Args:
            project_id: 项目ID
            query: 搜索关键词
            case_sensitive: 是否区分大小写
            regex: 是否使用正则表达式

        Returns:
            [{file, line, content}, ...]
        """
        import re

        project_path = self._resolve_path(project_id)
        if not project_path.exists():
            return []

        results = []
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            if regex:
                pattern = re.compile(query, flags)
            else:
                pattern = re.compile(re.escape(query), flags)
        except re.error:
            return []

        async def _search_dir(dir_path: Path, rel_prefix: str = "") -> None:
            for item in dir_path.iterdir():
                if item.name.startswith("."):
                    continue
                rel = f"{rel_prefix}/{item.name}" if rel_prefix else item.name
                if item.is_dir():
                    await _search_dir(item, rel)
                elif item.is_file() and item.suffix in (".md", ".txt", ".mdx"):
                    try:
                        async with aiofiles.open(item, "r", encoding="utf-8") as f:
                            content = await f.read()
                        for line_no, line in enumerate(content.splitlines(), 1):
                            if pattern.search(line):
                                results.append({
                                    "file": rel,
                                    "line": line_no,
                                    "content": line[:200],
                                })
                    except (UnicodeDecodeError, OSError):
                        pass

        await _search_dir(project_path)
        return results

    async def rename_path(self, project_id: str, old_path: str, new_path: str) -> None:
        """安全地重命名/移动文件或目录
        
        Args:
            project_id: 项目ID
            old_path: 原路径（相对于项目根目录）
            new_path: 新路径（相对于项目根目录）
        
        Raises:
            ValidationError: 路径非法或越界
            FileNotFoundError: 原路径不存在
        """
        from backend.core.exceptions import ResourceNotFoundError
        
        # 安全检查 old_path 和 new_path
        old_full = self._resolve_path(f"{project_id}/{old_path}", check_write_suffix=True)
        new_full = self._resolve_path(f"{project_id}/{new_path}", check_write_suffix=True)
        
        if not old_full.exists():
            raise ResourceNotFoundError(resource="file", identifier=old_path)
        
        # 执行重命名
        new_full.parent.mkdir(parents=True, exist_ok=True)
        old_full.rename(new_full)

    async def create_project_directory(self, project_id: str, dir_path: str) -> None:
        """安全地在项目目录下创建目录
        
        Args:
            project_id: 项目ID
            dir_path: 目录路径（相对于项目根目录）
        
        Raises:
            ValidationError: 路径非法或越界
        """
        # 安全检查 dir_path
        full_path = self._resolve_path(f"{project_id}/{dir_path}", check_write_suffix=True)
        
        full_path.mkdir(parents=True, exist_ok=True)
