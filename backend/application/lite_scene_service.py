"""墨韵 - Lite 场景路径与导航服务

集中管理 Lite 爽文模式的卷章场路径规则。
"""

from dataclasses import dataclass
import re


SECTIONS_PER_CHAPTER = 5
CHAPTERS_PER_VOLUME = 12


@dataclass(frozen=True)
class LiteSceneLocation:
    """Lite 场景位置"""
    volume: int
    chapter: int
    section: int


def extract_chapter_number(file_path: str | None) -> int:
    """从路径中提取章号"""
    if not file_path:
        return 0
    match = re.search(r"/ch-(\d+)/", file_path)
    return int(match.group(1)) if match else 0


def path_parts(file_path: str | None) -> tuple[int, int, int]:
    """从路径中提取卷号、章号、场景号

    Returns:
        tuple[volume, chapter, section]
    """
    if not file_path:
        return 1, 1, 0
    vol = int(re.search(r"vol-(\d+)", file_path).group(1)) if re.search(r"vol-(\d+)", file_path) else 1
    ch = int(re.search(r"ch-(\d+)", file_path).group(1)) if re.search(r"ch-(\d+)", file_path) else 1
    sec = int(re.search(r"sec-(\d+)", file_path).group(1)) if re.search(r"sec-(\d+)", file_path) else 0
    return vol, ch, sec


def section_path(volume_number: int, chapter_number: int, section_number: int) -> str:
    """生成场景文件路径

    Args:
        volume_number: 卷号
        chapter_number: 章号
        section_number: 场景号

    Returns:
        场景文件相对路径，例如 chapters/vol-01/ch-001/sec-001.md
    """
    return f"chapters/vol-{volume_number:02d}/ch-{chapter_number:03d}/sec-{section_number:03d}.md"


def chapter_path(chapter_number: int) -> str:
    """生成章节起始路径（第一卷第一场景）

    Args:
        chapter_number: 章号

    Returns:
        章节起始场景路径
    """
    return section_path(1, chapter_number, 1)


def next_section_path(current_file: str | None) -> str:
    """推导下一个场景路径

    规则：
    - sec < SECTIONS_PER_CHAPTER: 下一场景 sec+1
    - sec == SECTIONS_PER_CHAPTER 且 ch < CHAPTERS_PER_VOLUME: 下一章 ch+1 sec=1
    - sec == SECTIONS_PER_CHAPTER 且 ch == CHAPTERS_PER_VOLUME: 下一卷 vol+1 ch=1 sec=1

    Args:
        current_file: 当前文件路径

    Returns:
        下一个场景文件路径
    """
    vol, ch, sec = path_parts(current_file)
    if sec <= 0:
        return section_path(vol, ch, 1)
    if sec < SECTIONS_PER_CHAPTER:
        return section_path(vol, ch, sec + 1)
    if ch < CHAPTERS_PER_VOLUME:
        return section_path(vol, ch + 1, 1)
    return section_path(vol + 1, 1, 1)


def section_label(file_path: str) -> str:
    """生成场景标签文本

    Args:
        file_path: 场景文件路径

    Returns:
        场景标签，例如 "第1卷 第1章 第1场景"
    """
    vol, ch, sec = path_parts(file_path)
    return f"第{vol}卷 第{ch}章 第{sec}场景"


def chapter_vol_label(vol: int, ch: int) -> str:
    """生成卷章标签文本

    Args:
        vol: 卷号
        ch: 章号

    Returns:
        卷章标签，例如 "第1卷第1章"
    """
    return f"第{vol}卷第{ch}章"


class LiteSceneService:
    """Lite 场景导航服务"""

    def __init__(
        self,
        sections_per_chapter: int = SECTIONS_PER_CHAPTER,
        chapters_per_volume: int = CHAPTERS_PER_VOLUME,
    ):
        self.sections_per_chapter = sections_per_chapter
        self.chapters_per_volume = chapters_per_volume

    def location(self, rel_path: str | None) -> LiteSceneLocation:
        """从路径获取场景位置"""
        vol, ch, sec = path_parts(rel_path)
        return LiteSceneLocation(volume=vol, chapter=ch, section=sec)

    def build_path(self, volume: int, chapter: int, section: int) -> str:
        """构建场景路径"""
        return section_path(volume, chapter, section)

    def build_chapter_start(self, chapter: int) -> str:
        """构建章节起始路径"""
        return chapter_path(chapter)

    def next_location(self, current_path: str | None) -> LiteSceneLocation:
        """推导下一场景位置"""
        next_path = self._next_section_path(current_path)
        return self.location(next_path)

    def _next_section_path(self, current_file: str | None) -> str:
        """内部：推导下一场景路径"""
        vol, ch, sec = path_parts(current_file)
        if sec <= 0:
            return section_path(vol, ch, 1)
        if sec < self.sections_per_chapter:
            return section_path(vol, ch, sec + 1)
        if ch < self.chapters_per_volume:
            return section_path(vol, ch + 1, 1)
        return section_path(vol + 1, 1, 1)

    def label(self, rel_path: str) -> str:
        """生成场景标签"""
        return section_label(rel_path)

    def vol_ch_label(self, vol: int, ch: int) -> str:
        """生成卷章标签"""
        return chapter_vol_label(vol, ch)
