"""Lite 路径安全测试

覆盖 _validate_project_id, _validate_rel_path, _safe_project_path 的核心规则。
"""

from pathlib import Path

import pytest

from backend.api.lite import (
    LitePathError,
    _safe_project_path,
    _validate_project_id,
    _validate_rel_path,
)


# ═══════════════════════════════════════════════════════════
# _validate_project_id 测试
# ═══════════════════════════════════════════════════════════


class TestValidateProjectId:
    """project_id 安全验证"""

    def test_normal_id(self):
        assert _validate_project_id("abc123") == "abc123"

    def test_uuid_style_id(self):
        assert _validate_project_id("a1b2c3d4") == "a1b2c3d4"

    def test_empty_rejected(self):
        with pytest.raises(LitePathError, match="不能为空"):
            _validate_project_id("")

    def test_whitespace_rejected(self):
        with pytest.raises(LitePathError, match="不能为空"):
            _validate_project_id("   ")

    def test_dotdot_rejected(self):
        with pytest.raises(LitePathError, match="点号开头"):
            _validate_project_id("..")

    def test_traversal_slash_rejected(self):
        with pytest.raises(LitePathError, match="路径分隔符"):
            _validate_project_id("../other")

    def test_traversal_backslash_rejected(self):
        with pytest.raises(LitePathError, match="路径分隔符"):
            _validate_project_id("..\\other")

    def test_dot_prefix_rejected(self):
        with pytest.raises(LitePathError, match="点号开头"):
            _validate_project_id(".hidden")

    def test_slash_in_id_rejected(self):
        with pytest.raises(LitePathError, match="路径分隔符"):
            _validate_project_id("foo/bar")


# ═══════════════════════════════════════════════════════════
# _validate_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestValidateRelPath:
    """相对路径安全验证"""

    def test_normal_chapter_path(self):
        assert _validate_rel_path("chapters/vol-01/ch-001/sec-001.md") == "chapters/vol-01/ch-001/sec-001.md"

    def test_normal_state_file(self):
        assert _validate_rel_path("story-state.md") == "story-state.md"

    def test_empty_passes(self):
        assert _validate_rel_path("") == ""

    def test_none_passes(self):
        assert _validate_rel_path(None) is None

    def test_dotdot_traversal_rejected(self):
        with pytest.raises(LitePathError, match="遍历段"):
            _validate_rel_path("../../../etc/passwd")

    def test_mid_path_traversal_rejected(self):
        with pytest.raises(LitePathError, match="遍历段"):
            _validate_rel_path("chapters/../../../etc/passwd")

    def test_windows_traversal_rejected(self):
        with pytest.raises(LitePathError, match="遍历段"):
            _validate_rel_path("chapters\\..\\..\\etc\\passwd")

    def test_absolute_path_rejected(self):
        with pytest.raises(LitePathError, match="绝对路径"):
            _validate_rel_path("/etc/passwd")

    def test_windows_drive_rejected(self):
        with pytest.raises(LitePathError, match="Windows 盘符"):
            _validate_rel_path("C:\\Windows\\System32")

    def test_git_segment_rejected(self):
        with pytest.raises(LitePathError, match="禁止段"):
            _validate_rel_path(".git/config")

    def test_node_modules_rejected(self):
        with pytest.raises(LitePathError, match="禁止段"):
            _validate_rel_path("node_modules/package/index.js")

    def test_pycache_rejected(self):
        with pytest.raises(LitePathError, match="禁止段"):
            _validate_rel_path("__pycache__/module.pyc")

    def test_env_rejected(self):
        with pytest.raises(LitePathError, match="禁止段"):
            _validate_rel_path(".env")

    def test_config_json_rejected(self):
        with pytest.raises(LitePathError, match="禁止段"):
            _validate_rel_path(".config.json")

    def test_candidate_path_allowed(self):
        assert _validate_rel_path(".lite-candidates/abc.rewrite.md") == ".lite-candidates/abc.rewrite.md"

    def test_chapters_path_allowed(self):
        assert _validate_rel_path("chapters/vol-01/ch-001/sec-001.md") == "chapters/vol-01/ch-001/sec-001.md"

    def test_style_guide_allowed(self):
        assert _validate_rel_path("style-guide.md") == "style-guide.md"


# ═══════════════════════════════════════════════════════════
# _safe_project_path 测试
# ═══════════════════════════════════════════════════════════


class TestSafeProjectPath:
    """安全路径解析测试"""

    @pytest.fixture
    def project_dir(self, tmp_path):
        return tmp_path / "projects" / "test-project"

    def test_normal_chapter_path(self, project_dir):
        result = _safe_project_path(project_dir, "chapters/vol-01/ch-001/sec-001.md")
        assert str(result).replace("\\", "/").endswith("chapters/vol-01/ch-001/sec-001.md")

    def test_normal_state_file(self, project_dir):
        result = _safe_project_path(project_dir, "story-state.md")
        assert str(result).replace("\\", "/").endswith("story-state.md")

    def test_empty_path_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="不能为空"):
            _safe_project_path(project_dir, "")

    def test_traversal_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="遍历段"):
            _safe_project_path(project_dir, "../../../etc/passwd")

    def test_absolute_path_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="绝对路径"):
            _safe_project_path(project_dir, "/etc/passwd")

    def test_windows_drive_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="Windows 盘符"):
            _safe_project_path(project_dir, "C:\\Windows\\System32")

    def test_git_segment_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="禁止段"):
            _safe_project_path(project_dir, ".git/config")

    def test_node_modules_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="禁止段"):
            _safe_project_path(project_dir, "node_modules/x")

    def test_pycache_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="禁止段"):
            _safe_project_path(project_dir, "__pycache__/x")

    def test_env_rejected(self, project_dir):
        with pytest.raises(LitePathError, match="禁止段"):
            _safe_project_path(project_dir, ".env")

    def test_resolved_stays_inside_project(self, project_dir):
        """即使没有 .. 段，解析后的路径也必须在项目目录内"""
        result = _safe_project_path(project_dir, "chapters/vol-01/ch-001/sec-001.md")
        assert str(result).startswith(str(project_dir.resolve()))

    def test_dot_segments_normalized(self, project_dir):
        """单个 '.' 段被正确跳过"""
        result = _safe_project_path(project_dir, "./story-state.md")
        assert str(result).replace("\\", "/").endswith("story-state.md")
