"""墨韵 - 场景路径契约测试

验证 SceneService 的路径解析、构建、进位逻辑与契约文档一致。
契约文档：docs/contracts/scene-path-contract.md
"""

import pytest

from backend.application.scene_service import SceneService
from backend.domain.scene import SceneInfo


class TestParseScenePath:
    """parse_scene_path 契约测试"""

    def test_standard_path(self):
        """标准路径解析"""
        info = SceneService.parse_scene_path("chapters/vol-01/ch-001/sec-003.md")
        assert info is not None
        assert info.volume == 1
        assert info.chapter == 1
        assert info.scene == 3

    def test_high_numbers(self):
        """高编号路径"""
        info = SceneService.parse_scene_path("chapters/vol-12/ch-123/sec-999.md")
        assert info is not None
        assert info.volume == 12
        assert info.chapter == 123
        assert info.scene == 999

    def test_full_workspace_path(self):
        """包含项目前缀的完整路径"""
        info = SceneService.parse_scene_path(
            "my-project/chapters/vol-01/ch-002/sec-005.md"
        )
        assert info is not None
        assert info.volume == 1
        assert info.chapter == 2
        assert info.scene == 5

    def test_reject_non_scene_path(self):
        """非场景路径返回 None"""
        assert SceneService.parse_scene_path("foo/bar.md") is None

    def test_reject_missing_level(self):
        """缺少层级返回 None"""
        assert SceneService.parse_scene_path("chapters/vol-01/sec-001.md") is None

    def test_reject_ch_plan(self):
        """ch-plan.md 不是场景文件"""
        assert SceneService.parse_scene_path("chapters/vol-01/ch-001/ch-plan.md") is None

    def test_reject_extra_level(self):
        """路径中间有额外层级返回 None"""
        assert SceneService.parse_scene_path(
            "chapters/vol-01/extra/ch-001/sec-001.md"
        ) is None

    def test_reject_empty_string(self):
        """空字符串返回 None"""
        assert SceneService.parse_scene_path("") is None


class TestBuildScenePath:
    """build_scene_path 契约测试"""

    def test_standard_path(self):
        """标准路径构建"""
        assert SceneService.build_scene_path(1, 1, 3) == "chapters/vol-01/ch-001/sec-003.md"

    def test_zero_padding(self):
        """零填充：卷 2 位、章 3 位、场景 3 位"""
        assert SceneService.build_scene_path(1, 1, 1) == "chapters/vol-01/ch-001/sec-001.md"
        assert SceneService.build_scene_path(9, 99, 999) == "chapters/vol-09/ch-099/sec-999.md"

    def test_high_numbers(self):
        """高编号路径构建"""
        assert SceneService.build_scene_path(12, 123, 999) == "chapters/vol-12/ch-123/sec-999.md"


class TestIsSceneFile:
    """is_scene_file 契约测试"""

    def test_scene_file(self):
        assert SceneService.is_scene_file("chapters/vol-01/ch-001/sec-001.md") is True

    def test_ch_plan_not_scene(self):
        assert SceneService.is_scene_file("chapters/vol-01/ch-001/ch-plan.md") is False

    def test_random_file(self):
        assert SceneService.is_scene_file("story-state.md") is False


class TestGetNextScenePath:
    """get_next_scene_path 契约测试 — 核心进位规则"""

    # ── 场景进位 ──────────────────────────────────────────

    def test_sec_increment(self):
        """sec-001 → sec-002"""
        result = SceneService.get_next_scene_path("chapters/vol-01/ch-001/sec-001.md")
        assert result == "chapters/vol-01/ch-001/sec-002.md"

    def test_sec_mid_chapter(self):
        """sec-003 → sec-004"""
        result = SceneService.get_next_scene_path("chapters/vol-01/ch-001/sec-003.md")
        assert result == "chapters/vol-01/ch-001/sec-004.md"

    # ── 章进位 ──────────────────────────────────────────

    def test_sec005_to_next_chapter(self):
        """sec-005 → 下一章 sec-001（默认 scenes_per_chapter=5）"""
        result = SceneService.get_next_scene_path("chapters/vol-01/ch-001/sec-005.md")
        assert result == "chapters/vol-01/ch-002/sec-001.md"

    def test_last_scene_mid_volume(self):
        """ch-011/sec-005 → ch-012/sec-001"""
        result = SceneService.get_next_scene_path("chapters/vol-01/ch-011/sec-005.md")
        assert result == "chapters/vol-01/ch-012/sec-001.md"

    # ── 卷进位 ──────────────────────────────────────────

    def test_ch012_sec005_to_next_volume(self):
        """ch-012/sec-005 → vol-02/ch-001/sec-001（默认 chapters_per_volume=12）"""
        result = SceneService.get_next_scene_path("chapters/vol-01/ch-012/sec-005.md")
        assert result == "chapters/vol-02/ch-001/sec-001.md"

    def test_vol02_last_scene(self):
        """vol-02 最后一场景进位到 vol-03"""
        result = SceneService.get_next_scene_path("chapters/vol-02/ch-012/sec-005.md")
        assert result == "chapters/vol-03/ch-001/sec-001.md"

    # ── 自定义配置 ──────────────────────────────────────

    def test_custom_scenes_per_chapter(self):
        """自定义 scenes_per_chapter=3"""
        result = SceneService.get_next_scene_path(
            "chapters/vol-01/ch-001/sec-003.md",
            scenes_per_chapter=3,
        )
        assert result == "chapters/vol-01/ch-002/sec-001.md"

    def test_custom_chapters_per_volume(self):
        """自定义 chapters_per_volume=6"""
        result = SceneService.get_next_scene_path(
            "chapters/vol-01/ch-006/sec-005.md",
            chapters_per_volume=6,
        )
        assert result == "chapters/vol-02/ch-001/sec-001.md"

    # ── 非法路径 ────────────────────────────────────────

    def test_invalid_path_returns_none(self):
        """非法路径返回 None"""
        result = SceneService.get_next_scene_path("foo/bar.md")
        assert result is None

    def test_empty_string_returns_none(self):
        """空字符串返回 None"""
        result = SceneService.get_next_scene_path("")
        assert result is None


class TestBuildAndParseRoundTrip:
    """build ↔ parse 往返测试"""

    @pytest.mark.parametrize("vol,ch,sec", [
        (1, 1, 1),
        (1, 1, 5),
        (1, 12, 5),
        (3, 7, 2),
        (99, 999, 999),
    ])
    def test_round_trip(self, vol: int, ch: int, sec: int):
        """build → parse → 原始值"""
        path = SceneService.build_scene_path(vol, ch, sec)
        info = SceneService.parse_scene_path(path)
        assert info is not None
        assert info.volume == vol
        assert info.chapter == ch
        assert info.scene == sec
