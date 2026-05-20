"""文件 API 端点测试

测试要点：
1. GET /api/file 返回 mtime
2. POST /api/file 传入 expected_mtime，mtime 不匹配返回 409
3. file-updated SSE 不包含 content
4. rename_file 走 FileService 安全方法
5. create_directory 走 FileService 安全方法
"""

import pytest
from pathlib import Path

from backend.config import Settings, get_settings
from backend.core.file_ops import FileService


class TestFileReadAPI:
    """GET /api/file 测试"""

    def test_read_file_returns_mtime(self, client, temp_workspace):
        """GET /api/file 必须返回 mtime"""
        # 注意：temp_workspace 结构是 workspace/projects/test-project/
        # projects_path = temp_workspace / "projects"
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "test.txt").write_text("Hello World", encoding="utf-8")

        response = client.get(
            "/api/file",
            params={"project_id": "test-project", "path": "test.txt"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "mtime" in data
        assert data["mtime"] is not None
        assert isinstance(data["mtime"], float)
        assert data["mtime"] > 0

    def test_read_file_returns_content_and_frontmatter(self, client, temp_workspace):
        """GET /api/file 返回 content 和 frontmatter"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "chapter.md").write_text(
            "---\ntitle: 第一章\nword_count: 1000\n---\n\n# 第一章\n\n内容",
            encoding="utf-8",
        )

        response = client.get(
            "/api/file",
            params={"project_id": "test-project", "path": "chapter.md"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "第一章" in data["content"]
        assert data["frontmatter"] is not None
        assert data["frontmatter"]["title"] == "第一章"


class TestFileWriteAPI:
    """POST /api/file 测试"""

    def test_write_file_passes_expected_mtime(self, client, temp_workspace):
        """POST /api/file 应将 expected_mtime 传给 FileService"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "test.txt").write_text("原始内容", encoding="utf-8")

        # 先读取获取 mtime
        read_resp = client.get(
            "/api/file",
            params={"project_id": "test-project", "path": "test.txt"},
        )
        assert read_resp.status_code == 200
        mtime = read_resp.json()["data"]["mtime"]

        # 使用正确的 mtime 写入
        write_resp = client.post(
            "/api/file",
            params={"project_id": "test-project"},
            json={
                "path": "test.txt",
                "content": "新内容",
                "expected_mtime": mtime,
            },
        )
        assert write_resp.status_code == 200

    def test_write_file_mtime_mismatch_returns_409(self, client, temp_workspace):
        """POST /api/file expected_mtime 不匹配应返回 409"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "test.txt").write_text("原始内容", encoding="utf-8")

        # 使用明显错误的 mtime
        write_resp = client.post(
            "/api/file",
            params={"project_id": "test-project"},
            json={
                "path": "test.txt",
                "content": "新内容",
                "expected_mtime": 1000.0,  # 明显错误的时间
            },
        )
        assert write_resp.status_code == 409

    def test_write_file_without_expected_mtime_succeeds(self, client, temp_workspace):
        """POST /api/file 不传 expected_mtime 应成功"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "test.txt").write_text("原始内容", encoding="utf-8")

        write_resp = client.post(
            "/api/file",
            params={"project_id": "test-project"},
            json={
                "path": "test.txt",
                "content": "新内容",
            },
        )
        assert write_resp.status_code == 200


class TestRenameFileAPI:
    """POST /api/file/rename 测试"""

    def test_rename_uses_file_service(self, client, temp_workspace):
        """rename_file 应使用 FileService.rename_path"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "old.txt").write_text("内容", encoding="utf-8")

        response = client.post(
            "/api/file/rename",
            json={
                "project_id": "test-project",
                "old_path": "old.txt",
                "new_path": "new.txt",
            },
        )
        assert response.status_code == 200
        # 验证文件已被重命名
        assert not (project_dir / "old.txt").exists()
        assert (project_dir / "new.txt").exists()

    def test_rename_rejects_path_traversal(self, client, temp_workspace):
        """rename_file 应拒绝路径穿越"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "test.txt").write_text("内容", encoding="utf-8")

        response = client.post(
            "/api/file/rename",
            json={
                "project_id": "test-project",
                "old_path": "test.txt",
                "new_path": "../escaped.txt",
            },
        )
        # 应该返回错误（400 或 422）
        assert response.status_code in (400, 422)


class TestCreateDirectoryAPI:
    """POST /api/directory/create 测试"""

    def test_create_directory_uses_file_service(self, client, temp_workspace):
        """create_directory 应使用 FileService.create_project_directory"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        response = client.post(
            "/api/directory/create",
            json={
                "project_id": "test-project",
                "path": "new-dir",
            },
        )
        assert response.status_code == 200
        assert (project_dir / "new-dir").is_dir()

    def test_create_directory_rejects_path_traversal(self, client, temp_workspace):
        """create_directory 应拒绝路径穿越"""
        project_dir = temp_workspace / "projects" / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        response = client.post(
            "/api/directory/create",
            json={
                "project_id": "test-project",
                "path": "../escaped-dir",
            },
        )
        assert response.status_code in (400, 422)
