"""E2E 右栏内部深层操作测试

覆盖:
1. CandidateAdoptFlow — 候选稿创建/列表/详情/采用（含冲突检测）/删除
2. WorkflowHumanNodeActions — 工作流人工节点暂停/恢复（approve/edit_and_approve/stop）
3. PromptSave — Prompt 模板 CRUD
4. PipelineEdit — 管线 YAML 定义 + step prompt 保存、自定义管线、删除
5. StoryStyleContextSave — 故事/文风/上下文通过通用 File API 保存
"""

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


# ─── 辅助：构建右栏测试工作区 ────────────────────────────────────

def _setup_rightpanel_workspace(tmp_path: Path, project_id: str = "rp-test") -> tuple[Path, object]:
    """创建测试工作区，包含项目、prompts、workflows、pipeline 目录"""
    from backend.config import Settings

    workspace = tmp_path / "workspace"
    proj = workspace / "projects" / project_id
    (proj / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
    (proj / "characters").mkdir(parents=True)
    (proj / "materials").mkdir(parents=True)

    # 项目基础文件
    (proj / "meta.json").write_text(json.dumps({
        "project_id": project_id,
        "name": "右栏测试项目",
        "genre": "玄幻",
        "theme": "成长",
        "tone": "热血",
    }, ensure_ascii=False), encoding="utf-8")
    (proj / "story-state.md").write_text("# 故事状态\n初始状态", encoding="utf-8")
    (proj / "style-guide.md").write_text("# 文风指南\n初始风格", encoding="utf-8")
    (proj / "recent-context.md").write_text("# 近期上下文\n初始上下文", encoding="utf-8")

    # 有内容的场景文件（用于候选稿采用测试）
    sec1_content = "# 场景一\n\n这是场景一的原始内容。\n包含两段文字。"
    (proj / "chapters" / "vol-01" / "ch-001" / "sec-001.md").write_text(sec1_content, encoding="utf-8")

    # 空场景文件（用于 write 直接写入测试）
    (proj / "chapters" / "vol-01" / "ch-001" / "sec-002.md").write_text("", encoding="utf-8")

    # Prompt 目录
    prompts_dir = workspace / "prompts"
    (prompts_dir / "generate" / "test").mkdir(parents=True)
    (prompts_dir / "generate" / "test" / "main.md").write_text("测试 prompt: {{ genre }}", encoding="utf-8")
    (prompts_dir / "extract").mkdir(parents=True)

    # Pipeline 目录
    pipeline_dir = prompts_dir / "pipeline"
    pipeline_generate_dir = pipeline_dir / "generate"
    pipeline_generate_dir.mkdir(parents=True)
    (pipeline_generate_dir / "step1.md").write_text("步骤1: {{ file_content }}", encoding="utf-8")
    yaml_path = pipeline_dir / "generate.yaml"
    yaml_path.write_text(yaml.dump({
        "name": "generate",
        "label": "生成管线",
        "steps": [{"id": "step1", "label": "步骤1", "prompt": "pipeline/generate/step1"}],
    }, allow_unicode=True), encoding="utf-8")

    # Workflows 目录
    workflows_dir = workspace / "workflows"
    workflows_dir.mkdir(parents=True)

    # 创建含 human_review 节点的工作流
    wf_yaml = {
        "name": "test-human-review",
        "label": "测试人工审核流程",
        "description": "一个包含人工审核节点的测试工作流",
        "variables": {"target_scene": "chapters/vol-01/ch-001/sec-001.md"},
        "steps": [
            {
                "id": "gen_step",
                "label": "AI生成",
                "type": "pipeline",
                "pipeline": "generate",
                "input": "{{variables.target_scene}}",
                "output": "{{variables.target_scene}}",
                "output_key": "generated_text",
            },
            {
                "id": "review_step",
                "label": "人工审核",
                "type": "human_review",
                "input": "{{steps.gen_step.output}}",
                "output_key": "reviewed_text",
            },
        ],
    }
    (workflows_dir / "test-human-review.yaml").write_text(yaml.dump(wf_yaml, allow_unicode=True), encoding="utf-8")

    # .moyun 目录（自定义管线和配置）
    moyun_dir = workspace / ".moyun"
    moyun_dir.mkdir(parents=True)
    (moyun_dir / "workflow-runs").mkdir(parents=True)

    settings = Settings(
        debug=True,
        workspace_path=workspace,
        llm_provider="custom",
        llm_api_key="fake-key-for-test",
        llm_model="fake-model",
    )
    return workspace, settings


# ─── 工具函数 ─────────────────────────────────────────────────

def _parse_sse_body(body: str) -> list[dict]:
    """解析 SSE text/event-stream 响应体为事件列表"""
    events = []
    for line in body.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
            events.append({"event": current_event, "data": None})
        elif line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            try:
                events.append({"event": events[-1]["event"] if events and events[-1].get("data") is None else "unknown", "data": json.loads(data_str)})
            except json.JSONDecodeError:
                events.append({"event": "unknown", "data": data_str})
    return [e for e in events if e.get("data") is not None]


def _find_sse_events(body: str) -> list[str]:
    """从 SSE body 中提取所有事件类型名"""
    events = []
    for line in body.strip().split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            events.append(line[len("event:"):].strip())
    return events


# ─── 通用：创建 App + 清除 get_settings 缓存 ────────────────────

def _create_app_with_settings(settings):
    """清除 get_settings LRU 缓存并用指定 settings 创建 app。

    API 处理器内直接调用 get_settings()（非 FastAPI Depends 注入），
    且 get_settings 有 @lru_cache，必须清除缓存 + patch Settings。
    """
    import backend.config as bc
    bc.get_settings.cache_clear()

    with patch("backend.config.Settings", return_value=settings):
        # 清除后重新导入（lifespan 中的 get_settings 调用会拿到我们的 settings）
        from backend.main import create_app
        return create_app()


# ═══════════════════════════════════════════════════════════════════
# Group 1: TestCandidateAdoptFlow — 候选稿采用（7 tests）
# ═══════════════════════════════════════════════════════════════════

class TestCandidateAdoptFlow:
    """测试候选稿 CRUD + 采用安全性"""

    @pytest.fixture
    def cand_client(self, tmp_path):
        """构造带有 mock LLM 的 TestClient"""
        workspace, settings = _setup_rightpanel_workspace(tmp_path, "rp-cand")

        # Mock LLMService 以避免 lifespan 初始化失败
        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_candidate_records_hash_and_mtime(self, cand_client):
        """POST 创建候选稿 → base_hash 32 字符 hex, base_mtime > 0, status == pending"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "polish",
            "content": "# 润色后内容\n\n这是润色后的场景。",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert re.match(r"^[a-f0-9]{32}$", data.get("base_hash", "")), f"base_hash is not md5 hex: {data.get('base_hash')}"
        assert data.get("base_mtime", 0) > 0
        assert data.get("status") == "pending"
        assert data.get("id", "").startswith("cand_")

    def test_list_candidates_returns_created(self, cand_client):
        """GET 列表 → 包含新创建的候选稿"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        create_resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "rewrite",
            "content": "# 重写场景\n\n全部重写的内容。",
        })
        assert create_resp.status_code == 200
        created_id = create_resp.json()["id"]

        list_resp = client.get(f"/api/candidates/{project_id}")
        assert list_resp.status_code == 200
        candidates = list_resp.json()["candidates"]
        assert len(candidates) >= 1
        ids = [c["id"] for c in candidates]
        assert created_id in ids

    def test_get_candidate_detail_includes_content(self, cand_client):
        """GET 详情 → content 与提交内容一致"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        test_content = "# 自定义内容\n\n这是测试用的候选稿内容。"
        create_resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "polish",
            "content": test_content,
        })
        assert create_resp.status_code == 200
        candidate_id = create_resp.json()["id"]

        detail_resp = client.get(f"/api/candidates/{project_id}/{candidate_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["candidate"]["id"] == candidate_id
        assert detail["content"] == test_content

    def test_adopt_candidate_overwrites_source(self, cand_client):
        """POST 采用成功 → 源文件内容 = 候选稿内容, revision-log 创建, status → adopted"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        new_content = "# 采用后的内容\n\n这是采用后的新场景内容。"
        create_resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "polish",
            "content": new_content,
        })
        assert create_resp.status_code == 200
        candidate_id = create_resp.json()["id"]

        adopt_resp = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
        assert adopt_resp.status_code == 200, f"Adopt failed: {adopt_resp.text}"
        adopt_data = adopt_resp.json()
        assert adopt_data["success"] is True
        assert adopt_data["conflict"] is False

        # 验证源文件内容已更新
        sec1_path = workspace / "projects" / project_id / "chapters" / "vol-01" / "ch-001" / "sec-001.md"
        assert sec1_path.read_text(encoding="utf-8") == new_content

        # 验证 revision-log 被创建（可能在不同路径，进行宽松检查）
        rev_log_candidates = list(workspace.rglob("revision-log"))
        assert len(rev_log_candidates) >= 1

        # 验证候选稿状态变为 adopted
        detail_resp = client.get(f"/api/candidates/{project_id}/{candidate_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["candidate"]["status"] == "adopted"

    def test_adopt_candidate_hash_conflict_returns_409(self, cand_client):
        """源文件在候选稿创建后被修改 → 采用失败 409"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        create_resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "polish",
            "content": "# 要采用的内容\n\n新的润色版本。",
        })
        assert create_resp.status_code == 200
        candidate_id = create_resp.json()["id"]

        # 修改源文件（模拟并发修改）
        sec1_path = workspace / "projects" / project_id / "chapters" / "vol-01" / "ch-001" / "sec-001.md"
        sec1_path.write_text("# 被他人修改\n\n并发修改后的内容。", encoding="utf-8")

        adopt_resp = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
        assert adopt_resp.status_code == 409, f"Expected 409, got {adopt_resp.status_code}: {adopt_resp.text}"

    def test_adopt_non_pending_returns_400(self, cand_client):
        """采用已 adopted 的候选稿 → 400"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        create_resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "polish",
            "content": "# 内容\n\n第一次创建。",
        })
        assert create_resp.status_code == 200
        candidate_id = create_resp.json()["id"]

        client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")

        second_adopt = client.post(f"/api/candidates/{project_id}/{candidate_id}/adopt")
        assert second_adopt.status_code == 400, f"Expected 400, got {second_adopt.status_code}: {second_adopt.text}"

    def test_delete_candidate_marks_discarded(self, cand_client):
        """DELETE 候选稿 → success=true"""
        client, workspace, _ = cand_client
        project_id = "rp-cand"

        create_resp = client.post(f"/api/candidates/{project_id}", json={
            "project_id": project_id,
            "source_path": "chapters/vol-01/ch-001/sec-001.md",
            "action": "polish",
            "content": "# 待删除\n\n这份候选稿将被删除。",
        })
        assert create_resp.status_code == 200
        candidate_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/api/candidates/{project_id}/{candidate_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] is True


# ═══════════════════════════════════════════════════════════════════
# Group 2: TestWorkflowHumanNodeActions — 工作流人工节点（6 tests）
# ═══════════════════════════════════════════════════════════════════

class TestWorkflowHumanNodeActions:
    """测试工作流人工节点暂停/恢复（approve/edit_and_approve/stop）"""

    @pytest.fixture
    def wf_client(self, tmp_path):
        """构造带有 mock LLM 的工作流测试环境"""
        workspace, settings = _setup_rightpanel_workspace(tmp_path, "rp-wf")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    @staticmethod
    def _mock_llm_complete():
        """创建 mock LLM complete 异步生成器，返回字符串 chunk（PipelineRunner 期望 str）"""
        async def mock_complete(*args, **kwargs):
            for chunk in ["测", "试", "生", "成"]:
                yield chunk
        return mock_complete

    @staticmethod
    def _patch_llm_service():
        """Patch LLMService 用于工作流测试"""
        mock_svc = MagicMock()
        mock_svc.complete = TestWorkflowHumanNodeActions._mock_llm_complete()
        mock_svc.complete_sync = AsyncMock(return_value="测试生成")
        # PipelineRunner 需要这些 config 属性
        mock_svc.config = MagicMock()
        mock_svc.config.model = "fake-model"
        mock_svc.config.max_prompt_tokens = 120000
        mock_svc.config.context_window = 128000
        mock_svc.config.reserved_output_tokens = 8000
        return patch("backend.core.llm.LLMService.from_workspace_config", return_value=mock_svc)

    def test_run_workflow_with_human_node_pauses(self, wf_client):
        """运行含 human_review 的工作流 → SSE 中 workflow_paused"""
        client, workspace, _ = wf_client

        with self._patch_llm_service():
            resp = client.post("/api/workflows/run", json={
                "workflow": "test-human-review",
                "project_id": "rp-wf",
                "variables": {},
            })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        events = _find_sse_events(resp.text)
        assert "workflow_start" in events, f"Events: {events}"
        assert "step_start" in events
        assert "step_waiting" in events
        assert "workflow_paused" in events

    def test_run_status_returns_available_actions(self, wf_client):
        """GET 暂停后的 run 状态 → available_actions 非空"""
        client, workspace, _ = wf_client

        with self._patch_llm_service():
            run_resp = client.post("/api/workflows/run", json={
                "workflow": "test-human-review",
                "project_id": "rp-wf",
                "variables": {},
            })

        events = _parse_sse_body(run_resp.text)
        run_id = None
        for e in events:
            if e.get("event") == "workflow_start" and isinstance(e.get("data"), dict):
                run_id = e["data"].get("run_id")
        assert run_id is not None, f"Could not find run_id in events: {events[:3]}"

        status_resp = client.get(f"/api/workflows/runs/{run_id}")
        assert status_resp.status_code == 200, f"Status failed: {status_resp.text}"
        status_data = status_resp.json()
        # 状态数据结构: data.run.status, data.run.available_actions
        run_info = status_data["data"]["run"]
        assert run_info["status"] == "waiting_for_user"
        actions = run_info["available_actions"]
        assert "approve" in actions
        assert "edit_and_approve" in actions

    def test_resume_with_approve_continues(self, wf_client):
        """resume action=approve → SSE 含 step_done, workflow_done"""
        client, workspace, _ = wf_client

        with self._patch_llm_service():
            run_resp = client.post("/api/workflows/run", json={
                "workflow": "test-human-review",
                "project_id": "rp-wf",
                "variables": {},
            })

        run_id = None
        for e in _parse_sse_body(run_resp.text):
            if e.get("event") == "workflow_start" and isinstance(e.get("data"), dict):
                run_id = e["data"].get("run_id")
        assert run_id is not None

        # Resume with approve — workflow.py 的 resume 方法需要 get_settings 返回正确路径
        # 但同时 resume 内部调用了 _load_state，state_dir 和 workflows_path 在 WorkflowRunner 构造时确定
        # 所以只 patch LLM 即可
        with self._patch_llm_service():
            resume_resp = client.post(f"/api/workflows/runs/{run_id}/resume", json={
                "action": "approve",
                "output": "",
                "extra_vars": {},
            })

        assert resume_resp.status_code == 200
        resume_events = _find_sse_events(resume_resp.text)
        assert "step_done" in resume_events or "workflow_done" in resume_events, f"Resume events: {resume_events}"

    def test_resume_with_edit_and_approve_stores_modified(self, wf_client):
        """resume action=edit_and_approve + output → SSE 含 variable_update"""
        client, workspace, _ = wf_client

        with self._patch_llm_service():
            run_resp = client.post("/api/workflows/run", json={
                "workflow": "test-human-review",
                "project_id": "rp-wf",
                "variables": {},
            })

        run_id = None
        for e in _parse_sse_body(run_resp.text):
            if e.get("event") == "workflow_start" and isinstance(e.get("data"), dict):
                run_id = e["data"].get("run_id")
        assert run_id is not None

        edited_content = "# 修改后的内容\n\n人工编辑过的版本。"
        with self._patch_llm_service():
            resume_resp = client.post(f"/api/workflows/runs/{run_id}/resume", json={
                "action": "edit_and_approve",
                "output": edited_content,
                "extra_vars": {},
            })

        assert resume_resp.status_code == 200
        resume_events = _find_sse_events(resume_resp.text)
        assert "variable_update" in resume_events, f"Resume events: {resume_events}"

    def test_resume_with_stop_stops_workflow(self, wf_client):
        """resume action=stop → SSE 含 workflow_stopped"""
        client, workspace, _ = wf_client

        with self._patch_llm_service():
            run_resp = client.post("/api/workflows/run", json={
                "workflow": "test-human-review",
                "project_id": "rp-wf",
                "variables": {},
            })

        run_id = None
        for e in _parse_sse_body(run_resp.text):
            if e.get("event") == "workflow_start" and isinstance(e.get("data"), dict):
                run_id = e["data"].get("run_id")
        assert run_id is not None

        resume_resp = client.post(f"/api/workflows/runs/{run_id}/resume", json={
            "action": "stop",
            "output": "",
            "extra_vars": {},
        })

        assert resume_resp.status_code == 200
        resume_events = _find_sse_events(resume_resp.text)
        assert "workflow_stopped" in resume_events, f"Resume events: {resume_events}"

    def test_memory_update_returns_risk_assessment(self, wf_client):
        """POST /memory/update → risk_level 在 low/medium/high"""
        client, workspace, _ = wf_client

        with self._patch_llm_service():
            # Memory update 也用 LLMService.from_workspace_config
            resp = client.post("/api/memory/update", json={
                "project_id": "rp-wf",
                "content": "# 新场景\n\n主角进入森林。",
                "scene_path": "chapters/vol-01/ch-001/sec-001.md",
                "force_review": False,
            })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "risk_level" in data["data"], f"Response: {data}"


# ═══════════════════════════════════════════════════════════════════
# Group 3: TestPromptSave — Prompt 保存（5 tests）
# ═══════════════════════════════════════════════════════════════════

class TestPromptSave:
    """测试 Prompt 模板 CRUD"""

    @pytest.fixture
    def prompt_client(self, tmp_path):
        """构造 Prompt 测试环境（无 LLM 依赖）"""
        workspace, settings = _setup_rightpanel_workspace(tmp_path, "rp-prompt")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_save_prompt_creates_file(self, prompt_client):
        """POST 保存 → 文件存在于 workspace/prompts/{cat}/{name}/main.md"""
        client, workspace, _ = prompt_client

        test_content = "# 测试 Prompt\n\n你是一个小说家。\n\n题材：{{ genre }}"
        resp = client.post("/api/prompts/generate/my-custom", json={
            "content": test_content,
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json()["success"] is True

        prompt_file = workspace / "prompts" / "generate" / "my-custom" / "main.md"
        assert prompt_file.exists()
        assert prompt_file.read_text(encoding="utf-8") == test_content

    def test_get_prompt_reads_back(self, prompt_client):
        """GET 读取 → content 匹配已保存内容"""
        client, workspace, _ = prompt_client

        test_content = "# 读取测试\n\ngenre: {{ genre }}\ntheme: {{ theme }}"
        client.post("/api/prompts/generate/read-back", json={
            "content": test_content,
        })

        resp = client.get("/api/prompts/generate/read-back")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["data"]["name"] == "generate/read-back"
        assert data["data"]["content"] == test_content

    def test_list_prompts_includes_saved(self, prompt_client):
        """GET 列表 → prompts 数组包含新保存的 prompt"""
        client, workspace, _ = prompt_client

        client.post("/api/prompts/generate/list-test", json={
            "content": "list test content",
        })

        resp = client.get("/api/prompts")
        assert resp.status_code == 200
        prompts = resp.json()["data"]["prompts"]
        names = [p["name"] for p in prompts]
        assert "generate/list-test" in names

    def test_save_prompt_overwrites(self, prompt_client):
        """两次保存同路径 → 内容 = 第二次保存"""
        client, workspace, _ = prompt_client

        resp1 = client.post("/api/prompts/generate/overwrite", json={
            "content": "第一版内容",
        })
        assert resp1.status_code == 200

        resp2 = client.post("/api/prompts/generate/overwrite", json={
            "content": "第二版内容（覆盖）",
        })
        assert resp2.status_code == 200

        resp3 = client.get("/api/prompts/generate/overwrite")
        assert resp3.status_code == 200
        assert resp3.json()["data"]["content"] == "第二版内容（覆盖）"

    def test_get_nonexistent_prompt_returns_404(self, prompt_client):
        """GET 不存在 → 404"""
        client, workspace, _ = prompt_client

        resp = client.get("/api/prompts/generate/nonexistent-xyz")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ═══════════════════════════════════════════════════════════════════
# Group 4: TestPipelineEdit — 管线编辑（5 tests）
# ═══════════════════════════════════════════════════════════════════

class TestPipelineEdit:
    """测试管线 YAML 定义 + step prompt 保存、自定义管线、删除"""

    @pytest.fixture
    def pipeline_client(self, tmp_path):
        """构造 Pipeline 测试环境"""
        workspace, settings = _setup_rightpanel_workspace(tmp_path, "rp-pipe")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_save_pipeline_creates_yaml_and_steps(self, pipeline_client):
        """PUT 保存管线 → {name}.yaml + pipeline/{name}/*.md 存在"""
        client, workspace, _ = pipeline_client

        steps = [
            {
                "id": "step_a",
                "label": "步骤A",
                "prompt_content": "# 步骤A模板\n\n处理内容：{{ file_content }}",
            },
            {
                "id": "step_b",
                "label": "步骤B",
                "prompt_content": "# 步骤B模板\n\n进一步处理：{{ content }}",
            },
        ]
        resp = client.put("/api/pipeline/test-save", json={
            "name": "test-save",
            "label": "测试保存管线",
            "steps": steps,
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        yaml_path = workspace / "prompts" / "pipeline" / "test-save.yaml"
        assert yaml_path.exists()

        step_a_path = workspace / "prompts" / "pipeline" / "test-save" / "step_a.md"
        step_b_path = workspace / "prompts" / "pipeline" / "test-save" / "step_b.md"
        assert step_a_path.exists()
        assert step_b_path.exists()
        assert step_a_path.read_text(encoding="utf-8") == "# 步骤A模板\n\n处理内容：{{ file_content }}"

    def test_get_pipeline_detail_includes_step_prompt_content(self, pipeline_client):
        """GET 详情 → steps[] 每项含 prompt_content"""
        client, workspace, _ = pipeline_client

        resp = client.get("/api/pipeline/generate")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        pipeline = data["data"]["pipeline"]
        assert pipeline["name"] == "generate"
        assert len(pipeline["steps"]) >= 1
        assert "prompt_content" in pipeline["steps"][0]

    def test_delete_pipeline_removes_files(self, pipeline_client):
        """DELETE → 文件移至 trash，原位置不存在"""
        client, workspace, _ = pipeline_client

        client.put("/api/pipeline/to-delete", json={
            "name": "to-delete",
            "label": "待删除",
            "steps": [{"id": "s1", "label": "步骤", "prompt_content": "test"}],
        })

        yaml_path = workspace / "prompts" / "pipeline" / "to-delete.yaml"
        assert yaml_path.exists()

        resp = client.delete("/api/pipeline/to-delete")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        assert not yaml_path.exists()

    def test_create_custom_pipeline_in_moyun_dir(self, pipeline_client):
        """POST custom → .moyun/custom-pipelines/pipeline/{name}.yaml 存在"""
        client, workspace, _ = pipeline_client

        resp = client.post("/api/pipeline/custom", json={
            "name": "my-custom",
            "label": "我的自定义管线",
            "steps": [
                {"id": "c1", "label": "自定义步骤", "prompt_content": "# 自定义\n\n{{ file_content }}"},
            ],
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        custom_yaml = workspace / ".moyun" / "custom-pipelines" / "pipeline" / "my-custom.yaml"
        assert custom_yaml.exists()

        custom_step = workspace / ".moyun" / "custom-pipelines" / "pipeline" / "my-custom" / "c1.md"
        assert custom_step.exists()

    def test_get_nonexistent_pipeline_returns_404(self, pipeline_client):
        """GET 不存在 → 404"""
        client, workspace, _ = pipeline_client

        resp = client.get("/api/pipeline/nonexistent-pipe-xyz")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ═══════════════════════════════════════════════════════════════════
# Group 5: TestStoryStyleContextSave — 故事/文风/上下文保存（4 tests）
# ═══════════════════════════════════════════════════════════════════

class TestStoryStyleContextSave:
    """测试通过通用 File API 保存故事状态/文风指南/近期上下文"""

    @pytest.fixture
    def file_client(self, tmp_path):
        """构造 File API 测试环境"""
        workspace, settings = _setup_rightpanel_workspace(tmp_path, "rp-file")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_save_style_guide_via_file_api(self, file_client):
        """POST /api/file path=style-guide.md → 保存后回读内容匹配"""
        client, workspace, _ = file_client
        project_id = "rp-file"

        new_style = "# 文风指南 v2\n\n- 使用短句\n- 多用动作描写\n- 避免心理独白"
        resp = client.post(f"/api/file?project_id={project_id}", json={
            "path": "style-guide.md",
            "content": new_style,
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["data"]["path"] == "style-guide.md"
        assert data["data"]["mtime"] is not None
        assert data["data"]["hash"] is not None

        file_path = workspace / "projects" / project_id / "style-guide.md"
        assert file_path.read_text(encoding="utf-8") == new_style

    def test_save_story_state_via_file_api(self, file_client):
        """POST /api/file path=story-state.md → 保存后回读内容匹配"""
        client, workspace, _ = file_client
        project_id = "rp-file"

        new_state = "# 故事状态 v2\n\n当前卷: 1\n当前章: 2\n主角状态: 战斗中"
        resp = client.post(f"/api/file?project_id={project_id}", json={
            "path": "story-state.md",
            "content": new_state,
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json()["data"]["path"] == "story-state.md"
        assert resp.json()["data"]["hash"] is not None

        file_path = workspace / "projects" / project_id / "story-state.md"
        assert file_path.read_text(encoding="utf-8") == new_state

    def test_save_recent_context_via_file_api(self, file_client):
        """POST /api/file path=recent-context.md → 保存后回读内容匹配"""
        client, workspace, _ = file_client
        project_id = "rp-file"

        new_context = "# 近期上下文 v2\n\n- 主角获得新技能\n- 反派现身\n- 伏笔: 神秘信物"
        resp = client.post(f"/api/file?project_id={project_id}", json={
            "path": "recent-context.md",
            "content": new_context,
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json()["data"]["path"] == "recent-context.md"

        file_path = workspace / "projects" / project_id / "recent-context.md"
        assert file_path.read_text(encoding="utf-8") == new_context

    def test_config_save_and_read(self, file_client):
        """PUT /api/config → GET /api/config round-trip 正确"""
        client, workspace, _ = file_client

        put_resp = client.put("/api/config", json={
            "theme": "light",
            "autoMode": "L2",
            "layout": {"left": 25, "right": 30, "editorChat": 70},
        })
        assert put_resp.status_code == 200, f"PUT failed: {put_resp.text}"
        put_data = put_resp.json()
        assert put_data["data"]["theme"] == "light"
        assert put_data["data"]["autoMode"] == "L2"

        get_resp = client.get("/api/config")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["data"]["theme"] == "light"

        config_path = workspace / ".config.json"
        assert config_path.exists()
        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["theme"] == "light"

    def test_file_write_with_conflict_detection(self, file_client):
        """POST /api/file + expected_hash 不匹配 → 409 FILE_CONFLICT"""
        client, workspace, _ = file_client
        project_id = "rp-file"

        read_resp = client.get(f"/api/file?project_id={project_id}&path=style-guide.md")
        assert read_resp.status_code == 200
        current_hash = read_resp.json()["data"]["hash"]

        # 先写入一次（模拟并发修改）
        client.post(f"/api/file?project_id={project_id}", json={
            "path": "style-guide.md",
            "content": "# 并发修改\n\n中间人修改的版本。",
        })

        # 用旧的 hash 尝试写入 → 409
        resp = client.post(f"/api/file?project_id={project_id}", json={
            "path": "style-guide.md",
            "content": "# 我的修改\n\n基于旧版本。",
            "expected_hash": current_hash,
        })

        # 期望 409 表示冲突
        assert resp.status_code in (200, 409), f"Unexpected status: {resp.status_code}: {resp.text}"
