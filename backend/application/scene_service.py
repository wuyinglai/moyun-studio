"""墨韵 - 场景服务

职责：
- 场景路径解析 / 构建 / 进位
- 场景文件读写（委托 FileService）
- 场景空判断

不处理：候选稿、记忆、管线编排。
"""

import logging
import re

from backend.core.file_ops import FileService
from backend.domain.scene import SceneInfo

logger = logging.getLogger(__name__)

# 场景路径正则：chapters/vol-01/ch-001/sec-003.md
_SCENE_PATH_RE = re.compile(r"chapters/vol-(\d+)/ch-(\d+)/sec-(\d+)\.md$")


class SceneService:
    """场景语义服务"""

    def __init__(self, file_service: FileService):
        self._fs = file_service

    # ─── 纯路径函数（无 I/O）────────────────────────────

    @staticmethod
    def parse_scene_path(path: str) -> SceneInfo | None:
        """解析场景路径 → SceneInfo（不含 project_id / mtime / word_count）"""
        m = _SCENE_PATH_RE.search(path)
        if not m:
            return None
        vol, ch, sec = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return SceneInfo(
            project_id="",
            volume=vol,
            chapter=ch,
            scene=sec,
            path=path,
        )

    @staticmethod
    def build_scene_path(volume: int, chapter: int, scene: int) -> str:
        """构建场景相对路径"""
        return f"chapters/vol-{volume:02d}/ch-{chapter:03d}/sec-{scene:03d}.md"

    @staticmethod
    def is_scene_file(path: str) -> bool:
        """判断路径是否为场景文件"""
        return bool(_SCENE_PATH_RE.search(path))

    @staticmethod
    def get_next_scene_path(
        current_path: str,
        scenes_per_chapter: int = 5,
        chapters_per_volume: int = 12,
    ) -> str | None:
        """获取下一个场景路径，支持跨章 / 跨卷进位"""
        info = SceneService.parse_scene_path(current_path)
        if info is None:
            return None
        if info.scene < scenes_per_chapter:
            return SceneService.build_scene_path(info.volume, info.chapter, info.scene + 1)
        if info.chapter < chapters_per_volume:
            return SceneService.build_scene_path(info.volume, info.chapter + 1, 1)
        return SceneService.build_scene_path(info.volume + 1, 1, 1)

    # ─── I/O 函数（委托 FileService）────────────────────

    async def read_scene(self, project_id: str, scene_path: str) -> tuple[str, dict | None, float | None]:
        """读取场景文件

        Returns:
            (content, frontmatter, mtime)
        """
        return await self._fs.read_file(f"{project_id}/{scene_path}")

    async def write_scene(
        self,
        project_id: str,
        scene_path: str,
        content: str,
        expected_mtime: float | None = None,
        expected_hash: str | None = None,
    ) -> None:
        """写入场景文件"""
        await self._fs.write_file(
            f"{project_id}/{scene_path}",
            content,
            expected_mtime=expected_mtime,
            expected_hash=expected_hash,
        )

    async def is_scene_empty(self, project_id: str, scene_path: str) -> bool:
        """判断场景文件是否为空（不存在或内容为空白）"""
        try:
            content, _, _ = await self._fs.read_file(f"{project_id}/{scene_path}")
            return not content or len(content.strip()) == 0
        except Exception:
            return True
