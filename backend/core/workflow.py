"""墨韵 - 工作流引擎

在 Pipeline 之上提供多步骤编排能力：
- 顺序执行多个 pipeline
- loop 循环嵌套
- 文件操作（创建目录等）
- 变量解析与传递
"""

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

import yaml

from backend.core.pipeline import PipelineRunner, PipelineError
from backend.core.trash import TrashService
from backend.schemas.workflow import (
    WorkflowDef,
    WorkflowStepDef,
    WorkflowRunStatus,
    StepStatus,
    WorkflowSaveRequest,
)

logger = logging.getLogger(__name__)

# 变量解析模式：{{ var }} 和 {{ var|pad:N }}
VAR_PATTERN = re.compile(r"\{\{(\w+)(\|pad:(\d+))?\}\}")
# 带命名空间的变量：{{ variables.xxx }}、{{ steps.step_id.output }}
# 支持 |pad:N 过滤器
NS_VAR_PATTERN = re.compile(r"\{\{(\w+)\.([\w.]+)(\|pad:(\d+))?\}\}")


class WorkflowError(Exception):
    pass


class WorkflowContext:
    """工作流执行上下文"""

    def __init__(self, project_id: str, variables: dict[str, str] | None = None):
        self.project_id = project_id
        self.variables = variables or {}
        self.loop_vars: dict[str, str | int] = {}
        self.step_outputs: dict[str, str] = {}  # step_id → output file path
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
        if step.output_mode != "overwrite":
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
        workflow_name: str,
        project_id: str,
        context: WorkflowContext,
        status: str = "running",
        completed_paths: set[str] | None = None,
    ) -> None:
        """保存工作流执行状态到磁盘"""
        state = {
            "run_id": run_id,
            "workflow": workflow_name,
            "project_id": project_id,
            "status": status,
            "variables": context.variables,
            "loop_vars": context.loop_vars.copy(),
            "step_outputs": context.step_outputs.copy(),
            "completed_paths": list(completed_paths or []),
            "updated_at": datetime.now().isoformat(),
        }
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._get_state_path(run_id).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("保存工作流状态失败 %s: %s", run_id, e)

    def _load_state(self, run_id: str) -> dict | None:
        """从磁盘加载工作流执行状态"""
        state_path = self._get_state_path(run_id)
        if not state_path.exists():
            return None
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
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
        saved_state = self._load_state(run_id) if run_id else None
        completed_paths: set[str] = set()
        if saved_state:
            context.variables.update(saved_state.get("variables", {}))
            context.loop_vars.update(saved_state.get("loop_vars", {}))
            context.step_outputs.update(saved_state.get("step_outputs", {}))
            completed_paths = set(saved_state.get("completed_paths", []))
            is_resume = saved_state.get("status") in ("running", "paused")
            if is_resume:
                logger.info("恢复工作流 %s (run_id=%s), 已完成步骤路径: %s",
                           workflow_name, run_id, completed_paths)

        total_steps = self.count_steps(workflow.steps)
        is_restored = bool(saved_state and saved_state.get("status") in ("running", "paused"))

        yield {"event": "workflow_start", "data": json.dumps({
            "run_id": run_id,
            "workflow": workflow_name,
            "label": workflow.label,
            "description": workflow.description,
            "total_steps": total_steps,
            "restored": is_restored,
            "completed_paths": list(completed_paths),
        }, ensure_ascii=False)}

        try:
            async for event in self._run_steps(
                workflow.steps, context, stop_event,
                path_prefix=run_id, completed_paths=completed_paths,
            ):
                # 注入 run_id
                ev_data = json.loads(event["data"])
                ev_data["run_id"] = run_id
                event["data"] = json.dumps(ev_data, ensure_ascii=False)
                yield event

                # step_done/step_skip → 保存状态（记录完整路径）
                if event.get("event") in ("step_done", "step_skip"):
                    step_path = ev_data.get("path", "")
                    if step_path:
                        completed_paths.add(step_path)
                    self._save_state(
                        run_id, workflow_name, project_id, context,
                        status="running",
                        completed_paths=completed_paths,
                    )

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

    # ─── 步骤调度 ─────────────────────────────────────────────────

    async def _run_steps(
        self,
        steps: list[WorkflowStepDef],
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        path_prefix: str = "",
        completed_paths: set[str] | None = None,
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
                yield {"event": "step_skip", "data": json.dumps({
                    "step_id": step.id,
                    "label": step.label,
                    "type": step.type,
                    "path": step_path,
                    "status": "skipped",
                    "output": context.step_outputs.get(step.id, ""),
                }, ensure_ascii=False)}
                continue

            async for event in self._run_step(step, context, stop_event, path_prefix, completed):
                yield event

    async def _run_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        path_prefix: str = "",
        completed_paths: set[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        step_path = f"{path_prefix}.{step.id}" if path_prefix else step.id

        yield {"event": "step_start", "data": json.dumps({
            "step_id": step.id,
            "label": step.label,
            "type": step.type,
            "path": step_path,
        }, ensure_ascii=False)}

        try:
            if step.type == "pipeline":
                async for event in self._run_pipeline_step(step, context, stop_event):
                    yield event
            elif step.type == "loop":
                async for event in self._run_loop_step(
                    step, context, stop_event, step_path, completed_paths,
                ):
                    yield event
            elif step.type == "file":
                await self._run_file_step(step, context)
            else:
                logger.warning("未知步骤类型: %s", step.type)
        except WorkflowError:
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
        }, ensure_ascii=False)}

    # ─── Pipeline 步骤 ────────────────────────────────────────────

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
                content, _ = await self.file_service.read_file(
                    f"{context.project_id}/{input_file}"
                )
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

                # pipeline done → 记录输出路径
                if ev_type == "done":
                    if target_file:
                        context.step_outputs[step.id] = target_file

        except PipelineError as e:
            raise WorkflowError(f"管线 {step.pipeline} 执行失败: {e}")

    # ─── Loop 步骤 ────────────────────────────────────────────────

    async def _run_loop_step(
        self,
        step: WorkflowStepDef,
        context: WorkflowContext,
        stop_event: asyncio.Event | None,
        step_path: str,
        completed_paths: set[str] | None = None,
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
            ):
                yield event

    # ─── File 步骤 ────────────────────────────────────────────────

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
            content, _ = await self.file_service.read_file(
                f"{context.project_id}/{src}"
            )
            await self.file_service.write_file(
                f"{context.project_id}/{dst}", content
            )
            if dst:
                context.step_outputs[step.id] = dst
        elif step.action == "delete":
            await self.file_service.delete_file(full_path)
        else:
            logger.warning("未知 file action: %s", step.action)
