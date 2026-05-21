"""墨韵 - 工作流引擎

在 Pipeline 之上提供多步骤编排能力：
- 顺序执行多个 pipeline
- loop 循环嵌套
- 文件操作（创建目录等）
- 变量解析与传递
- Human 节点暂停与恢复
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any
import uuid

import yaml

from backend.core.candidate_service import CandidateService
from backend.core.node_types import build_node_info
from backend.core.pipeline import PipelineError, PipelineRunner
from backend.core.trash import TrashService
from backend.schemas.candidate import CandidateAction
from backend.schemas.workflow import (
    WorkflowDef,
    WorkflowSaveRequest,
    WorkflowStepDef,
    WorkflowRunState,
)

logger = logging.getLogger(__name__)

# 变量解析模式：{{ var }} 和 {{ var|pad:N }}
VAR_PATTERN = re.compile(r"\{\{(\w+)(\|pad:(\d+))?\}\}")
# 带命名空间的变量：{{ variables.xxx }}、{{ steps.step_id.output }}
# 支持 |pad:N 过滤器
NS_VAR_PATTERN = re.compile(r"\{\{(\w+)\.([\w.]+)(\|pad:(\d+))?\}\}")


class WorkflowError(Exception):
    pass


class WorkflowPaused(Exception):
    """工作流暂停异常（用于中断执行流）"""
    pass


def _file_content(read_result: Any) -> str:
    """Return content from a FileService.read_file result."""
    if isinstance(read_result, tuple):
        return read_result[0]
    return str(read_result)


class WorkflowContext:
    """工作流执行上下文"""

    def __init__(self, project_id: str, variables: dict[str, str] | None = None):
        self.project_id = project_id
        self.variables = variables or {}
        self.loop_vars: dict[str, str | int] = {}
        self.step_outputs: dict[str, str] = {}  # step_id -> output file path
        self.current_path: list[str] = []

    def set_loop_var(self, name: str, value: int | str) -> None:
        self.loop_vars[name] = value

    def resolve(self, text: str | None) -> str:
        """解析模板变量"""
        if not text:
            return ""
        result = text

        # {{ project_id }}
        result = result.replace("{{project_id}}", self.project_id)

        # {{ variables.xxx }}
        for k, v in self.variables.items():
            result = result.replace("{{variables." + k + "}}", str(v))

        # {{ steps.step_id.output }}
        for step_id, output_path in self.step_outputs.items():
            placeholder = "{{steps." + step_id + ".output}}"
            if placeholder in result:
                result = result.replace(placeholder, output_path)

        # 命名空间变量 (variables.* / steps.*)
        result = NS_VAR_PATTERN.sub(self._replace_ns_var, result)

        # 普通变量 + pad 过滤器 ({{ var }} / {{ var|pad:N }})
        result = VAR_PATTERN.sub(self._replace_var, result)

        return result

    def _replace_ns_var(self, m: re.Match) -> str:
        ns = m.group(1)
        path = m.group(2)
        pad = m.group(4)
        val = ""
        if ns == "variables":
            val = self.variables.get(path, "")
        elif ns == "steps":
            parts = path.split(".")
            if len(parts) == 2 and parts[1] == "output":
                val = self.step_outputs.get(parts[0], "")
        if pad and val:
            val = str(val).zfill(int(pad))
        return str(val)

    def _replace_var(self, m: re.Match) -> str:
        name = m.group(1)
        pad = m.group(3)
        val = self.loop_vars.get(name, "")
        if pad and val:
            val = str(val).zfill(int(pad))
        return str(val)

    def resolve_int(self, text: str | None) -> int:
        """解析并转为整数"""
        resolved = self.resolve(text)
        try:
            return int(resolved)
        except (ValueError, TypeError):
            return 0


class WorkflowRunner:
    """工作流执行引擎"""

    def __init__(
        self,
        workflows_path: Path,
        prompts_path: Path,
        llm_service: Any,
        file_service: Any,
        state_dir: Path | None = None,
        system_prompts_path: Path | None = None,
    ):
        self.workflows_path = Path(workflows_path)
        self.prompts_path = Path(prompts_path)
        self.system_prompts_path = system_prompts_path
        self.llm_service = llm_service
        self.file_service = file_service
        self.state_dir = Path(state_dir) if state_dir else Path(".moyun/workflow-runs")

    # ─── 工作流加载 ───────────────────────────────────────────────

    def _get_workflow_yaml_path(self, name: str) -> Path:
        return self.workflows_path / f"{name}.yaml"

    def load_workflow(self, name: str) -> WorkflowDef:
        """加载工作流 YAML 定义"""
        yaml_path = self._get_workflow_yaml_path(name)
        if not yaml_path.exists():
            raise WorkflowError(f"工作流不存在: {name}")
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            return WorkflowDef(**data)
        except Exception as e:
            raise WorkflowError(f"加载工作流失败 {name}: {e}")

    def list_workflows(self) -> list[WorkflowDef]:
        """列出所有工作流"""
        if not self.workflows_path.exists():
            return []
        result = []
        for f in sorted(self.workflows_path.glob("*.yaml")):
            try:
                result.append(self.load_workflow(f.stem))
            except Exception as e:
                logger.warning("跳过无效工作流 %s: %s", f.name, e)
        return result

    def _step_to_yaml(self, step: WorkflowStepDef) -> dict:
        """将步骤定义转为可序列化为 YAML 的 dict"""
        d: dict = {"id": step.id, "label": step.label, "type": step.type}
        if step.pipeline:
            d["pipeline"] = step.pipeline
        if step.input:
            d["input"] = step.input
        if step.output:
            d["output"] = step.output
        if step.output_mode != "write_scene":  # only include if non-default
            d["output_mode"] = step.output_mode
        if step.action:
            d["action"] = step.action
        if step.path:
            d["path"] = step.path
        if step.count:
            d["count"] = step.count
        if step.var:
            d["var"] = step.var
        if step.extra_vars:
            d["extra_vars"] = step.extra_vars
        if step.output_key:
            d["output_key"] = step.output_key
        if step.steps:
            d["steps"] = [self._step_to_yaml(s) for s in step.steps]
        return {k: v for k, v in d.items() if v is not None}

    def save_workflow(self, req: WorkflowSaveRequest) -> WorkflowDef:
        """保存工作流定义到 YAML 文件"""
        yaml_path = self._get_workflow_yaml_path(req.name)
        data = {
            "name": req.name,
            "label": req.label,
            "description": req.description,
        }
        if req.variables:
            data["variables"] = req.variables
        data["steps"] = [self._step_to_yaml(s) for s in req.steps]

        try:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            yaml_path.write_text(
                yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            return WorkflowDef(name=req.name, label=req.label, description=req.description,
                             variables=req.variables, steps=req.steps)
        except Exception as e:
            raise WorkflowError(f"保存工作流失败 {req.name}: {e}")

    def delete_workflow(self, name: str) -> dict:
        """删除工作流 YAML 文件（移到回收站）

        Returns:
            回收站记录
        """
        yaml_path = self._get_workflow_yaml_path(name)
        if not yaml_path.exists():
            raise WorkflowError(f"工作流不存在: {name}")
        try:
            trash = TrashService(self.workflows_path.parent)
            return trash.move_to_trash(yaml_path)
        except Exception as e:
            raise WorkflowError(f"删除工作流失败 {name}: {e}")

    def count_steps(self, steps: list[WorkflowStepDef]) -> int:
        """递归统计步骤总数（含 loop 内子步骤按 1 步计）"""
        total = 0
        for step in steps:
            if step.type == "loop" and step.steps:
                # loop 整体算 1 步，展开后是 N*子步骤
                total += 1
            else:
                total += 1
        return total

    # ─── 状态持久化 ────────────────────────────────────────────────

    def _get_state_path(self, run_id: str) -> Path:
        return self.state_dir / f"{run_id}.json"

    def _save_state(
        self,
        run_id: str,
        workflow: str | None = None,
        project_id: str | None = None,
        context: WorkflowContext | None = None,
        status: str = "running",
        completed_paths: list[str] | None = None,
        current_node: str | None = None,
        current_step_path: str | None = None,
        waiting_reason: str | None = None,
        available_actions: list[str] | None = None,
        waiting_input: str | None = None,
        remaining_steps: list[dict] | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        """保存工作流执行状态到磁盘"""
        workflow = workflow or legacy_kwargs.pop("workflow_name", None)
        if workflow is None or project_id is None or context is None:
            raise WorkflowError("Missing workflow state fields")

        state = WorkflowRunState(
            run_id=run_id,
            workflow=workflow,
            project_id=project_id,
            status=status,
            current_node=current_node,
            current_step_path=current_step_path,
            waiting_reason=waiting_reason,
            available_actions=available_actions or [],
            waiting_input=waiting_input,
            variables=context.variables,
            loop_vars=context.loop_vars,
            step_outputs=context.step_outputs,
            completed_paths=completed_paths or [],
            remaining_steps=remaining_steps or [],
            updated_at=datetime.now().isoformat(),
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._get_state_path(run_id).write_text(
                state.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("保存工作流状态失败 %s: %s", run_id, e)

    def _load_state(self, run_id: str) -> WorkflowRunState | None:
        """从磁盘加载工作流执行状态"""
        state_path = self._get_state_path(run_id)
        if not state_path.exists():
            return None
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            return WorkflowRunState(**data)
        except Exception as e:
            logger.warning("加载工作流状态失败 %s: %s", run_id, e)
            return None

    def _delete_state(self, run_id: str) -> None:
        """执行完毕后清理状态文件"""
        state_path = self._get_state_path(run_id)
        if state_path.exists():
            try:
                state_path.unlink()
            except Exception as e:
                logger.warning("删除工作流状态文件失败 %s: %s", run_id, e)

    # ─── 主入口 ───────────────────────────────────────────────────

    async def run(
        self,
        workflow_name: str,
        project_id: str,
        variables: dict[str, str] | None = None,
        stop_event: asyncio.Event | None = None,
        run_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """执行工作流，以 SSE 事件形式输出"""
        workflow = self.load_workflow(workflow_name)
        context = WorkflowContext(project_id, variables or {})
        run_id = run_id or f"wf-{uuid.uuid4().hex[:8]}"

        # 尝试恢复已保存状态
        saved_state = self._load_state(run_id)
        completed_paths: set[str] = set()
        is_resume = False

        if saved_state:
            context.variables.update(saved_state.variables)
            context.loop_vars.update(saved_state.loop_vars)
            context.step_outputs.update(saved_state.step_outputs)
            completed_paths = set(saved_state.completed_paths)
            is_resume = True

            if saved_state.status == "waiting_for_user":
                # 之前处于等待状态，发送等待状态事件
                yield {"event": "workflow_paused", "data": json.dumps({
                    "run_id": run_id,
                    "status": "waiting_for_user",
                    "current_node": saved_state.current_node,
                    "step_id": saved_state.current_node,
                    "path": saved_state.current_step_path,
                    "waiting_reason": saved_state.waiting_reason,
                    "available_actions": saved_state.available_actions,
                    "actions": saved_state.available_actions,
                    "waiting_input": saved_state.waiting_input,
                    "input": saved_state.waiting_input,
                    "variables": context.variables,
                }, ensure_ascii=False)}
                return

        total_steps = self.count_steps(workflow.steps)

        # 构建步骤树预览（带节点元信息）
        steps_preview = []
        for s in workflow.steps:
            node_info = build_node_info(s.type, s.action, s.label)
            steps_preview.append({
                "id": s.id,
                "label": s.label,
                "type": s.type,
                "node_type": node_info["node_type"],
                "node_label": node_info["node_label"],
                "executor": node_info["executor"],
                "executor_label": node_info["executor_label"],
            })

        yield {"event": "workflow_start", "data": json.dumps({
            "run_id": run_id,
            "workflow": workflow_name,
            "label": workflow.label,
            "description": workflow.description,
            "total_steps": total_steps,
            "restored": is_resume,
            "completed_paths": list(completed_paths),
            "steps_preview": steps_preview,  # 步骤树预览（带节点元信息）
            "variables": context.variables,   # 当前变量池
        }, ensure_ascii=False)}

        try:
            async for event in self._run_steps(
                workflow.steps, context, stop_event,
                path_prefix=run_id, completed_paths=completed_paths,
                workflow=workflow, run_id=run_id,
            ):
                yield event

        except WorkflowPaused:
            # 工作流被正常暂停
            return
        except WorkflowError as e:
            logger.error("工作流执行失败: %s", e)
            yield {"event": "workflow_error", "data": json.dumps({
                "run_id": run_id,
                "message": str(e),
            }, ensure_ascii=False)}
            return

        yield {"event": "workflow_done", "data": json.dumps({
            "run_id": run_id,
            "message": "工作流执行完成",
        }, ensure_ascii=False)}

        # 执行完毕，清理状态文件
        self._delete_state(run_id)

    async def resume(
        self,
        run_id: str,
        action: str,
        output: str = "",
        extra_vars: dict[str, str] | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict, None]:
        """从暂停状态恢复工作流"""
        saved_state = self._load_state(run_id)
        if not saved_state:
            raise WorkflowError(f"找不到工作流运行状态: {run_id}")

        if saved_state.status != "waiting_for_user":
            raise WorkflowError(f"工作流当前状态不是等待用户: {saved_state.status}")

        workflow = self.load_workflow(saved_state.workflow)
        context = WorkflowContext(saved_state.project_id, saved_state.variables)
        context.loop_vars = saved_state.loop_vars
        context.step_outputs = saved_state.step_outputs
        completed_paths = set(saved_state.completed_paths)

        # 处理用户动作
        if action == "stop":
            yield {"event": "workflow_stopped", "data": json.dumps({
                "message": "用户停止工作流",
            }, ensure_ascii=False)}
            self._delete_state(run_id)
            return

        # 找到当前等待的节点
        current_step = self._find_step_by_id(workflow.steps, saved_state.current_node)
        if not current_step:
            raise WorkflowError(f"找不到节点: {saved_state.current_node}")

        node_info = build_node_info(current_step.type, current_step.action, current_step.label)

        # 处理用户输出
        final_output = output or saved_state.waiting_input or ""

        # 将输出写入变量池
        output_key = current_step.output_key or f"approved_{current_step.id}"
        context.variables[output_key] = final_output
        context.step_outputs[current_step.id] = final_output

        # 合并额外变量
        if extra_vars:
            context.variables.update(extra_vars)

        # 标记当前步骤为已完成
        if saved_state.current_step_path:
            completed_paths.add(saved_state.current_step_path)

        # 发送节点完成事件
        if completed_paths is not None:
            completed_paths.add(step_path)

        yield {"event": "step_done", "data": json.dumps({
            "step_id": current_step.id,
            "label": current_step.label,
            "type": current_step.type,
            "path": saved_state.current_step_path,
            "status": "done",
            "output": final_output,
            "node_type": node_info["node_type"],
            "node_label": node_info["node_label"],
            "executor": node_info["executor"],
            "executor_label": node_info["executor_label"],
        }, ensure_ascii=False)}

        # 更新变量池
        yield {"event": "variable_update", "data": json.dumps({
            "key": output_key,
            "value": final_output,
            "source": "approved",
        }, ensure_ascii=False)}

        # 保存当前状态为 running
        self._save_state(
            run_id, saved_state.workflow, saved_state.project_id, context,
            status="running", completed_paths=list(completed_paths),
        )

        # 继续执行剩余步骤
        try:
            # 从当前位置之后继续执行
            remaining_steps = self._get_remaining_steps(workflow.steps, current_step.id)

            async for event in self._run_steps(
                workflow.steps, context, stop_event,
                path_prefix=run_id, completed_paths=completed_paths,
                workflow=workflow, run_id=run_id,
            ):
                yield event

        except WorkflowPaused:
            return

        yield {"event": "workflow_done", "data": json.dumps({
            "run_id": run_id,
            "message": "工作流执行完成",
        }, ensure_ascii=False)}

        self._delete_state(run_id)

    # ─── 辅助方法 ─────────────────────────────────────────────────

    def _find_step_by_id(self, steps: list[WorkflowStepDef], step_id: str) -> WorkflowStepDef | None:
        """在步骤树中查找指定 ID 的步骤"""
        for step in steps:
            if step.id == step_id:
                return step
            if step.steps:
                found = self._find_step_by_id(step.steps, step_id)
                if found:
                    return found
        return None

    def _get_remaining_steps(self, steps: list[WorkflowStepDef], after_step_id: str) -> list[WorkflowStepDef]:
        """获取指定步骤之后的剩余步骤"""
        found = False
        remaining = []
        for step in steps:
            if found:
                remaining.append(step)
            elif step.id == after_step_id:
                found = True
        return remaining

    # ─── 步骤调度 ─────────────────────────────────────────────────

    async def _run_steps(
        self,
        steps: list[WorkflowStepDef],
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        path_prefix: str = "",
        completed_paths: set[str] | None = None,
        workflow: WorkflowDef | None = None,
        run_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        completed = completed_paths or set()
        for step in steps:
            if stop_event and stop_event.is_set():
                yield {"event": "workflow_stopped", "data": json.dumps({
                    "message": "用户已停止",
                })}
                return

            step_path = f"{path_prefix}.{step.id}" if path_prefix else step.id

            # 断点续跑：按完整路径跳过已完成的步骤
            if step_path in completed:
                node_info = build_node_info(step.type, step.action, step.label)
                yield {"event": "step_skip", "data": json.dumps({
                    "step_id": step.id,
                    "label": step.label,
                    "type": step.type,
                    "path": step_path,
                    "status": "skipped",
                    "output": context.step_outputs.get(step.id, ""),
                    # 节点元信息
                    "node_type": node_info["node_type"],
                    "node_label": node_info["node_label"],
                    "executor": node_info["executor"],
                    "executor_label": node_info["executor_label"],
                }, ensure_ascii=False)}
                continue

            async for event in self._run_step(
                step, context, stop_event, path_prefix, completed, workflow, run_id,
            ):
                yield event

    async def _run_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        path_prefix: str = "",
        completed_paths: set[str] | None = None,
        workflow: WorkflowDef | None = None,
        run_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        step_path = f"{path_prefix}.{step.id}" if path_prefix else step.id

        # 构建节点元信息
        node_info = build_node_info(step.type, step.action, step.label)

        yield {"event": "step_start", "data": json.dumps({
            "step_id": step.id,
            "label": step.label,
            "type": step.type,
            "path": step_path,
            # 节点元信息
            "node_type": node_info["node_type"],
            "node_label": node_info["node_label"],
            "executor": node_info["executor"],
            "executor_label": node_info["executor_label"],
            "status": "running",
            # Human 节点需要等待用户
            "waiting_for_user": node_info["executor"] == "human",
            "waiting_reason": node_info.get("waiting_reason", ""),
            "actions": node_info.get("actions", []),
        }, ensure_ascii=False)}

        try:
            if step.type.startswith("human_"):
                # Human 节点：暂停等待用户
                async for event in self._run_human_step(
                    step, context, step_path, workflow, run_id, node_info,
                ):
                    yield event
                # 抛出异常中断执行流
                raise WorkflowPaused()
            elif step.type == "pipeline":
                async for event in self._run_pipeline_step(step, context, stop_event):
                    yield event
            elif step.type == "loop":
                async for event in self._run_loop_step(
                    step, context, stop_event, step_path, completed_paths,
                    workflow, run_id,
                ):
                    yield event
            elif step.type == "file":
                await self._run_file_step(step, context)
            elif step.type in ("memory_update", "memory_review"):
                async for event in self._run_memory_step(
                    step, context, stop_event, step_path, workflow, run_id, node_info,
                ):
                    yield event
            else:
                logger.warning("未知步骤类型: %s", step.type)
        except WorkflowPaused:
            raise
        except Exception as e:
            raise WorkflowError(f"步骤 {step.label} 执行失败: {e}")

        yield {"event": "step_done", "data": json.dumps({
            "step_id": step.id,
            "label": step.label,
            "type": step.type,
            "path": step_path,
            "status": "done",
            "output": context.step_outputs.get(step.id, ""),
            # 节点元信息
            "node_type": node_info["node_type"],
            "node_label": node_info["node_label"],
            "executor": node_info["executor"],
            "executor_label": node_info["executor_label"],
        }, ensure_ascii=False)}

        # 保存状态
        if workflow and run_id:
            self._save_state(
                run_id, workflow.name, context.project_id, context,
                status="running", completed_paths=list(completed_paths or []),
            )

    # ─── Human 节点 ───────────────────────────────────────────────

    async def _run_human_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        step_path: str,
        workflow: WorkflowDef | None,
        run_id: str,
        node_info: dict,
    ) -> AsyncGenerator[dict, None]:
        """执行 Human 节点：暂停并保存状态"""
        # 解析输入内容
        waiting_input = ""
        if step.input:
            resolved_input = context.resolve(step.input)
            try:
                # 尝试读取文件
                file_path = f"{context.project_id}/{resolved_input}"
                waiting_input = _file_content(
                    await self.file_service.read_file(file_path)
                )
            except Exception:
                # 如果不是文件路径，直接使用值
                waiting_input = resolved_input

        # 保存暂停状态
        if workflow and run_id:
            remaining_steps = self._get_remaining_steps(workflow.steps, step.id)
            remaining_steps_serialized = [self._step_to_yaml(s) for s in remaining_steps]

            self._save_state(
                run_id, workflow.name, context.project_id, context,
                status="waiting_for_user",
                current_node=step.id,
                current_step_path=step_path,
                waiting_reason=node_info.get("waiting_reason", ""),
                available_actions=node_info.get("actions", []),
                waiting_input=waiting_input,
                remaining_steps=remaining_steps_serialized,
            )

        # 发送等待事件
        yield {"event": "step_waiting", "data": json.dumps({
            "step_id": step.id,
            "label": step.label,
            "type": step.type,
            "path": step_path,
            "node_type": node_info["node_type"],
            "node_label": node_info["node_label"],
            "executor": node_info["executor"],
            "executor_label": node_info["executor_label"],
            "waiting_reason": node_info.get("waiting_reason", ""),
            "actions": node_info.get("actions", []),
            "input": waiting_input,
            "output_key": step.output_key or f"approved_{step.id}",
        }, ensure_ascii=False)}

        yield {"event": "workflow_paused", "data": json.dumps({
            "run_id": run_id,
            "status": "waiting_for_user",
            "current_node": step.id,
            "step_id": step.id,
            "label": step.label,
            "type": step.type,
            "path": step_path,
            "node_type": node_info["node_type"],
            "node_label": node_info["node_label"],
            "executor": node_info["executor"],
            "executor_label": node_info["executor_label"],
            "waiting_reason": node_info.get("waiting_reason", ""),
            "available_actions": node_info.get("actions", []),
            "actions": node_info.get("actions", []),
            "waiting_input": waiting_input,
            "input": waiting_input,
            "output_key": step.output_key or f"approved_{step.id}",
            "variables": context.variables,
        }, ensure_ascii=False)}

    # ─── Pipeline 节点 ────────────────────────────────────────────

    async def _run_pipeline_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
    ) -> AsyncGenerator[dict, None]:
        # 解析 input/output 路径
        target_file = context.resolve(step.output)
        input_file = context.resolve(step.input)

        # 如果有 input 但不等于 output，读取 input 文件作为 file_content
        extra_vars = {}
        if input_file and input_file != target_file:
            try:
                content = _file_content(await self.file_service.read_file(
                    f"{context.project_id}/{input_file}"
                ))
                extra_vars["file_content"] = content
            except Exception:
                logger.warning("读取 input 文件失败: %s", input_file)

        # 合并 step 级 extra_vars
        for k, v in step.extra_vars.items():
            extra_vars[k] = context.resolve(v)

        # 注入循环变量（vol、ch 等），让 pipeline 模板可知当前章节编号
        for k, v in context.loop_vars.items():
            if k not in extra_vars:
                extra_vars[k] = str(v)

        runner = PipelineRunner(
            self.prompts_path,
            self.llm_service,
            self.file_service,
            system_prompts_path=self.system_prompts_path,
        )

        try:
            async for event in runner.run(
                pipeline_name=step.pipeline,
                project_id=context.project_id,
                target_file=target_file,
                user_input="",
                output_mode=step.output_mode,
                extra_vars=extra_vars,
                stop_event=stop_event,
            ):
                # 转发 pipeline 事件
                ev_type = event.get("event", "")
                ev_data = json.loads(event.get("data", "{}"))
                ev_data["step_id"] = step.id
                event["data"] = json.dumps(ev_data, ensure_ascii=False)
                yield event

                # pipeline done -> 记录输出路径
                if ev_type == "done":
                    if target_file:
                        context.step_outputs[step.id] = target_file

        except PipelineError as e:
            raise WorkflowError(f"管线 {step.pipeline} 执行失败: {e}")

    # ─── Loop 节点 ────────────────────────────────────────────────

    async def _run_loop_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        step_path: str,
        completed_paths: set[str] | None = None,
        workflow: WorkflowDef | None = None,
        run_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        count = context.resolve_int(step.count)
        if count <= 0:
            logger.warning("loop count 无效: %s", step.count)
            return

        var_name = step.var or "index"

        for i in range(1, count + 1):
            if stop_event and stop_event.is_set():
                yield {"event": "workflow_stopped", "data": json.dumps({
                    "message": "用户已停止",
                })}
                return

            context.set_loop_var(var_name, i)

            # 每次迭代使用不同 prefix，确保子步骤路径唯一（如 wf-xxx.loop.1.calc）
            iter_prefix = f"{step_path}.{i}"

            yield {"event": "loop_iteration", "data": json.dumps({
                "step_id": step.id,
                "label": step.label,
                "path": iter_prefix,
                "var": var_name,
                "value": i,
                "current": i,
                "total": count,
            }, ensure_ascii=False)}

            async for event in self._run_steps(
                step.steps, context, stop_event,
                path_prefix=iter_prefix, completed_paths=completed_paths,
                workflow=workflow, run_id=run_id,
            ):
                yield event

    # ─── File 节点 ────────────────────────────────────────────────

    async def _run_file_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
    ) -> None:
        resolved_path = context.resolve(step.path)
        full_path = f"{context.project_id}/{resolved_path}"

        if step.action == "mkdir":
            await self.file_service.create_directory(full_path)
            logger.info("创建目录: %s", full_path)
            if resolved_path:
                context.step_outputs[step.id] = resolved_path
        elif step.action == "copy":
            src = context.resolve(step.input)
            dst = context.resolve(step.output)
            content = _file_content(await self.file_service.read_file(
                f"{context.project_id}/{src}"
            ))
            await self.file_service.write_file(
                f"{context.project_id}/{dst}", content
            )
            if dst:
                context.step_outputs[step.id] = dst
        elif step.action == "delete":
            await self.file_service.delete_file(full_path)
        elif step.action == "create_candidate":
            await self._run_file_create_candidate(step, context)
        elif step.action == "adopt_candidate":
            await self._run_file_adopt_candidate(step, context)
        else:
            logger.warning("未知 file action: %s", step.action)

    async def _run_file_create_candidate(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
    ) -> None:
        resolved_path = context.resolve(step.path)
        input_file = context.resolve(step.input)

        if not resolved_path:
            logger.warning("create_candidate 需要指定 path")
            return

        content = ""
        if input_file:
            content = _file_content(await self.file_service.read_file(
                f"{context.project_id}/{input_file}"
            ))

        candidate_action = CandidateAction(step.extra_vars.get("action", "rewrite"))
        workflow_run_id = context.variables.get("run_id")

        candidate_service = CandidateService(self.file_service)
        candidate = await candidate_service.create_candidate(
            project_id=context.project_id,
            source_path=resolved_path,
            action=candidate_action,
            content=content,
            workflow_run_id=workflow_run_id,
        )

        logger.info("创建候选稿: %s -> %s", resolved_path, candidate.id)
        context.step_outputs[step.id] = candidate.id

    async def _run_file_adopt_candidate(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
    ) -> None:
        candidate_id = context.resolve(step.input)

        if not candidate_id:
            logger.warning("adopt_candidate 需要指定 input (candidate_id)")
            return

        candidate_service = CandidateService(self.file_service)
        result = await candidate_service.adopt_candidate(
            project_id=context.project_id,
            candidate_id=candidate_id,
        )

        if result == "success":
            logger.info("采用候选稿: %s", candidate_id)
            context.step_outputs[step.id] = candidate_id
        elif result == "conflict":
            logger.warning("采用候选稿冲突（源文件已变化）: %s", candidate_id)
        else:
            logger.warning("采用候选稿失败: %s (result=%s)", candidate_id, result)

    # ─── Memory 节点 ───────────────────────────────────────────────

    async def _run_memory_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        step_path: str,
        workflow: WorkflowDef | None,
        run_id: str,
        node_info: dict,
    ) -> AsyncGenerator[dict, None]:
        """执行 Memory 节点：生成/审核记忆更新"""
        # 解析输入
        changed_content = ""
        if step.input:
            resolved_input = context.resolve(step.input)
            try:
                # 尝试读取文件
                file_path = f"{context.project_id}/{resolved_input}"
                changed_content = _file_content(
                    await self.file_service.read_file(file_path)
                )
            except Exception:
                # 如果不是文件路径，直接使用值
                changed_content = resolved_input

        # 读取当前记忆状态
        story_state_content = ""
        recent_context_content = ""

        try:
            story_content = _file_content(await self.file_service.read_file(
                f"{context.project_id}/story-state.md"
            ))
            story_state_content = story_content
        except Exception:
            logger.warning("读取 story-state.md 失败")

        try:
            recent_content = _file_content(await self.file_service.read_file(
                f"{context.project_id}/recent-context.md"
            ))
            recent_context_content = recent_content
        except Exception:
            logger.warning("读取 recent-context.md 失败")

        # 评估风险等级
        risk_level = "low"
        risk_reason = "常规内容更新"
        if hasattr(self, 'assess_memory_risk'):
            risk_level, risk_reason = self.assess_memory_risk(
                changed_content, story_state_content
            )
        else:
            # 简单的关键词检测
            high_risk_keywords = ["死亡", "消失", "揭示", "回收伏笔", "重大转折"]
            for keyword in high_risk_keywords:
                if keyword in changed_content:
                    risk_level = "high"
                    risk_reason = f"包含高风险内容：{keyword}"
                    break

        yield {"event": "memory_risk_assessment", "data": json.dumps({
            "step_id": step.id,
            "label": step.label,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "changed_content_length": len(changed_content),
        }, ensure_ascii=False)}

        # 如果是高风险或 memory_review 类型，需要人工确认
        if risk_level == "high" or step.type == "memory_review":
            # 保存暂停状态，等待人工确认
            if workflow and run_id:
                remaining_steps = self._get_remaining_steps(workflow.steps, step.id)
                remaining_steps_serialized = [self._step_to_yaml(s) for s in remaining_steps]

                self._save_state(
                    run_id, workflow.name, context.project_id, context,
                    status="waiting_for_user",
                    current_node=step.id,
                    current_step_path=step_path,
                    waiting_reason=f"记忆更新风险等级：{risk_level}，需要人工确认",
                    available_actions=["approve", "edit_and_approve", "stop"],
                    waiting_input=changed_content,
                    remaining_steps=remaining_steps_serialized,
                )

            # 发送等待事件
            yield {"event": "step_waiting", "data": json.dumps({
                "step_id": step.id,
                "label": step.label,
                "type": step.type,
                "path": step_path,
                "node_type": node_info["node_type"],
                "node_label": node_info["node_label"],
                "executor": node_info["executor"],
                "executor_label": node_info["executor_label"],
                "waiting_reason": f"记忆更新风险等级：{risk_level}，需要人工确认",
                "actions": ["approve", "edit_and_approve", "stop"],
                "input": changed_content,
                "output_key": step.output_key or "draft_memory_update",
                "risk_level": risk_level,
                "risk_reason": risk_reason,
            }, ensure_ascii=False)}

            yield {"event": "workflow_paused", "data": json.dumps({
                "run_id": run_id,
                "status": "waiting_for_user",
                "current_node": step.id,
                "waiting_reason": f"记忆更新风险等级：{risk_level}，需要人工确认",
                "available_actions": ["approve", "edit_and_approve", "stop"],
                "waiting_input": changed_content,
                "variables": context.variables,
                "risk_level": risk_level,
            }, ensure_ascii=False)}

            # 抛出异常中断执行流
            raise WorkflowPaused()

        # 低风险：自动执行记忆更新
        # 1. 生成草稿
        draft_update = await self._generate_memory_draft(
            changed_content, story_state_content, recent_context_content,
        )

        # 2. 更新记忆文件
        if step.output_key or "story-state" in step.label.lower():
            updated_story_state = await self._apply_memory_update(
                draft_update, story_state_content,
            )
            await self.file_service.write_file(
                f"{context.project_id}/story-state.md",
                updated_story_state,
            )
            logger.info("更新 story-state.md 成功")

        if step.output_key or "recent-context" in step.label.lower():
            updated_recent_context = await self._update_recent_context(
                changed_content, recent_context_content, step.input or "未知场景",
            )
            await self.file_service.write_file(
                f"{context.project_id}/recent-context.md",
                updated_recent_context,
            )
            logger.info("更新 recent-context.md 成功")

        # 记录输出
        context.step_outputs[step.id] = draft_update

        yield {"event": "memory_update_done", "data": json.dumps({
            "step_id": step.id,
            "label": step.label,
            "draft_update": draft_update,
            "risk_level": risk_level,
            "updated_files": ["story-state.md", "recent-context.md"],
        }, ensure_ascii=False)}

        # 更新变量池
        output_key = step.output_key or "draft_memory_update"
        context.variables[output_key] = draft_update
        yield {"event": "variable_update", "data": json.dumps({
            "key": output_key,
            "value": draft_update,
            "source": "ai",
        }, ensure_ascii=False)}

    async def _generate_memory_draft(
        self,
        changed_content: str,
        story_state: str,
        recent_context: str,
    ) -> str:
        """使用 LLM 生成记忆更新草稿"""
        # 准备 prompt
        from jinja2 import Template

        prompt_template_path = Path(self.prompts_path) / "pipeline" / "memory" / "draft_update.md"
        if not prompt_template_path.exists():
            # 如果模板不存在，生成简单摘要
            return await self._simple_memory_summary(changed_content)

        try:
            template = Template(prompt_template_path.read_text(encoding="utf-8"))
            prompt = template.render(
                changed_content=changed_content,
                story_state=story_state or "暂无",
                recent_context=recent_context or "暂无",
            )
        except Exception as e:
            logger.warning("加载记忆更新模板失败: %s", e)
            return await self._simple_memory_summary(changed_content)

        # 调用 LLM
        try:
            response = await self.llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                model="auto",
            )
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error("LLM 生成记忆草稿失败: %s", e)
            return await self._simple_memory_summary(changed_content)

    async def _simple_memory_summary(self, content: str) -> str:
        """简单的记忆摘要生成（当 LLM 不可用时）"""
        # 简单的文本截取和摘要
        lines = content.split('\n')
        summary_lines = []
        for line in lines[:20]:  # 取前20行
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())

        summary = '\n'.join(summary_lines[:5])  # 取前5行作为摘要

        return f"""# 故事状态更新草案

## 摘要
{summary}

## 风险评估
- 风险等级：low
- 风险说明：常规内容更新

## 更新内容
{content[:500]}...
"""

    async def _apply_memory_update(
        self,
        draft_update: str,
        current_state: str,
    ) -> str:
        """应用记忆更新到现有状态"""
        # 简单实现：追加更新内容到现有状态
        # 实际应该使用 LLM 智能合并

        if not current_state:
            return draft_update

        # 提取草案中的关键更新
        # 实际实现应该解析草案结构
        return current_state + "\n\n## 更新于 " + \
            datetime.now().strftime("%Y-%m-%d %H:%M:%S") + \
            "\n\n" + draft_update

    async def _update_recent_context(
        self,
        scene_content: str,
        current_context: str,
        scene_path: str,
    ) -> str:
        """更新近期上下文"""
        # 生成场景摘要
        summary = await self._generate_scene_summary(scene_content)

        # 构建新的上下文条目
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"""## {timestamp} - {scene_path}
【场景摘要】
{summary}

【人物状态变化】
暂无

【新增线索/伏笔】
暂无

【下一场承接点】
待续
"""

        # 在顶部添加新条目
        if not current_context:
            return f"""# 近期上下文摘要

> 本文件存储最近5章的摘要，用于在生成章节时提供近期情节上下文。
> **由系统在每次生成章节后自动生成/更新。**

---

## 章节范围

- **起始章节**：第1章
- **结束章节**：第1章
- **总章节数**：1章

---

## 摘要列表

{new_entry}
"""
        else:
            # 在 ## 摘要列表 后添加新条目
            if "## 摘要列表" in current_context:
                parts = current_context.split("## 摘要列表")
                return parts[0] + "## 摘要列表\n\n" + new_entry + "\n".join(parts[1:])
            else:
                return new_entry + "\n\n" + current_context

    async def _generate_scene_summary(self, content: str) -> str:
        """生成场景摘要"""
        # 简单的摘要生成
        # 实际应该使用 LLM

        lines = [line.strip() for line in content.split('\n') if line.strip()]

        # 提取前3个段落作为摘要
        summary_lines = []
        para_count = 0
        for line in lines:
            if len(line) > 10 and not line.startswith('#'):
                summary_lines.append(line)
                para_count += 1
                if para_count >= 3:
                    break

        return ' '.join(summary_lines[:2]) if summary_lines else "场景内容待补充"
