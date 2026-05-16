"""墨韵 - 项目管理服务

职责：
- 项目元数据读写
- 项目统计计算
- 项目创建/删除
"""

import asyncio
import json
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.config import Settings
from backend.core.exceptions import ProjectError, ProjectNotFoundError
from backend.schemas.project import ProjectInfo

logger = logging.getLogger(__name__)


def _count_words(text: str) -> int:
    """统计字数（中英文混合）"""
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    return chinese_chars + english_words


class ProjectService:
    """项目服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.projects_path = settings.projects_path

    # ─── 路径辅助 ────────────────────────────────────────

    def _meta_path(self, project_dir: Path) -> Path:
        return project_dir / "meta.json"

    def _context_path(self, project_dir: Path) -> Path:
        return project_dir / "context.json"

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_path / project_id

    # ─── 元数据读写 ──────────────────────────────────────

    def _load_meta(self, project_dir: Path) -> dict | None:
        mp = self._meta_path(project_dir)
        if not mp.is_file():
            return None
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("跳过无效项目meta: %s (%s)", mp, e)
            return None

    def _load_context(self, project_dir: Path) -> dict:
        cp = self._context_path(project_dir)
        if cp.is_file():
            try:
                return json.loads(cp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("跳过无效项目context: %s (%s)", cp, e)
        return {"stats": {"total_words": 0, "total_sections": 0, "completed_sections": 0}}

    # ─── 统计计算 ────────────────────────────────────────

    def _compute_completion(self, meta: dict, context: dict) -> tuple[float, int]:
        """返回 (completion_rate, total_words)"""
        stats = context.get("stats", {})
        total = stats.get("total_sections", 0)
        completed = stats.get("completed_sections", 0)
        rate = (completed / total) if total > 0 else 0.0
        return rate, stats.get("total_words", 0)

    def _dt(self, s: str) -> datetime:
        """datetime 兼容处理"""
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.now(timezone.utc)

    def recalculate_stats(self, project_dir: Path) -> dict:
        """扫描 chapters/ 下实际文件，重新计算项目统计信息

        完成度 = 有内容的节文件数 / 大纲中计划的节总数
        - 节文件有实际内容（字数 > 0）才算完成
        - 空文件不计入完成数
        - ch-meta.json 中 status 为 discarded 的章节不计入总数
        """
        chapters_dir = project_dir / "chapters"
        total_sections = 0
        completed_sections = 0
        total_words = 0
        chapter_count = 0
        volume_count = 0

        if not chapters_dir.exists():
            return {"total_sections": 0, "completed_sections": 0, "total_words": 0,
                    "chapter_count": 0, "volume_count": 0}

        for vol_dir in sorted(chapters_dir.glob("vol-*")):
            if not vol_dir.is_dir():
                continue
            volume_count += 1

            for ch_dir in sorted(vol_dir.glob("ch-*")):
                if not ch_dir.is_dir():
                    continue
                chapter_count += 1

                # 读取 ch-meta.json 检查废弃状态
                ch_meta = {}
                ch_meta_file = ch_dir / "ch-meta.json"
                if ch_meta_file.exists():
                    try:
                        ch_meta = json.loads(ch_meta_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass

                # 废弃章不计入统计
                if ch_meta.get("status") == "discarded":
                    continue

                for sec_file in sorted(ch_dir.glob("sec-*.md")):
                    total_sections += 1
                    try:
                        text = sec_file.read_text(encoding="utf-8")
                        wc = _count_words(text)
                        if wc > 0:
                            completed_sections += 1
                            total_words += wc
                    except Exception:
                        pass

        return {
            "total_sections": total_sections,
            "completed_sections": completed_sections,
            "total_words": total_words,
            "chapter_count": chapter_count,
            "volume_count": volume_count,
        }

    def get_project_info(self, project_dir: Path) -> ProjectInfo | None:
        """获取项目信息"""
        meta = self._load_meta(project_dir)
        if meta is None:
            return None
        context = self._load_context(project_dir)
        rate, words = self._compute_completion(meta, context)

        return ProjectInfo(
            project_id=meta["project_id"],
            name=meta.get("name", project_dir.name),
            author=meta.get("author", ""),
            genre=meta.get("genre", ""),
            theme=meta.get("theme", ""),
            tone=meta.get("tone", ""),
            background=meta.get("background", ""),
            writing_style=meta.get("writing_style", ""),
            target_word_count=meta.get("target_word_count", 0),
            completion_rate=round(rate, 4),
            total_words=words,
            created_at=self._dt(meta.get("created_at", "")),
            updated_at=self._dt(meta.get("updated_at", "")),
        )

    def list_projects(self) -> list[ProjectInfo]:
        """获取所有项目列表"""
        self.projects_path.mkdir(parents=True, exist_ok=True)

        projects: list[ProjectInfo] = []
        for d in sorted(self.projects_path.iterdir()):
            if d.is_dir():
                info = self.get_project_info(d)
                if info:
                    projects.append(info)

        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def create_project_meta(self, project_id: str, name: str, req) -> dict:
        """生成并写入项目元数据"""
        now = datetime.now(timezone.utc).isoformat()
        project_dir = self._project_dir(project_id)

        # 写 meta.json
        meta = {
            "project_id": project_id,
            "name": name,
            "genre": req.genre,
            "theme": req.theme,
            "tone": req.tone,
            "background": req.background,
            "writing_style": req.writing_style,
            "target_word_count": req.target_word_count,
            "author": req.author,
            "created_at": now,
            "updated_at": now,
        }
        return meta

    def write_meta(self, project_dir: Path, meta: dict):
        self._meta_path(project_dir).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    def write_context(self, project_dir: Path, context: dict):
        self._context_path(project_dir).write_text(
            json.dumps(context, ensure_ascii=False, indent=2), "utf-8")

    def save_stats(self, project_dir: Path, stats: dict):
        """更新 context.json 中的统计信息"""
        context = self._load_context(project_dir)
        context["stats"] = stats
        context["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write_context(project_dir, context)

    def delete_project_dir(self, project_id: str):
        """删除项目目录"""
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)
        try:
            shutil.rmtree(project_dir)
        except Exception as e:
            raise ProjectError(f"删除项目失败: {str(e)}")
