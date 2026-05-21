"""质量审查 API 测试

重点验证：
1. batch 端点逐项容错：某个文件不存在时不中断整个批量
2. 不再出现 project_dir / target_file 直接路径拼接
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, get_settings
from backend.core.exceptions import (
    MoyunFileNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from backend.schemas.quality import QualityReviewResult, QualityScores


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def quality_settings(tmp_path):
    """测试用 Settings，指向临时目录"""
    projects = tmp_path / "projects"
    projects.mkdir()
    proj = projects / "test-project"
    proj.mkdir()
    (proj / "chapters").mkdir()
    (proj / "characters").mkdir()
    (proj / "materials").mkdir()
    (proj / "style-guide.md").write_text("# style", encoding="utf-8")
    (proj / "story-state.md").write_text("# state", encoding="utf-8")
    # 创建一个存在的场景文件
    (proj / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
    (proj / "chapters" / "vol-01" / "ch-001" / "sec-001.md").write_text(
        "# 场景一\n\n测试内容", encoding="utf-8"
    )

    prompts = tmp_path / "prompts" / "review"
    prompts.mkdir(parents=True)
    (prompts / "quality.md").write_text("审查: {{ content }}", encoding="utf-8")

    return Settings(
        debug=True,
        workspace_path=tmp_path,
        llm_provider="custom",
        llm_api_key="fake-key",
        llm_model="fake-model",
    )


@pytest.fixture
def quality_client(quality_settings):
    """返回配置好依赖覆盖的 TestClient"""
    from backend.main import create_app

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: quality_settings
    with TestClient(app) as c:
        yield c


def _mock_review_result():
    """返回一个简单的审查结果"""
    return QualityReviewResult(
        scores=QualityScores(),
        summary="测试审查结果",
        strengths=["优点1"],
        issues=[],
        suggestions=[],
    )


# ─── 测试：batch 逐项容错 ────────────────────────────────────

class TestQualityBatchItemErrors:
    """batch 端点逐项容错测试"""

    def test_batch_one_file_not_found_continues(self, quality_client, quality_settings):
        """batch 中一个文件不存在时，不中断整个批量，该文件标记 error"""
        # 准备：mock perform_review，对不存在的文件抛 ResourceNotFoundError
        good_result = _mock_review_result()

        async def mock_perform_review(project_id, target_file, chapter_title):
            if "missing" in target_file:
                raise ResourceNotFoundError(resource="file", identifier=target_file)
            return good_result

        with patch("backend.api.quality.QualityService") as MockSvc:
            svc_instance = MagicMock()
            svc_instance.perform_review = AsyncMock(side_effect=mock_perform_review)
            svc_instance.save_review_result = MagicMock()
            MockSvc.return_value = svc_instance

            resp = quality_client.post("/api/quality/review-batch", json={
                "project_id": "test-project",
                "target_files": [
                    "chapters/vol-01/ch-001/sec-001.md",
                    "chapters/missing/sec-999.md",
                ],
            })

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["succeeded"] == 1
        assert data["failed"] == 1

        # 成功的文件
        assert data["reviews"][0]["status"] == "success"
        assert data["reviews"][0]["target_file"] == "chapters/vol-01/ch-001/sec-001.md"

        # 不存在的文件
        assert data["reviews"][1]["status"] == "error"
        assert data["reviews"][1]["target_file"] == "chapters/missing/sec-999.md"

    def test_batch_validation_error_continues(self, quality_client, quality_settings):
        """batch 中一个文件路径非法时，不中断整个批量"""
        good_result = _mock_review_result()

        async def mock_perform_review(project_id, target_file, chapter_title):
            if ".." in target_file:
                raise ValidationError(f"路径不能包含 '..': {target_file}")
            return good_result

        with patch("backend.api.quality.QualityService") as MockSvc:
            svc_instance = MagicMock()
            svc_instance.perform_review = AsyncMock(side_effect=mock_perform_review)
            svc_instance.save_review_result = MagicMock()
            MockSvc.return_value = svc_instance

            resp = quality_client.post("/api/quality/review-batch", json={
                "project_id": "test-project",
                "target_files": [
                    "chapters/vol-01/ch-001/sec-001.md",
                    "../etc/passwd",
                ],
            })

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["succeeded"] == 1
        assert data["failed"] == 1
        assert data["reviews"][1]["status"] == "error"

    def test_batch_all_files_succeed(self, quality_client, quality_settings):
        """batch 中所有文件都成功时，全部返回 success"""
        good_result = _mock_review_result()

        with patch("backend.api.quality.QualityService") as MockSvc:
            svc_instance = MagicMock()
            svc_instance.perform_review = AsyncMock(return_value=good_result)
            svc_instance.save_review_result = MagicMock()
            MockSvc.return_value = svc_instance

            resp = quality_client.post("/api/quality/review-batch", json={
                "project_id": "test-project",
                "target_files": [
                    "chapters/vol-01/ch-001/sec-001.md",
                    "chapters/vol-01/ch-001/sec-002.md",
                ],
            })

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["succeeded"] == 2
        assert data["failed"] == 0

    def test_batch_no_project_dir_path_concat(self):
        """确认 quality.py 中不再出现 project_dir / target_file 直接拼接"""
        import ast
        import inspect
        from backend.api import quality as quality_module

        source = inspect.getsource(quality_module)
        tree = ast.parse(source)

        # 检查所有 BinOp 节点，不应出现 project_dir / target_file 或 project_dir / req.path
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                # 检查左侧是否为 project_dir
                if isinstance(node.left, ast.Name) and node.left.id == "project_dir":
                    # 右侧不能是 req.xxx 或包含 target_file / path 的属性
                    right_str = ast.dump(node.right)
                    if "target_file" in right_str or "req." in right_str or "path" in right_str:
                        violations.append(f"Found: project_dir / {right_str}")

        assert len(violations) == 0, f"Found path concatenation violations: {violations}"
