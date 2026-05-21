"""墨韵 - Pipeline YAML 校验器测试

测试内容：
1. 所有现有 prompts/pipeline YAML 都能通过校验
2. step id 重复会失败
3. depends_on 指向不存在 step 会失败
4. prompt 文件不存在会失败
5. output_mode 非法会失败
6. overwrite/rewrite 对危险路径会产生 warning
"""

from pathlib import Path

import pytest
import yaml

from backend.core.pipeline_validator import validate_all_pipelines, validate_pipeline_file
from backend.schemas.pipeline_config import PipelineConfig


# ─── 辅助函数 ──────────────────────────────────────────────────

def _write_pipeline_yaml(
    tmp_path: Path,
    name: str,
    data: dict,
    prompts_root: Path | None = None,
) -> Path:
    """在 tmp_path 下创建一个 pipeline YAML 文件，并返回其路径"""
    pipeline_dir = tmp_path / "pipeline"
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = pipeline_dir / f"{name}.yaml"
    yaml_path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    # 同时创建 prompt 文件（如果 prompts_root 指定）
    root = prompts_root or tmp_path
    if "steps" in data:
        for step in data["steps"]:
            if "prompt" in step:
                prompt_file = root / f"{step['prompt']}.md"
                prompt_file.parent.mkdir(parents=True, exist_ok=True)
                if not prompt_file.exists():
                    prompt_file.write_text(f"# {step['id']} prompt\n", encoding="utf-8")
    return yaml_path


def _make_valid_pipeline(name: str = "test") -> dict:
    """生成一个合法的 pipeline 数据"""
    return {
        "name": name,
        "label": "测试管线",
        "steps": [
            {"id": "step1", "label": "步骤1", "prompt": f"pipeline/{name}/step1", "fallback": None},
        ],
    }


# ─── 1. 现有 YAML 通过校验 ────────────────────────────────────

class TestExistingPipelines:
    """校验项目中所有现有的 pipeline YAML"""

    @pytest.fixture
    def prompts_root(self) -> Path:
        """项目根目录下的 prompts/"""
        return Path(__file__).resolve().parent.parent.parent / "prompts"

    def test_all_existing_pipelines_valid(self, prompts_root: Path):
        """所有现有 YAML 都能通过校验"""
        pipeline_dir = prompts_root / "pipeline"
        if not pipeline_dir.exists():
            pytest.skip("prompts/pipeline 目录不存在")

        results = validate_all_pipelines(prompts_root)
        assert len(results) > 0, "应该至少有一个 pipeline YAML"

        for r in results:
            assert r.valid, (
                f"Pipeline {r.file} 校验失败:\n"
                + "\n".join(f"  ERROR: {e.message}" for e in r.errors)
            )


# ─── 2. step id 重复 ──────────────────────────────────────────

class TestDuplicateStepId:

    def test_duplicate_step_id_fails(self, tmp_path: Path):
        data = {
            "name": "dup",
            "label": "重复ID",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/dup/step1", "fallback": None},
                {"id": "step1", "label": "步骤2", "prompt": "pipeline/dup/step2", "fallback": None},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "dup", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid
        assert any("step id 重复" in e.message for e in result.errors)


# ─── 3. depends_on 引用不存在 step ────────────────────────────

class TestDependsOn:

    def test_depends_on_nonexistent_step_fails(self, tmp_path: Path):
        data = {
            "name": "deps",
            "label": "依赖测试",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/deps/step1", "fallback": None,
                 "depends_on": ["nonexistent"]},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "deps", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid
        assert any("depends_on" in e.field and "不存在" in e.message for e in result.errors)


# ─── 4. prompt 文件不存在 ─────────────────────────────────────

class TestPromptFileMissing:

    def test_missing_prompt_file_fails(self, tmp_path: Path):
        data = _make_valid_pipeline("missing")
        # 不创建 prompt 文件（不调用 _write_pipeline_yaml 的 prompt 创建）
        pipeline_dir = tmp_path / "pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = pipeline_dir / "missing.yaml"
        yaml_path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid
        assert any("prompt 文件不存在" in e.message for e in result.errors)


# ─── 5. output_mode 非法 ──────────────────────────────────────

class TestInvalidOutputMode:

    def test_invalid_output_mode_fails(self, tmp_path: Path):
        data = {
            "name": "badmode",
            "label": "非法模式",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/badmode/step1",
                 "fallback": None, "output_mode": "invalid_mode"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "badmode", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid
        assert any("output_mode 非法" in e.message for e in result.errors)


# ─── 6. 危险 output 路径 warning ──────────────────────────────

class TestDangerousOutputWarning:

    def test_overwrite_dangerous_path_warns(self, tmp_path: Path):
        data = {
            "name": "danger",
            "label": "危险路径",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/danger/step1",
                 "fallback": None, "output": "story-state.md"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "danger", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert result.valid  # warning 不阻止
        assert any("危险目标" in w.message for w in result.warnings)

    def test_overwrite_chapters_warns(self, tmp_path: Path):
        data = {
            "name": "chapters",
            "label": "章节路径",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/chapters/step1",
                 "fallback": None, "output": "chapters/vol-01/ch-001/sec-001.md"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "chapters", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert result.valid
        assert any("危险目标" in w.message for w in result.warnings)

    def test_deprecated_output_mode_warns(self, tmp_path: Path):
        data = {
            "name": "deprecated",
            "label": "旧模式",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/deprecated/step1",
                 "fallback": None, "output_mode": "overwrite"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "deprecated", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert result.valid
        assert any("不推荐" in w.message for w in result.warnings)

    def test_rewrite_output_mode_warns(self, tmp_path: Path):
        data = {
            "name": "rewrite_mode",
            "label": "重写模式",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/rewrite_mode/step1",
                 "fallback": None, "output_mode": "rewrite"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "rewrite_mode", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert result.valid
        assert any("不推荐" in w.message for w in result.warnings)


# ─── 7. 其他校验 ──────────────────────────────────────────────

class TestOtherValidations:

    def test_missing_name_fails(self, tmp_path: Path):
        """缺少 name 字段"""
        pipeline_dir = tmp_path / "pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = pipeline_dir / "noname.yaml"
        yaml_path.write_text(
            yaml.dump({"label": "无名称", "steps": []}, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid

    def test_empty_steps_fails(self, tmp_path: Path):
        """steps 为空列表"""
        data = {"name": "empty", "label": "空步骤", "steps": []}
        pipeline_dir = tmp_path / "pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = pipeline_dir / "empty.yaml"
        yaml_path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid

    def test_fallback_nonexistent_step_fails(self, tmp_path: Path):
        """fallback 引用不存在的 step"""
        data = {
            "name": "badfb",
            "label": "错误回退",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/badfb/step1",
                 "fallback": "nonexistent_step"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "badfb", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid
        assert any("fallback" in e.field and "不存在" in e.message for e in result.errors)

    def test_name_file_mismatch_warns(self, tmp_path: Path):
        """name 与文件名不一致时 warning"""
        data = _make_valid_pipeline("wrong_name")
        yaml_path = _write_pipeline_yaml(tmp_path, "mismatch", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert result.valid
        assert any("不一致" in w.message for w in result.warnings)

    def test_invalid_yaml_fails(self, tmp_path: Path):
        """YAML 解析失败"""
        pipeline_dir = tmp_path / "pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = pipeline_dir / "broken.yaml"
        yaml_path.write_text("name: [invalid\n  broken", encoding="utf-8")
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert not result.valid
        assert any("YAML 解析失败" in e.message for e in result.errors)

    def test_safe_output_no_warning(self, tmp_path: Path):
        """安全 output 路径不产生 warning"""
        data = {
            "name": "safe",
            "label": "安全路径",
            "steps": [
                {"id": "step1", "label": "步骤1", "prompt": "pipeline/safe/step1",
                 "fallback": None, "output": "materials/extracted/characters.md"},
            ],
        }
        yaml_path = _write_pipeline_yaml(tmp_path, "safe", data)
        result = validate_pipeline_file(yaml_path, tmp_path)
        assert result.valid
        assert not any("危险目标" in w.message for w in result.warnings)


# ─── 8. validate_all_pipelines ────────────────────────────────

class TestValidateAllPipelines:

    def test_validate_all_with_empty_dir(self, tmp_path: Path):
        """空目录返回空列表"""
        results = validate_all_pipelines(tmp_path)
        assert results == []

    def test_validate_all_multiple_files(self, tmp_path: Path):
        """多文件校验"""
        _write_pipeline_yaml(tmp_path, "p1", _make_valid_pipeline("p1"))
        _write_pipeline_yaml(tmp_path, "p2", _make_valid_pipeline("p2"))
        results = validate_all_pipelines(tmp_path)
        assert len(results) == 2
        assert all(r.valid for r in results)

    def test_validate_all_mixed_valid_invalid(self, tmp_path: Path):
        """混合有效和无效文件"""
        _write_pipeline_yaml(tmp_path, "good", _make_valid_pipeline("good"))
        # 创建一个无效的 YAML
        pipeline_dir = tmp_path / "pipeline"
        (pipeline_dir / "bad.yaml").write_text("name: bad\nlabel: bad\nsteps: []\n", encoding="utf-8")
        results = validate_all_pipelines(tmp_path)
        assert len(results) == 2
        good_results = [r for r in results if r.file == "good.yaml"]
        bad_results = [r for r in results if r.file == "bad.yaml"]
        assert len(good_results) == 1 and good_results[0].valid
        assert len(bad_results) == 1 and not bad_results[0].valid
