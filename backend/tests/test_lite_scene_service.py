"""墨韵 - Lite 场景路径服务测试

验证 Lite 场景路径和卷章场导航服务的行为。
"""

import pytest

from backend.application.lite_scene_service import (
    SECTIONS_PER_CHAPTER,
    CHAPTERS_PER_VOLUME,
    chapter_path,
    chapter_vol_label,
    extract_chapter_number,
    next_section_path,
    path_parts,
    section_label,
    section_path,
    LiteSceneLocation,
    LiteSceneService,
)


class TestSectionPath:
    """测试场景路径构建"""

    def test_section_path_builds_standard_path(self):
        """标准路径构建"""
        assert section_path(1, 1, 1) == "chapters/vol-01/ch-001/sec-001.md"
        assert section_path(1, 1, 5) == "chapters/vol-01/ch-001/sec-005.md"
        assert section_path(2, 12, 3) == "chapters/vol-02/ch-012/sec-003.md"

    def test_section_path_padding(self):
        """路径填充格式"""
        assert section_path(1, 1, 1) == "chapters/vol-01/ch-001/sec-001.md"
        assert section_path(10, 100, 5) == "chapters/vol-10/ch-100/sec-005.md"


class TestChapterPath:
    """测试章节路径构建"""

    def test_chapter_path_builds_standard_path(self):
        """章节起始路径"""
        assert chapter_path(1) == "chapters/vol-01/ch-001/sec-001.md"
        assert chapter_path(5) == "chapters/vol-01/ch-005/sec-001.md"
        assert chapter_path(12) == "chapters/vol-01/ch-012/sec-001.md"


class TestPathParts:
    """测试路径解析"""

    def test_path_parts_parses_standard_section(self):
        """解析标准场景路径"""
        vol, ch, sec = path_parts("chapters/vol-01/ch-003/sec-005.md")
        assert vol == 1
        assert ch == 3
        assert sec == 5

    def test_path_parts_handles_none(self):
        """处理 None 输入"""
        vol, ch, sec = path_parts(None)
        assert vol == 1
        assert ch == 1
        assert sec == 0

    def test_path_parts_with_various_volumes(self):
        """解析不同卷"""
        vol, ch, sec = path_parts("chapters/vol-02/ch-001/sec-001.md")
        assert vol == 2
        assert ch == 1
        assert sec == 1


class TestNextSectionPath:
    """测试下一场景推导"""

    def test_next_section_within_chapter(self):
        """章内下一场景"""
        assert next_section_path("chapters/vol-01/ch-001/sec-001.md") == "chapters/vol-01/ch-001/sec-002.md"
        assert next_section_path("chapters/vol-01/ch-001/sec-003.md") == "chapters/vol-01/ch-001/sec-004.md"

    def test_next_section_at_chapter_boundary(self):
        """章边界切换"""
        assert next_section_path("chapters/vol-01/ch-001/sec-005.md") == "chapters/vol-01/ch-002/sec-001.md"

    def test_next_section_at_volume_boundary(self):
        """卷边界切换"""
        assert next_section_path("chapters/vol-01/ch-012/sec-005.md") == "chapters/vol-02/ch-001/sec-001.md"

    def test_next_section_handles_none(self):
        """处理 None 输入"""
        result = next_section_path(None)
        assert "sec-001.md" in result


class TestSectionLabel:
    """测试场景标签"""

    def test_section_label_format(self):
        """标签格式"""
        assert section_label("chapters/vol-01/ch-001/sec-001.md") == "第1卷 第1章 第1场景"
        assert section_label("chapters/vol-02/ch-003/sec-005.md") == "第2卷 第3章 第5场景"

    def test_section_label_with_nonexistent(self):
        """处理 None"""
        vol, ch, sec = path_parts(None)
        assert vol == 1
        assert ch == 1
        assert sec == 0


class TestExtractChapterNumber:
    """测试章号提取"""

    def test_extract_chapter_number(self):
        """提取章号"""
        assert extract_chapter_number("chapters/vol-01/ch-003/sec-005.md") == 3
        assert extract_chapter_number("chapters/vol-02/ch-012/sec-001.md") == 12

    def test_extract_chapter_number_handles_none(self):
        """处理 None"""
        assert extract_chapter_number(None) == 0


class TestChapterVolLabel:
    """测试卷章标签"""

    def test_chapter_vol_label_format(self):
        """标签格式"""
        assert chapter_vol_label(1, 1) == "第1卷第1章"
        assert chapter_vol_label(2, 12) == "第2卷第12章"


class TestLiteSceneLocation:
    """测试场景位置数据类"""

    def test_location_creation(self):
        """创建位置"""
        location = LiteSceneLocation(volume=1, chapter=3, section=5)
        assert location.volume == 1
        assert location.chapter == 3
        assert location.section == 5

    def test_location_immutable(self):
        """位置不可变"""
        location = LiteSceneLocation(volume=1, chapter=3, section=5)
        with pytest.raises(AttributeError):
            location.volume = 2


class TestLiteSceneService:
    """测试 Lite 场景服务类"""

    def test_service_location(self):
        """获取位置"""
        svc = LiteSceneService()
        location = svc.location("chapters/vol-02/ch-005/sec-003.md")
        assert location.volume == 2
        assert location.chapter == 5
        assert location.section == 3

    def test_service_build_path(self):
        """构建路径"""
        svc = LiteSceneService()
        path = svc.build_path(1, 1, 1)
        assert path == "chapters/vol-01/ch-001/sec-001.md"

    def test_service_next_location(self):
        """下一位置"""
        svc = LiteSceneService()
        location = svc.next_location("chapters/vol-01/ch-001/sec-004.md")
        assert location.volume == 1
        assert location.chapter == 1
        assert location.section == 5

    def test_service_label(self):
        """生成标签"""
        svc = LiteSceneService()
        label = svc.label("chapters/vol-01/ch-002/sec-003.md")
        assert label == "第1卷 第2章 第3场景"

    def test_service_vol_ch_label(self):
        """生成卷章标签"""
        svc = LiteSceneService()
        label = svc.vol_ch_label(1, 5)
        assert label == "第1卷第5章"


class TestConstants:
    """测试常量定义"""

    def test_sections_per_chapter(self):
        """每章场景数"""
        assert SECTIONS_PER_CHAPTER == 5

    def test_chapters_per_volume(self):
        """每卷章数"""
        assert CHAPTERS_PER_VOLUME == 12
