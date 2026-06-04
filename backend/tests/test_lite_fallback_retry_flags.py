"""测试 LiteWriteNextResponse 的 fallback_used、retry_used、retry_count 字段"""

import pytest
from backend.schemas.lite import LiteWriteNextResponse


class TestLiteWriteNextResponseRetryFlags:
    """测试 retry 相关字段"""

    def test_retry_fields_default_values(self):
        """测试默认 retry_used 为 false，retry_count 为 0"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
        )
        assert response.retry_used is False
        assert response.retry_count == 0
        assert response.fallback_used is False

    def test_retry_used_true(self):
        """测试可以设置 retry_used 为 true"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
            retry_used=True,
        )
        assert response.retry_used is True
        assert response.retry_count == 0

    def test_retry_count_1(self):
        """测试可以设置 retry_count 为 1"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
            retry_used=True,
            retry_count=1,
        )
        assert response.retry_used is True
        assert response.retry_count == 1

    def test_all_three_flags_fallback_true_retry_true(self):
        """测试 fallback_used=true, retry_used=true 的组合（重试也失败）"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
            fallback_used=True,
            retry_used=True,
            retry_count=1,
        )
        assert response.fallback_used is True
        assert response.retry_used is True
        assert response.retry_count == 1

    def test_retry_fields_serialization(self):
        """测试 retry_used 和 retry_count 的序列化"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
            retry_used=True,
            retry_count=1,
        )
        data = response.model_dump()
        assert "retry_used" in data
        assert data["retry_used"] is True
        assert "retry_count" in data
        assert data["retry_count"] == 1

        # 测试 JSON 序列化
        json_str = response.model_dump_json()
        assert '"retry_used":true' in json_str or '"retry_used": true' in json_str
        assert '"retry_count":1' in json_str or '"retry_count": 1' in json_str

    def test_all_flags_serialization_together(self):
        """测试三个字段一起序列化"""
        response = LiteWriteNextResponse(
            file_path="chapters/vol-01/ch-001/sec-001.md",
            content="# 测试内容",
            quality_summary="质量正常",
            story_engine_summary={},
            fallback_used=True,
            retry_used=True,
            retry_count=1,
        )
        json_str = response.model_dump_json()
        assert '"fallback_used":true' in json_str or '"fallback_used": true' in json_str
        assert '"retry_used":true' in json_str or '"retry_used": true' in json_str
        assert '"retry_count":1' in json_str or '"retry_count": 1' in json_str
