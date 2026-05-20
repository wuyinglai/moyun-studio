"""墨韵 - Prompt 版本管理单元测试"""

import json
from pathlib import Path
import time

from backend.core.prompt_versioning import (
    archive_prompt,
    list_archives,
    restore_archive,
)


class TestArchivePrompt:
    """归档功能测试"""

    def test_archive_single_file(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        src = prompts / "generate" / "chapter" / "main.md"
        src.parent.mkdir(parents=True)
        src.write_text("original content", encoding="utf-8")

        result = archive_prompt(src, prompts)

        assert result is not None
        archive_dir = Path(result)
        assert archive_dir.is_dir()
        assert any(f.name == "main.md" for f in archive_dir.iterdir())
        assert (archive_dir / ".metadata.json").exists()

        meta = json.loads((archive_dir / ".metadata.json").read_text(encoding="utf-8"))
        assert meta["type"] == "file"
        assert "timestamp" in meta

    def test_archive_nonexistent_file_returns_none(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()

        result = archive_prompt(prompts / "nonexistent.md", prompts)
        assert result is None

    def test_archive_directory(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        pipeline_dir = prompts / "pipeline" / "my-pipeline"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "step1.md").write_text("step 1", encoding="utf-8")
        (pipeline_dir / "step2.md").write_text("step 2", encoding="utf-8")

        result = archive_prompt(pipeline_dir, prompts)

        assert result is not None
        archive_dir = Path(result)
        assert archive_dir.is_dir()
        # copytree nests inside archive_dir / rel, so we check deeper
        assert any(f.suffix == ".md" for f in archive_dir.rglob("*"))

    def test_archive_with_note(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        src = prompts / "test.md"
        src.write_text("content", encoding="utf-8")

        result = archive_prompt(src, prompts, note="手动修改")

        archive_dir = Path(result)
        meta = json.loads((archive_dir / ".metadata.json").read_text(encoding="utf-8"))
        assert meta["note"] == "手动修改"


class TestListArchives:
    """列出归档测试"""

    def test_list_empty_when_no_archive_dir(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()

        versions = list_archives(prompts)
        assert versions == []

    def test_list_archives_returns_all(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        src1 = prompts / "generate" / "chapter" / "main.md"
        src1.parent.mkdir(parents=True)
        src1.write_text("v1", encoding="utf-8")
        archive_prompt(src1, prompts, note="v1")

        time.sleep(1.1)  # ensure different timestamp

        src2 = prompts / "pipeline" / "diff-summary" / "analyze.md"
        src2.parent.mkdir(parents=True)
        src2.write_text("v2", encoding="utf-8")
        archive_prompt(src2, prompts, note="v2")

        versions = list_archives(prompts)
        assert len(versions) == 2

    def test_list_archives_filter_by_name(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        src1 = prompts / "generate" / "chapter" / "main.md"
        src1.parent.mkdir(parents=True)
        src1.write_text("chapter", encoding="utf-8")
        archive_prompt(src1, prompts, note="docs")

        src2 = prompts / "pipeline" / "diff-summary" / "analyze.md"
        src2.parent.mkdir(parents=True)
        src2.write_text("diff", encoding="utf-8")
        archive_prompt(src2, prompts, note="pipeline")

        # filter by substring match on archive entry name (rel path)
        versions = list_archives(prompts, pipeline_name="pipeline")
        assert len(versions) >= 1


class TestRestoreArchive:
    """恢复归档测试"""

    def test_restore_file_to_directory(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        src = prompts / "generate" / "chapter" / "main.md"
        src.parent.mkdir(parents=True)
        src.write_text("original", encoding="utf-8")

        archive_path = Path(archive_prompt(src, prompts))

        # modify original
        src.write_text("modified", encoding="utf-8")

        # restore — target is the parent directory
        ok = restore_archive(archive_path, src.parent)
        assert ok is True
        assert src.read_text(encoding="utf-8") == "original"

    def test_restore_nonexistent_archive_returns_false(self, tmp_path: Path):
        prompts = tmp_path / "prompts"
        prompts.mkdir()

        ok = restore_archive(tmp_path / "nonexistent", prompts / "target")
        assert ok is False
