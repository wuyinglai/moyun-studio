"""测试 LiteWriteNextResponse 的 fallback_used 字段"""

import pytest
from backend.schemas.lite import LiteWriteNextResponse


class TestLiteWriteNextResponseFallbackUsed:
    """测试 fallback_used 字段的默认值和序列化"""

    def test_fallback_used_default_false(self):
        """验证默认 fallback_used=False"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
        )
        assert response.fallback_used is False

    def test_fallback_used_can_be_true(self):
        """验证 fallback_used 可以设置为 True"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="使用了 fallback 模板",
            story_engine_summary={},
            fallback_used=True,
        )
        assert response.fallback_used is True

    def test_fallback_used_serialization_false(self):
        """验证 fallback_used=False 序列化包含该字段"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
            fallback_used=False,
        )
        data = response.model_dump()
        assert "fallback_used" in data
        assert data["fallback_used"] is False

    def test_fallback_used_serialization_true(self):
        """验证 fallback_used=True 序列化包含该字段"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="使用了 fallback 模板",
            story_engine_summary={},
            fallback_used=True,
        )
        data = response.model_dump()
        assert "fallback_used" in data
        assert data["fallback_used"] is True

    def test_response_with_all_fields_and_fallback(self):
        """验证完整 response 包含 fallback_used 字段"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={"主角": "张三"},
            chapter_plan="下一章计划",
            candidate_id="cand-123",
            source_file="chapters/vol-01/ch-001/sec-001.md",
            fallback_used=True,
        )
        data = response.model_dump()
        # 验证所有字段都存在
        assert data["file_path"] == "chapters/vol-01/ch-001/sec-001.md"
        assert data["candidate_id"] == "cand-123"
        assert data["fallback_used"] is True
        # 验证 JSON 序列化
        json_str = response.model_dump_json()
        assert '"fallback_used":true' in json_str or '"fallback_used": true' in json_str
