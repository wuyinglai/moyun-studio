"""墨韵 - 项目服务实现

封装项目创建、打开、删除等操作。
"""

import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from backend.config import get_settings

logger = logging.getLogger(__name__)


class ProjectService:
    """项目服务"""

    def __init__(self):
        self.settings = get_settings()
        self.projects_path = self.settings.projects_path

    async def list_projects(self) -> list[dict[str, Any]]:
        """列出所有项目"""
        if not self.projects_path.exists():
            return []

        projects = []
        for project_dir in sorted(self.projects_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not project_dir.is_dir():
                continue

            meta_file = project_dir / "meta.json"
            if meta_file.exists():
                try:
                    async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.loads(await f.read())
                except Exception:
                    meta = {}
            else:
                meta = {}

            # 计算完成度
            completion = await self._calculate_completion(project_dir)

            projects.append({
                "id": project_dir.name,
                "name": meta.get("name", project_dir.name),
                "author": meta.get("author", ""),
                "genre": meta.get("genre", ""),
                "created_at": meta.get("created_at", datetime.fromtimestamp(project_dir.stat().st_ctime).isoformat()),
                "updated_at": meta.get("updated_at", datetime.fromtimestamp(project_dir.stat().st_mtime).isoformat()),
                "completion": completion,
                "word_count": meta.get("word_count", 0),
            })

        return projects

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        """获取项目信息"""
        project_path = self.projects_path / project_id
        if not project_path.exists():
            return None

        meta_file = project_path / "meta.json"
        if meta_file.exists():
            try:
                async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.loads(await f.read())
            except Exception:
                meta = {}
        else:
            meta = {}

        return {
            "id": project_id,
            "name": meta.get("name", project_id),
            "author": meta.get("author", ""),
            "genre": meta.get("genre", ""),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
        }

    async def create_project(
        self,
        name: str,
        author: str = "",
        genre: str = "",
        scale: int = 100000,
        genre_tags: list[str] = None,
        tone: str = "",
        background: str = "",
        theme: str = "",
        writing_style: str = "",
    ) -> dict[str, Any]:
        """创建新项目"""
        project_id = str(uuid.uuid4())[:8]
        project_path = self.projects_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)

        created_at = datetime.now().isoformat()

        logger.info(
            "创建新项目",
            extra={
                "project_id": project_id,
                "name": name,
                "genre": genre,
                "scale": scale,
            }
        )

        # 写入meta.json
        meta = {
            "name": name,
            "author": author,
            "genre": genre,
            "scale": scale,
            "genre_tags": genre_tags or [],
            "tone": tone,
            "background": background,
            "theme": theme,
            "writing_style": writing_style,
            "auto_mode": "L1",
            "thinking": True,
            "created_at": created_at,
            "updated_at": created_at,
        }

        async with aiofiles.open(project_path / "meta.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))

        # 写入context.json
        context = {
            "stats": {
                "total_words": 0,
                "total_sections": 0,
                "completed_sections": 0,
                "chapter_count": 0,
                "volume_count": 0,
                "character_count": 0,
            }
        }

        async with aiofiles.open(project_path / "context.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(context, ensure_ascii=False, indent=2))

        # 创建目录结构
        await self._create_directories(project_path)

        # 创建新文件
        await self._create_initial_files(project_path)

        return {
            "id": project_id,
            "name": name,
            "path": str(project_path),
        }

    async def update_project(
        self,
        project_id: str,
        **kwargs
    ) -> dict[str, Any]:
        """更新项目配置"""
        project_path = self.projects_path / project_id
        meta_file = project_path / "meta.json"

        meta = {}
        if meta_file.exists():
            async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                meta = json.loads(await f.read())

        meta.update(kwargs)
        meta["updated_at"] = datetime.now().isoformat()

        async with aiofiles.open(meta_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))

        return meta

    async def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        project_path = self.projects_path / project_id
        if not project_path.exists():
            logger.warning(f"项目不存在，无法删除: {project_id}")
            return False

        logger.info(f"删除项目: {project_id}")
        shutil.rmtree(project_path)
        return True

    async def generate_structure(
        self,
        project_id: str,
        scale: int = 100000
    ) -> dict[str, Any]:
        """生成项目目录结构"""
        logger.info(
            "生成项目结构",
            extra={"project_id": project_id, "scale": scale}
        )

        project_path = self.projects_path / project_id

        # 计算卷/章/节数量
        # 每节约1800字，每章4节，每卷8-15章
        total_sections = scale // 1800
        total_chapters = total_sections // 4
        chapters_per_volume = 10  # 平均每卷10章
        total_volumes = (total_chapters + chapters_per_volume - 1) // chapters_per_volume

        structure = []
        section_num = 1
        chapter_num = 1

        for vol_num in range(1, total_volumes + 1):
            vol_dir = project_path / "chapters" / f"vol-{vol_num:02d}"
            vol_dir.mkdir(parents=True, exist_ok=True)

            vol_chapters = min(chapters_per_volume, total_chapters - chapter_num + 1)
            if vol_chapters <= 0:
                break

            # 创建卷元数据
            vol_meta = {
                "volume": vol_num,
                "title": f"第{vol_num}卷",
                "description": "",
                "chapter_count": vol_chapters,
            }
            async with aiofiles.open(vol_dir / "vol-meta.json", "w", encoding="utf-8") as f:
                await f.write(json.dumps(vol_meta, ensure_ascii=False, indent=2))

            for ch_num in range(1, vol_chapters + 1):
                ch_dir = vol_dir / f"ch-{chapter_num:03d}"
                ch_dir.mkdir(parents=True, exist_ok=True)

                # 创建章元数据
                ch_meta = {
                    "chapter": chapter_num,
                    "title": f"第{chapter_num}章",
                    "description": "",
                    "section_count": 4,
                    "status": "pending",
                    "memory": "",
                    "story_state": "",
                    "pending_foreshadowing": "",
                    "active_quests": [],
                }
                async with aiofiles.open(ch_dir / "ch-meta.json", "w", encoding="utf-8") as f:
                    await f.write(json.dumps(ch_meta, ensure_ascii=False, indent=2))

                # 创建反馈和修改日志目录
                (ch_dir / "feedback").mkdir(exist_ok=True)
                (ch_dir / "revision-log").mkdir(exist_ok=True)

                # 创建4个节文件
                for sec_num in range(1, 5):
                    sec_file = ch_dir / f"sec-{section_num:03d}.md"
                    sec_file.write_text("", encoding="utf-8")
                    section_num += 1

                structure.append({
                    "volume": vol_num,
                    "chapter": chapter_num,
                    "sections": list(range(section_num - 4, section_num)),
                })
                chapter_num += 1

        # 更新context.json
        context_file = project_path / "context.json"
        context = {}
        if context_file.exists():
            async with aiofiles.open(context_file, "r", encoding="utf-8") as f:
                context = json.loads(await f.read())

        context["stats"] = {
            "total_words": 0,
            "total_sections": total_sections,
            "completed_sections": 0,
            "chapter_count": total_chapters,
            "volume_count": total_volumes,
            "character_count": 0,
        }

        async with aiofiles.open(context_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(context, ensure_ascii=False, indent=2))

        return {
            "volumes": total_volumes,
            "chapters": total_chapters,
            "sections": total_sections,
            "structure": structure,
        }

    async def _calculate_completion(self, project_path: Path) -> float:
        """计算项目完成度"""
        context_file = project_path / "context.json"
        if not context_file.exists():
            return 0.0

        try:
            async with aiofiles.open(context_file, "r", encoding="utf-8") as f:
                context = json.loads(await f.read())

            stats = context.get("stats", {})
            total = stats.get("total_sections", 0)
            completed = stats.get("completed_sections", 0)

            if total == 0:
                return 0.0

            return round(completed / total * 100, 1)
        except Exception:
            return 0.0

    async def _create_directories(self, project_path: Path) -> None:
        """创建目录结构"""
        directories = [
            "chapters",
            "characters",
            "materials/extracted/plots",
            "materials/extracted/scenes",
            "materials/extracted/summaries",
            "materials/extracted/worldbuilding",
            "backup",
        ]

        for directory in directories:
            (project_path / directory).mkdir(parents=True, exist_ok=True)

    async def _create_initial_files(self, project_path: Path) -> None:
        """创建初始文件"""
        initial_files = {
            "outline.md": "# 大纲\n\n## 第一卷\n\n## 第二卷\n",
            "style-guide.md": "# 文风指南\n\n## 语言风格\n\n- 简洁有力\n- 描写细腻\n\n## 叙事风格\n\n- 第三人称\n- 倒叙与插叙结合\n",
            "story-state.md": "# 故事全局状态\n\n## 主角状态\n\n## 势力关系\n\n## 伏笔追踪\n\n## 主线/支线进度\n\n",
            "recent-context.md": "# 近期上下文\n\n## 最近章节摘要\n\n",
        }

        for filename, content in initial_files.items():
            file_path = project_path / filename
            if not file_path.exists():
                file_path.write_text(content, encoding="utf-8")
