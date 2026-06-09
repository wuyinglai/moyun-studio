"""Scene Plan 质量评分 - Provenance 链路测试（T5.18-H1）

验证：
1. legacy candidate（无 .json metadata）不会导致评分脚本崩溃
2. scoring JSON 输出中包含 provenance/status 字段
3. note 字段不被 provenance 覆盖
4. 评分分数不受 provenance 影响
"""

import json
import sys
import pytest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "eval" / "scene_plan_quality_score.py"
sys.path.insert(0, str(PROJECT_ROOT))

# 从 scoring 脚本导入 provenance 相关函数
import importlib.util
spec = importlib.util.spec_from_file_location(
    "scene_plan_quality_score", SCRIPT_PATH
)
sp_module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(sp_module)
except Exception:
    sp_module = None


def test_module_loadable():
    """验证 scoring 模块可加载"""
    assert sp_module is not None, f"Failed to load {SCRIPT_PATH}"


@pytest.mark.skipif(sp_module is None, reason="scoring module not loadable")
class TestProvenanceBuild:
    """测试 provenance 构建逻辑"""

    def test_legacy_candidate_returns_legacy_status(self, tmp_path, monkeypatch):
        """当 candidate 无 .json metadata 时应返回 legacy_candidate"""
        # 构造一个不存在 metadata 的 candidate 场景
        build_provenance_info = sp_module.build_provenance_info

        result = build_provenance_info(
            project_id="demo-novel",
            candidate_id="cand_non_existent_001",
            scene_plan_path="materials/scene_plans/test.scene-plan.json",
            scene_plan_used=True,
        )

        assert result["status"] == "legacy_candidate"
        assert result["scene_plan_used"] is True
        assert result["scene_plan_hash"] is None
        assert result["scene_plan_path"] is not None  # 回退到 scene_plan_path
        assert "before T5.17-H2" in result["message"]

    def test_provenance_result_structure(self, tmp_path, monkeypatch):
        """验证 provenance 结果包含所有关键字段"""
        build_provenance_info = sp_module.build_provenance_info

        result = build_provenance_info(
            project_id="demo-novel",
            candidate_id="cand_no_meta",
            scene_plan_path="materials/scene_plans/test.json",
            scene_plan_used=False,
        )

        assert "status" in result
        assert "scene_plan_used" in result
        assert "scene_plan_hash" in result
        assert "scene_plan_path" in result
        assert "message" in result

    def test_legacy_status_for_missing_metadata_file(self, tmp_path, monkeypatch):
        """显式 mock metadata 文件不存在时的行为"""
        # mock Path.exists 返回 False
        original_exists = Path.exists

        def mock_exists(self):
            if ".json" in str(self) and ".candidates" in str(self):
                return False
            return original_exists(self)

        monkeypatch.setattr(Path, "exists", mock_exists)

        build_provenance_info = sp_module.build_provenance_info
        result = build_provenance_info(
            project_id="demo-novel",
            candidate_id="cand_mock_legacy",
            scene_plan_path="test.json",
            scene_plan_used=True,
        )

        assert result["status"] == "legacy_candidate"
        assert result["message"] is not None and len(result["message"]) > 0


class TestScoringJsonOutput:
    """验证 scoring 生成的 JSON 输出结构"""

    @pytest.fixture
    def cases_json_path(self):
        return PROJECT_ROOT / "docs" / "testing" / "artifacts" / "t5-scene-plan-quality-cases-2026-06.json"

    def test_cases_json_exists(self, cases_json_path):
        assert cases_json_path.exists(), f"cases json not found: {cases_json_path}"

    def test_cases_json_has_expected_structure(self, cases_json_path):
        data = json.loads(cases_json_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 2
        for case in data:
            assert "case_id" in case
            assert "baseline_candidate_id" in case
            assert "with_plan_candidate_id" in case

    def test_multi_score_json_has_provenance(self):
        """验证生成的 multi-score JSON 中包含 provenance 字段"""
        multi_score_path = (
            PROJECT_ROOT
            / "docs"
            / "testing"
            / "artifacts"
            / "t5-scene-plan-quality-multi-score-final-2026-06.json"
        )
        if not multi_score_path.exists():
            pytest.skip(f"multi-score json not generated yet: {multi_score_path}")
            return

        data = json.loads(multi_score_path.read_text(encoding="utf-8"))
        assert "cases" in data, "JSON 顶层缺少 cases"
        assert "note" in data, "JSON 顶层缺少 note 字段"

        for case in data["cases"]:
            assert "provenance" in case, f"Case {case.get('case_id')} 缺少 provenance 字段"
            assert "provenance_overall" in case, f"Case {case.get('case_id')} 缺少 provenance_overall"

            baseline_prov = case["provenance"]["baseline"]
            with_plan_prov = case["provenance"]["with_plan"]

            assert "status" in baseline_prov, "baseline provenance 缺少 status"
            assert "status" in with_plan_prov, "with_plan provenance 缺少 status"
            assert baseline_prov["status"] in ("legacy_candidate", "complete", "partial")
            assert with_plan_prov["status"] in ("legacy_candidate", "complete", "partial")

    def test_scores_preserved_after_adding_provenance(self):
        """验证添加 provenance 不会覆盖评分分数"""
        multi_score_path = (
            PROJECT_ROOT
            / "docs"
            / "testing"
            / "artifacts"
            / "t5-scene-plan-quality-multi-score-final-2026-06.json"
        )
        if not multi_score_path.exists():
            pytest.skip(f"multi-score json not generated yet: {multi_score_path}")
            return

        data = json.loads(multi_score_path.read_text(encoding="utf-8"))

        # sec-001: baseline=17, with-plan=15
        sec001 = next(c for c in data["cases"] if "sec-001" in c["case_id"])
        assert sec001["summary"]["baseline_total"] == 17, f"sec-001 baseline 分数应保持 17，实际 {sec001['summary']['baseline_total']}"
        assert sec001["summary"]["with_plan_total"] == 15, f"sec-001 with_plan 分数应保持 15"

        # sec-002: baseline=14, with-plan=14
        sec002 = next(c for c in data["cases"] if "sec-002" in c["case_id"])
        assert sec002["summary"]["baseline_total"] == 14
        assert sec002["summary"]["with_plan_total"] == 14

    def test_note_field_not_overwritten_by_provenance(self):
        """验证顶层 note 字段不被 provenance 覆盖"""
        multi_score_path = (
            PROJECT_ROOT
            / "docs"
            / "testing"
            / "artifacts"
            / "t5-scene-plan-quality-multi-score-final-2026-06.json"
        )
        if not multi_score_path.exists():
            pytest.skip(f"multi-score json not generated yet: {multi_score_path}")
            return

        data = json.loads(multi_score_path.read_text(encoding="utf-8"))
        note = data.get("note", "")
        assert isinstance(note, str)
        assert len(note) > 0, "note 字段不应为空"
        # note 应包含 T5.16.2 相关内容，不被 provenance 覆盖
        assert "T5.16.2" in note or "真实" in note or "历史测试数据" in note or "T5.18" in note


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
