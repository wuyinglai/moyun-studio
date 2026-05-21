"""墨韵 - File API 契约测试

确保 File API 的核心接口行为不被后续修改破坏。
"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from backend.core.exceptions import FileConflictError, ValidationError


class TestFileReadContract:
    """GET /api/file 契约测试"""

    def test_read_file_returns_required_fields(self, client: TestClient):
        """GET /api/file 必须返回 path, content, frontmatter, mtime"""
        resp = client.get("/api/file", params={
            "project_id": "test-project",
            "path": "outline.md",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "path" in data
        assert "content" in data
        assert "frontmatter" in data
        assert "mtime" in data

    def test_read_file_returns_hash(self, client: TestClient):
        """GET /api/file 应返回 hash 字段"""
        resp = client.get("/api/file", params={
            "project_id": "test-project",
            "path": "outline.md",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "hash" in data

    def test_read_nonexistent_file_returns_404(self, client: TestClient):
        """读取不存在的文件返回 404"""
        resp = client.get("/api/file", params={
            "project_id": "test-project",
            "path": "nonexistent.md",
        })
        assert resp.status_code == 404


class TestFileWriteContract:
    """POST /api/file 契约测试"""

    def test_write_file_supports_expected_mtime(self, client: TestClient):
        """POST /api/file 必须支持 expected_mtime"""
        read_resp = client.get("/api/file", params={
            "project_id": "test-project",
            "path": "outline.md",
        })
        mtime = read_resp.json()["data"]["mtime"]

        resp = client.post("/api/file?project_id=test-project", json={
            "path": "outline.md",
            "content": "# Updated outline",
            "expected_mtime": mtime,
        })
        assert resp.status_code == 200

    def test_write_file_supports_expected_hash(self, client: TestClient):
        """POST /api/file 必须支持 expected_hash"""
        read_resp = client.get("/api/file", params={
            "project_id": "test-project",
            "path": "outline.md",
        })
        file_hash = read_resp.json()["data"]["hash"]

        resp = client.post("/api/file?project_id=test-project", json={
            "path": "outline.md",
            "content": "# Updated outline",
            "expected_hash": file_hash,
        })
        assert resp.status_code == 200

    def test_mtime_conflict_returns_409(self, client: TestClient):
        """expected_mtime 不匹配时必须返回 HTTP 409"""
        resp = client.post("/api/file?project_id=test-project", json={
            "path": "outline.md",
            "content": "# Conflict test",
            "expected_mtime": 12345.0,
        })
        assert resp.status_code == 409
        body = resp.json()
        assert body.get("error", {}).get("code") == "FILE_CONFLICT" or "FILE_CONFLICT" in str(body)

    def test_hash_conflict_returns_409(self, client: TestClient):
        """expected_hash 不匹配时必须返回 HTTP 409"""
        resp = client.post("/api/file?project_id=test-project", json={
            "path": "outline.md",
            "content": "# Hash conflict test",
            "expected_hash": "0000000000000000",
        })
        assert resp.status_code == 409

    def test_write_file_without_conflict_check_succeeds(self, client: TestClient):
        """不带 expected_mtime/expected_hash 时写入成功"""
        resp = client.post("/api/file?project_id=test-project", json={
            "path": "outline.md",
            "content": "# No conflict check",
        })
        assert resp.status_code == 200


class TestFilePathValidation:
    """路径安全验证契约测试"""

    @pytest.mark.parametrize("dangerous_path", [
        "../secret.md",
        ".env",
        ".config.json",
        ".git/config",
    ])
    def test_dangerous_paths_rejected(self, client: TestClient, dangerous_path: str):
        """非法路径必须被拒绝"""
        resp = client.get("/api/file", params={
            "project_id": "test-project",
            "path": dangerous_path,
        })
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("dangerous_path", [
        "../secret.md",
        ".env",
        ".config.json",
        ".git/config",
    ])
    def test_dangerous_write_paths_rejected(self, client: TestClient, dangerous_path: str):
        """写入非法路径必须被拒绝"""
        resp = client.post("/api/file?project_id=test-project", json={
            "path": dangerous_path,
            "content": "malicious",
        })
        assert resp.status_code in (400, 404, 422)


class TestFileServicePathValidation:
    """FileService 路径安全验证契约测试（直接测试 FileService）"""

    @pytest.mark.parametrize("dangerous_path", [
        "../secret.md",
        ".env",
        ".config.json",
        ".git/config",
    ])
    def test_resolve_path_rejects_dangerous_paths(self, fs, dangerous_path: str):
        """_resolve_path 必须拒绝危险路径"""
        with pytest.raises(ValidationError):
            fs._resolve_path(f"test-project/{dangerous_path}")

    def test_path_traversal_rejected(self, fs):
        """路径遍历必须被拒绝"""
        with pytest.raises(ValidationError):
            fs._resolve_path("test-project/../../etc/passwd")

    def test_normal_path_accepted(self, fs):
        """正常路径必须被接受"""
        resolved = fs._resolve_path("test-project/outline.md")
        assert resolved is not None

    def test_scene_path_accepted(self, fs):
        """场景路径必须被接受"""
        resolved = fs._resolve_path("test-project/chapters/vol-01/ch-001/sec-001.md")
        assert resolved is not None


class TestFileConflictDetection:
    """FileService 冲突检测契约测试"""

    @pytest.mark.asyncio
    async def test_mtime_conflict_raises_file_conflict_error(self, fs):
        """mtime 不匹配必须抛出 FileConflictError"""
        # 先写入文件使其存在
        await fs.write_file("test-project/outline.md", "original content")
        with pytest.raises(FileConflictError):
            await fs.write_file(
                "test-project/outline.md",
                "conflict test",
                expected_mtime=12345.0,
            )

    @pytest.mark.asyncio
    async def test_hash_conflict_raises_file_conflict_error(self, fs):
        """hash 不匹配必须抛出 FileConflictError"""
        # 先写入文件使其存在
        await fs.write_file("test-project/outline.md", "original content")
        with pytest.raises(FileConflictError):
            await fs.write_file(
                "test-project/outline.md",
                "conflict test",
                expected_hash="0000000000000000",
            )

    @pytest.mark.asyncio
    async def test_correct_mtime_passes(self, fs):
        """正确的 mtime 通过冲突检测"""
        await fs.write_file("test-project/outline.md", "original content")
        _, _, mtime = await fs.read_file("test-project/outline.md")
        await fs.write_file(
            "test-project/outline.md",
            "updated content",
            expected_mtime=mtime,
        )

    @pytest.mark.asyncio
    async def test_correct_hash_passes(self, fs):
        """正确的 hash 通过冲突检测"""
        await fs.write_file("test-project/outline.md", "original content")
        content, _, _ = await fs.read_file("test-project/outline.md")
        file_hash = hashlib.md5(content.encode()).hexdigest()
        await fs.write_file(
            "test-project/outline.md",
            "updated content",
            expected_hash=file_hash,
        )
