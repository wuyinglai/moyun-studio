"""墨韵 - Lite API 契约测试

确保 Lite 模式核心行为不被后续修改破坏。
"""

import re

import pytest
from fastapi.testclient import TestClient

from backend.application.scene_service import SceneService


# 场景路径正则
SCENE_PATH_PATTERN = re.compile(r"^chapters/vol-\d+/ch-\d+/sec-\d+\.md$")


class TestLiteIdeasContract:
    """POST /api/lite/ideas 契约测试"""

    def test_ideas_returns_card_list(self, client: TestClient):
        """开局卡接口返回卡片列表"""
        resp = client.post("/api/lite/ideas", json={"seed": "test"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        cards = body["data"]["cards"]
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_idea_card_has_required_fields(self, client: TestClient):
        """每张开局卡必须包含必要字段"""
        resp = client.post("/api/lite/ideas", json={"seed": "test"})
        cards = resp.json()["data"]["cards"]
        for card in cards:
            assert "id" in card
            assert "title" in card
            assert "genre" in card
            assert "one_liner" in card
            assert "protagonist_hook" in card
            assert "core_conflict" in card
            assert "selling_point" in card


class TestLiteProjectsContract:
    """POST /api/lite/projects 契约测试"""

    def test_create_project_returns_project_id(self, client: TestClient):
        """创建项目后返回 project_id"""
        resp = client.post("/api/lite/projects", json={
            "card": {
                "id": "test-card",
                "title": "测试小说",
                "genre": "玄幻",
                "one_liner": "测试",
                "protagonist_hook": "测试",
                "core_conflict": "测试",
                "selling_point": "测试",
            },
            "prefs": {
                "style": "爽文",
                "intensity": "高",
                "pace": "快",
                "protagonist": "强",
                "likes": "",
                "dislikes": "",
                "genre_params": {},
            },
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "project_id" in data
        assert data["project_id"]

    def test_create_project_returns_first_file(self, client: TestClient):
        """创建项目后返回 first_file"""
        resp = client.post("/api/lite/projects", json={
            "card": {
                "id": "test-card",
                "title": "测试小说",
                "genre": "玄幻",
                "one_liner": "测试",
                "protagonist_hook": "测试",
                "core_conflict": "测试",
                "selling_point": "测试",
            },
            "prefs": {
                "style": "爽文",
                "intensity": "高",
                "pace": "快",
                "protagonist": "强",
                "likes": "",
                "dislikes": "",
                "genre_params": {},
            },
        })
        data = resp.json()["data"]
        assert "first_file" in data
        # first_file 必须符合场景路径格式
        assert SCENE_PATH_PATTERN.match(data["first_file"]), \
            f"first_file {data['first_file']} 不符合场景路径格式"


class TestLiteScenePathContract:
    """Lite 场景路径契约测试"""

    def test_scene_path_format(self):
        """Lite 返回的 target path 必须符合标准格式"""
        path = "chapters/vol-01/ch-001/sec-001.md"
        assert SCENE_PATH_PATTERN.match(path)

    def test_scene_path_uses_sec_not_section(self):
        """场景路径使用 sec 而非 section"""
        path = "chapters/vol-01/ch-001/sec-001.md"
        assert "sec-" in path
        assert "section-" not in path

    def test_scene_service_build_path(self):
        """SceneService.build_scene_path 生成标准路径"""
        path = SceneService.build_scene_path(1, 1, 1)
        assert SCENE_PATH_PATTERN.match(path)
        assert path == "chapters/vol-01/ch-001/sec-001.md"

    def test_scene_service_parse_path(self):
        """SceneService.parse_scene_path 正确解析"""
        info = SceneService.parse_scene_path("chapters/vol-01/ch-001/sec-003.md")
        assert info is not None
        assert info.volume == 1
        assert info.chapter == 1
        assert info.scene == 3


class TestLiteWriteActionContract:
    """Lite 写入操作契约测试"""

    def test_rewrite_action_generates_candidate(self):
        """rewrite 操作必须生成 candidate（策略验证）"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            "rewrite",
            "chapters/vol-01/ch-001/sec-001.md",
            True, True,
        ) is True

    def test_more_exciting_generates_candidate(self):
        """more_exciting 操作必须生成 candidate"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            "more_exciting",
            "chapters/vol-01/ch-001/sec-001.md",
            True, True,
        ) is True

    def test_more_reasonable_generates_candidate(self):
        """more_reasonable 操作必须生成 candidate"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            "more_reasonable",
            "chapters/vol-01/ch-001/sec-001.md",
            True, True,
        ) is True

    def test_lite_backend_falls_back_to_candidate_path_for_rewrite(self):
        """Lite 后端即使调用方未传 output_file，也不能把 rewrite 直接写回已有场景"""
        from backend.api.lite import _resolve_lite_output_file
        from backend.schemas.lite import LiteNextOptionCard, LiteWriteNextRequest

        req = LiteWriteNextRequest(
            project_id="test-project",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            action="rewrite",
            selected_card=LiteNextOptionCard(
                id="card-1",
                title="改稿",
                beat="加强冲突",
                scene="当前场景",
                payoff="兑现爽点",
                hook="留下钩子",
            ),
        )

        output_file = _resolve_lite_output_file(
            req,
            "chapters/vol-01/ch-001/sec-001.md",
            "已有正文内容，不能直接覆盖。",
            False,
        )

        assert output_file.startswith(".lite-candidates/")
        assert output_file.endswith(".rewrite.md")

    def test_chat_edit_generates_candidate(self):
        """chat_edit 操作必须生成 candidate"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            "chat_edit",
            "chapters/vol-01/ch-001/sec-001.md",
            True, True,
        ) is True

    def test_write_action_to_empty_scene_writes_directly(self):
        """write action 对空场景直接写入"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            "write",
            "chapters/vol-01/ch-001/sec-001.md",
            False, False,
        ) is False
