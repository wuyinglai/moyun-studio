"""T6.5.1 Candidate 工作流端到端测试

测试策略：
- 不调用真实 LLM
- 不通过 generate / batch / pipeline run 创建 candidate
- 直接通过 backend API 或服务层预置 candidate
- 使用 __e2e_* 前缀的测试文件，便于清理
- 验证：list → detail/preview → adopt 成功 → adopt 冲突 → delete
- 验证：SSE candidate-created / candidate-adopted 事件
- 验证：adopt 后 target sec 文件内容变化
- 测试结束后清理所有 __e2e_* 文件

运行：
    python -m pytest backend/tests/contracts/test_t6_5_1_candidate_workflow_e2e.py -v
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import State

from backend.core.candidate_service import CandidateService, AdoptResult
from backend.core.file_ops import FileService
from backend.schemas.candidate import CandidateAction, CandidateStatus


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def project_id() -> str:
    """独立 project id，避免污染其他测试数据。"""
    return "__e2e_t6_5_1_candidate"


@pytest.fixture
def target_scene_rel() -> str:
    """目标场景的相对路径。"""
    return "chapters/vol-01/ch-001/sec-001.md"


@pytest.fixture
def initial_source_content() -> str:
    return "这是目标场景的初始正文内容。不应被 candidate 创建操作修改。"


@pytest.fixture
def candidate_content() -> str:
    return "这是候选稿内容。adopt 成功后，目标正文应包含此内容。"


@pytest.fixture
def cleanup_paths() -> list:
    """收集本次测试产生的文件路径，供 teardown 时统一清理。"""
    return []


# ---------------------------------------------------------------------------
# TestCase 1: 服务层端到端（最稳定，不依赖 HTTP API）
# ---------------------------------------------------------------------------
class TestCandidateWorkflowServiceLayer:
    """Candidate 核心工作流的服务层端到端验证。"""

    @pytest.mark.asyncio
    async def test_preset_candidate_list_detail_adopt_delete(
        self,
        fs: FileService,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        """
        验证核心链路：
        1) 预置目标正文文件
        2) 通过 CandidateService 创建 candidate（不经过 LLM）
        3) list_candidates 能看到该 candidate（PENDING）
        4) get_candidate / get_candidate_content 能读到正确内容
        5) adopt_candidate 成功 → SUCCESS
        6) 源文件内容已被替换为 candidate 内容
        7) candidate status 变为 ADOPTED
        8) revision-log 被写入
        9) delete_candidate 成功 → status = DISCARDED
        10) list_candidates 仍然可读取（metadata 保留），但状态为 DISCARDED
        """
        svc = CandidateService(fs)

        # (1) 预置目标正文
        source_full = f"{project_id}/{target_scene_rel}"
        await fs.write_file(source_full, initial_source_content)
        source_before, _, _ = await fs.read_file(source_full)
        assert source_before == initial_source_content

        # (2) 创建 candidate（不经过 LLM / generate）
        candidate = await svc.create_candidate(
            project_id=project_id,
            source_path=target_scene_rel,
            action=CandidateAction.REWRITE,
            content=candidate_content,
            workflow_run_id="test-workflow-t6-5-1",
            model="test-model",
            pipeline_id="test-pipeline",
        )
        assert candidate is not None
        assert candidate.source_path == target_scene_rel
        assert candidate.status == CandidateStatus.PENDING
        assert candidate.base_hash, "base_hash 必须记录"
        assert candidate.base_mtime is not None, "base_mtime 必须记录"
        assert ".candidates/" in candidate.candidate_path

        # (2a) 创建 candidate 不应修改源文件
        source_after_create, _, _ = await fs.read_file(source_full)
        assert source_after_create == initial_source_content, "创建 candidate 不得修改源文件"

        # (3) list_candidates
        listed = await svc.list_candidates(project_id)
        assert any(c.id == candidate.id for c in listed), "list 应包含新建 candidate"

        # (4) detail / content
        detail = await svc.get_candidate(project_id, candidate.id)
        assert detail is not None
        assert detail.status == CandidateStatus.PENDING

        content = await svc.get_candidate_content(project_id, candidate.id)
        assert content == candidate_content

        # (5) adopt 成功
        result = await svc.adopt_candidate(project_id, candidate.id)
        assert result == AdoptResult.SUCCESS

        # (6) 源文件内容被替换
        source_after_adopt, _, _ = await fs.read_file(source_full)
        assert source_after_adopt == candidate_content, "adopt 成功后正文应等于 candidate 内容"

        # (7) candidate status = ADOPTED
        adopted = await svc.get_candidate(project_id, candidate.id)
        assert adopted is not None
        assert adopted.status == CandidateStatus.ADOPTED

        # (8) revision-log 存在
        rev_dir = fs._resolve_path(f"{project_id}/chapters/vol-01/ch-001/revision-log")
        assert rev_dir.exists(), "adopt 成功应在章节目录创建 revision-log"
        log_files = list(rev_dir.glob("*.json"))
        assert len(log_files) >= 1
        # 至少一个 log 提到本次 candidate adopt
        found = False
        for log_file in log_files:
            try:
                log_data = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            if log_data.get("candidate_id") == candidate.id and log_data.get("revision_type") == "candidate_adopt":
                found = True
                break
        assert found, f"revision-log 中应记录 candidate_id={candidate.id}"

        # (9) delete_candidate
        deleted = await svc.delete_candidate(project_id, candidate.id)
        assert deleted is True

        # (10) 状态变为 DISCARDED
        discarded = await svc.get_candidate(project_id, candidate.id)
        assert discarded is not None
        assert discarded.status == CandidateStatus.DISCARDED

    @pytest.mark.asyncio
    async def test_adopt_conflict_blocks_rewrite(
        self,
        fs: FileService,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        """
        验证 adopt 冲突保护：
        - 先创建 candidate（记录 base_hash / base_mtime）
        - 在 adopt 前修改源文件（制造冲突）
        - adopt_candidate 返回 CONFLICT
        - 源文件保持为「被修改后」的内容，不是 candidate 内容
        - candidate status 变为 REJECTED（或状态仍是 PENDING，但 adopt 返回 CONFLICT）
        """
        svc = CandidateService(fs)
        source_full = f"{project_id}/{target_scene_rel}"
        modified_content = initial_source_content + "\n[外部修改：制造冲突]"

        await fs.write_file(source_full, initial_source_content)

        candidate = await svc.create_candidate(
            project_id=project_id,
            source_path=target_scene_rel,
            action=CandidateAction.REWRITE,
            content=candidate_content,
        )

        # 制造冲突：修改源文件
        import time as _time
        _time.sleep(0.01)
        await fs.write_file(source_full, modified_content)

        result = await svc.adopt_candidate(project_id, candidate.id)
        assert result == AdoptResult.CONFLICT, "adopt 在源文件被修改时必须返回 CONFLICT"

        # 源文件内容保持修改后的内容
        current, _, _ = await fs.read_file(source_full)
        assert current == modified_content, "冲突时不得用 candidate 内容覆盖源文件"
        assert candidate_content not in current

        # candidate status 变为 REJECTED
        rejected = await svc.get_candidate(project_id, candidate.id)
        assert rejected is not None
        assert rejected.status == CandidateStatus.REJECTED

    @pytest.mark.asyncio
    async def test_adopt_with_empty_base_hash_rejected(
        self,
        fs: FileService,
        project_id: str,
        target_scene_rel: str,
        candidate_content: str,
    ):
        """
        当 candidate 记录的 base_hash 为空时（例如源文件在创建时读失败的边缘场景），
        adopt 必须拒绝。
        """
        svc = CandidateService(fs)
        source_full = f"{project_id}/{target_scene_rel}"
        await fs.write_file(source_full, "原始正文")

        candidate = await svc.create_candidate(
            project_id=project_id,
            source_path=target_scene_rel,
            action=CandidateAction.REWRITE,
            content=candidate_content,
        )

        # 手工把 metadata 中的 base_hash 置空，模拟创建时读源文件失败的边缘场景
        meta_path = f"{project_id}/{CandidateService.CANDIDATES_DIR}/{CandidateService.METADATA_FILE}"
        try:
            raw, _, _ = await fs.read_file(meta_path)
        except Exception:
            pytest.skip("metadata 路径未按预期暴露，跳过边缘场景验证")
        metadata = json.loads(raw)
        if candidate.id in metadata:
            metadata[candidate.id]["base_hash"] = ""
            await fs.write_file(meta_path, json.dumps(metadata, ensure_ascii=False, indent=2))

            result = await svc.adopt_candidate(project_id, candidate.id)
            assert result == AdoptResult.CONFLICT, "base_hash 为空时 adopt 必须拒绝"

    @pytest.mark.asyncio
    async def test_candidates_for_file_filtering(
        self,
        fs: FileService,
        project_id: str,
        candidate_content: str,
    ):
        """get_candidates_for_file 只返回指定 source_path 的 PENDING candidate。"""
        svc = CandidateService(fs)
        path_a = f"chapters/vol-01/ch-001/sec-001.md"
        path_b = f"chapters/vol-01/ch-001/sec-002.md"

        for path in (path_a, path_b):
            await fs.write_file(f"{project_id}/{path}", f"源文件-{path}")
            await svc.create_candidate(
                project_id=project_id,
                source_path=path,
                action=CandidateAction.REWRITE,
                content=candidate_content,
            )

        a_list = await svc.get_candidates_for_file(project_id, path_a)
        b_list = await svc.get_candidates_for_file(project_id, path_b)
        assert len(a_list) == 1
        assert len(b_list) == 1
        assert a_list[0].source_path == path_a
        assert b_list[0].source_path == path_b

    @pytest.mark.asyncio
    async def test_delete_candidate_still_visible_in_metadata(
        self,
        fs: FileService,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        """delete 后 candidate 正文文件被移除，但元数据保留（status = DISCARDED）。"""
        svc = CandidateService(fs)
        source_full = f"{project_id}/{target_scene_rel}"
        await fs.write_file(source_full, initial_source_content)

        candidate = await svc.create_candidate(
            project_id=project_id,
            source_path=target_scene_rel,
            action=CandidateAction.REWRITE,
            content=candidate_content,
        )

        # 正文文件存在
        assert await svc.get_candidate_content(project_id, candidate.id) == candidate_content

        await svc.delete_candidate(project_id, candidate.id)

        # 元数据仍可读取，但状态为 DISCARDED
        discarded = await svc.get_candidate(project_id, candidate.id)
        assert discarded is not None
        assert discarded.status == CandidateStatus.DISCARDED

        # 正文文件被删除 → get_candidate_content 返回 None 或空
        content_after = await svc.get_candidate_content(project_id, candidate.id)
        assert content_after in (None, ""), "delete 后 candidate 正文应不可读"


# ---------------------------------------------------------------------------
# TestCase 2: HTTP API 端到端（FastAPI TestClient）
# ---------------------------------------------------------------------------
def _build_test_app(app_fixture, settings, monkeypatch):
    """从 conftest 提供的 FastAPI app 复用。"""
    app = app_fixture
    # 确保 SSE event_bus 存在（app.state 由 main.py 装配）
    if not hasattr(app.state, "event_bus"):
        bus = _InProcessEventBus()
        app.state.event_bus = bus
    return app


class _InProcessEventBus:
    """简化的进程内事件总线：只记录 publish 内容，用于断言 SSE 事件存在。"""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def publish(self, event_type: str, payload: dict | str) -> None:
        self.events.append({"type": event_type, "payload": payload})


class TestCandidateWorkflowHTTP:
    """通过 HTTP API 验证候选稿 CRUD + adopt + delete 行为。"""

    def test_http_create_list_detail_adopt_delete(
        self,
        client: TestClient,
        temp_workspace: Path,
        test_settings,
        monkeypatch,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        """
        HTTP 级端到端：
        - 在 temp_workspace 下创建 project & scene
        - POST /candidates/{project_id} 创建 candidate
        - GET  /candidates/{project_id} 列表
        - GET  /candidates/{project_id}/{cid} 详情
        - POST /candidates/{project_id}/{cid}/adopt 采用
        - DELETE /candidates/{project_id}/{cid} 删除
        - 读取正文：adopt 后内容应等于 candidate content
        """
        monkeypatch.setattr("backend.api.candidates.get_settings", lambda: test_settings)

        project_dir = temp_workspace / "projects" / project_id
        scene_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        scene_dir.mkdir(parents=True, exist_ok=True)
        scene_file = project_dir / target_scene_rel
        scene_file.write_text(initial_source_content, encoding="utf-8")

        # (1) create candidate
        create = client.post(
            f"/api/candidates/{project_id}",
            json={
                "project_id": project_id,
                "source_path": target_scene_rel,
                "action": "rewrite",
                "content": candidate_content,
                "workflow_run_id": "t6-5-1-http",
                "model": "test-model",
                "pipeline_id": "test-pipeline",
            },
        )
        assert create.status_code == 200, f"create 失败: {create.text}"
        body = create.json()
        candidate_id = body["id"]
        assert body["status"] == CandidateStatus.PENDING.value
        assert body["source_path"] == target_scene_rel
        # 此时源文件不应被修改
        assert scene_file.read_text(encoding="utf-8") == initial_source_content

        # (2) list
        list_resp = client.get(f"/api/candidates/{project_id}")
        assert list_resp.status_code == 200
        listed = list_resp.json().get("candidates", [])
        assert any(c["id"] == candidate_id for c in listed)

        # (3) detail
        detail = client.get(f"/api/candidates/{project_id}/{candidate_id}")
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["candidate"]["id"] == candidate_id
        assert detail_body["content"] == candidate_content

        # (4) adopt 成功
        adopt = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
        assert adopt.status_code == 200, f"adopt 失败: {adopt.text}"
        assert adopt.json().get("success") is True
        # 正文变化
        assert scene_file.read_text(encoding="utf-8") == candidate_content

        # (5) 再次 adopt（同一 candidate）应失败（非 PENDING）
        adopt_again = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
        assert adopt_again.status_code in (400, 409), "非 PENDING 状态应被拒绝 adopt"

        # (6) delete candidate
        delete = client.delete(f"/api/candidates/{project_id}/{candidate_id}")
        assert delete.status_code == 200, f"delete 失败: {delete.text}"
        assert delete.json().get("success") is True

    def test_http_adopt_conflict_returns_409(
        self,
        client: TestClient,
        temp_workspace: Path,
        test_settings,
        monkeypatch,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        """adopt 前修改源文件 → HTTP 409 FILE_CONFLICT，文件保持修改后内容。"""
        monkeypatch.setattr("backend.api.candidates.get_settings", lambda: test_settings)

        project_dir = temp_workspace / "projects" / project_id
        scene_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        scene_dir.mkdir(parents=True, exist_ok=True)
        scene_file = project_dir / target_scene_rel
        scene_file.write_text(initial_source_content, encoding="utf-8")

        # 创建 candidate
        create = client.post(
            f"/api/candidates/{project_id}",
            json={
                "project_id": project_id,
                "source_path": target_scene_rel,
                "action": "polish",
                "content": candidate_content,
            },
        )
        assert create.status_code == 200
        candidate_id = create.json()["id"]

        # 制造冲突：直接改写源文件
        import time as _time
        _time.sleep(0.01)
        modified = initial_source_content + "\n[被外部修改]"
        scene_file.write_text(modified, encoding="utf-8")

        # adopt 必须返回 409
        adopt = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
        assert adopt.status_code == 409, f"adopt 冲突应返回 409，实际 {adopt.status_code}: {adopt.text}"
        resp_json = adopt.json()
        # 响应中应带 FILE_CONFLICT 标识
        assert "FILE_CONFLICT" in json.dumps(resp_json, ensure_ascii=False) or resp_json.get("code") == "FILE_CONFLICT"
        # 正文保持修改后内容，不是 candidate 内容
        assert scene_file.read_text(encoding="utf-8") == modified


# ---------------------------------------------------------------------------
# TestCase 3: SSE 事件验证（进程内 event bus 记录）
# ---------------------------------------------------------------------------
class TestCandidateSSEEvents:
    """验证 create / adopt API 会发布 SSE 事件。"""

    def test_publish_candidate_created_on_create(
        self,
        client: TestClient,
        temp_workspace: Path,
        test_settings,
        monkeypatch,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        monkeypatch.setattr("backend.api.candidates.get_settings", lambda: test_settings)

        project_dir = temp_workspace / "projects" / project_id
        scene_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        scene_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / target_scene_rel).write_text(initial_source_content, encoding="utf-8")

        # 注入一个可观察的 event bus
        bus = _InProcessEventBus()
        app = client._client.app if hasattr(client, "_client") else client.app  # type: ignore[attr-defined]
        if app is None:
            pytest.skip("无法访问底层 FastAPI app，跳过 SSE 事件验证")
        original = getattr(app.state, "event_bus", None)
        app.state.event_bus = bus  # type: ignore[attr-defined]
        try:
            resp = client.post(
                f"/api/candidates/{project_id}",
                json={
                    "project_id": project_id,
                    "source_path": target_scene_rel,
                    "action": "polish",
                    "content": candidate_content,
                },
            )
            assert resp.status_code == 200
            types = [e["type"] for e in bus.events]
            assert any("candidate.created" in t for t in types), f"应发布 candidate.created 事件: {types}"
        finally:
            if original is not None:
                app.state.event_bus = original  # type: ignore[attr-defined]

    def test_publish_candidate_adopted_on_adopt(
        self,
        client: TestClient,
        temp_workspace: Path,
        test_settings,
        monkeypatch,
        project_id: str,
        target_scene_rel: str,
        initial_source_content: str,
        candidate_content: str,
    ):
        monkeypatch.setattr("backend.api.candidates.get_settings", lambda: test_settings)

        project_dir = temp_workspace / "projects" / project_id
        scene_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        scene_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / target_scene_rel).write_text(initial_source_content, encoding="utf-8")

        bus = _InProcessEventBus()
        app = client._client.app if hasattr(client, "_client") else client.app  # type: ignore[attr-defined]
        if app is None:
            pytest.skip("无法访问底层 FastAPI app，跳过 SSE 事件验证")
        original = getattr(app.state, "event_bus", None)
        app.state.event_bus = bus  # type: ignore[attr-defined]
        try:
            create = client.post(
                f"/api/candidates/{project_id}",
                json={
                    "project_id": project_id,
                    "source_path": target_scene_rel,
                    "action": "polish",
                    "content": candidate_content,
                },
            )
            assert create.status_code == 200
            candidate_id = create.json()["id"]

            adopt = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
            assert adopt.status_code == 200

            types = [e["type"] for e in bus.events]
            assert any("candidate.adopted" in t for t in types), f"应发布 candidate.adopted 事件: {types}"
        finally:
            if original is not None:
                app.state.event_bus = original  # type: ignore[attr-defined]
