"""墨韵 - 管线引擎

职责：
- 加载管线 YAML 定义
- 按步骤顺序执行 LLM 调用
- 失败时自动 fallback
- 以 AsyncGenerator 形式输出 SSE 事件

管线 YAML 路径：workspace/prompts/pipeline/{name}.yaml
每步 Prompt 路径：workspace/prompts/pipeline/{name}/{step_id}.md
"""

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

import yaml
from jinja2 import Environment, FileSystemLoader

from backend.core.llm import LLMService
from backend.core.file_ops import FileService
from backend.schemas.pipeline import PipelineDef, PipelineStepDef

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


class PipelineRunner:
    """管线执行引擎"""

    def __init__(
        self,
        prompts_path: Path,
        llm_service: LLMService,
        file_service: FileService,
    ):
        self.prompts_path = Path(prompts_path)
        self.llm_service = llm_service
        self.file_service = file_service
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_path)),
            autoescape=False,
        )

    def _get_pipeline_dir(self) -> Path:
        return self.prompts_path / "pipeline"

    def _get_pipeline_yaml_path(self, name: str) -> Path:
        return self._get_pipeline_dir() / f"{name}.yaml"

    def _get_step_prompt_path(self, pipeline_name: str, step_id: str) -> Path:
        return self._get_pipeline_dir() / pipeline_name / f"{step_id}.md"

    def _render_prompt(self, relative_path: str, variables: dict) -> str:
        """使用 Jinja2 渲染 prompt 模板"""
        template = self.env.get_template(relative_path)
        return template.render(**variables)

    def load_pipeline(self, name: str) -> PipelineDef:
        """加载管线 YAML 定义"""
        yaml_path = self._get_pipeline_yaml_path(name)
        if not yaml_path.exists():
            raise PipelineError(f"管线不存在: {name}")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            return PipelineDef(**data)
        except Exception as e:
            raise PipelineError(f"加载管线定义失败 {name}: {e}")

    def list_pipelines(self) -> list[PipelineDef]:
        """列出所有可用管线（系统预置）"""
        pipeline_dir = self._get_pipeline_dir()
        if not pipeline_dir.exists():
            return []
        pipelines = []
        for f in sorted(pipeline_dir.glob("*.yaml")):
            try:
                pipelines.append(self.load_pipeline(f.stem))
            except Exception as e:
                logger.warning("跳过无效管线定义 %s: %s", f.name, e)
        return pipelines

    async def run(
        self,
        pipeline_name: str,
        project_id: str,
        target_file: str | None = None,
        user_input: str | None = None,
        output_mode: str = "overwrite",
        extra_vars: dict | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict, None]:
        """执行管线

        Yields:
            SSE 事件字典:
            - {"event": "task_start", "data": json}
            - {"event": "thinking", "data": json}
            - {"event": "step_done", "data": json}
            - {"event": "prompt", "data": json}
            - {"event": "generation", "data": json}
            - {"event": "done", "data": json}
            - {"event": "error", "data": json}
        """
        pipeline = self.load_pipeline(pipeline_name)
        extra_vars = extra_vars or {}

        task_id = f"pipeline-{pipeline_name}-{uuid.uuid4().hex[:8]}"
        step_outputs: dict[str, str] = {}

        total_steps = len(pipeline.steps)
        yield {"event": "task_start", "data": json.dumps({
            "task_id": task_id,
            "pipeline": pipeline_name,
            "total_steps": total_steps,
        })}

        for i, step in enumerate(pipeline.steps):
            if stop_event and stop_event.is_set():
                yield {"event": "done", "data": json.dumps({"task_id": task_id, "message": "已取消"})}
                return

            is_final = (i == total_steps - 1)

            # 发送 thinking 事件
            yield {"event": "thinking", "data": json.dumps({
                "step_id": step.id,
                "label": step.label,
                "step": i + 1,
                "total": total_steps,
            })}

            try:
                # 读取文件内容
                file_content = ""
                if target_file:
                    try:
                        content, _ = await self.file_service.read_file(f"{project_id}/{target_file}")
                        file_content = content
                    except Exception as e:
                        logger.warning("无法读取目标文件 %s/%s: %s", project_id, target_file, e)

                # 准备模板变量
                step_vars = {
                    "file_content": file_content,
                    "file_path": target_file or "",
                    "project_id": project_id,
                    "user_input": user_input or "",
                    "previous_output": step_outputs.get(step.fallback) if step.fallback else None,
                    "style_guide": "",
                    "story_state": "",
                    **extra_vars,
                }

                # 渲染 prompt 模板（使用 step.prompt 保证与 YAML 定义一致）
                prompt_relative = f"{step.prompt}.md"
                prompt_text = self._render_prompt(prompt_relative, step_vars)

                # 发送渲染后的 prompt
                yield {"event": "prompt", "data": json.dumps({
                    "prompt": prompt_text,
                    "task_id": task_id,
                    "step_id": step.id,
                })}

                # 调用 LLM
                messages = [{"role": "user", "content": prompt_text}]
                step_output = ""

                async for chunk in self.llm_service.complete(
                    messages,
                    stop_event=stop_event,
                    timeout=180,
                ):
                    step_output += chunk
                    # 只有最终步骤才流式输出到前端
                    if is_final:
                        yield {"event": "generation", "data": json.dumps({
                            "delta": chunk,
                            "task_id": task_id,
                        })}

                step_outputs[step.id] = step_output

                yield {"event": "step_done", "data": json.dumps({
                    "step_id": step.id,
                    "label": step.label,
                    "status": "done",
                })}

            except Exception as e:
                logger.error("管线步骤失败: %s/%s - %s", pipeline_name, step.id, e)
                if step.fallback and step.fallback in step_outputs:
                    logger.info("回退到步骤 %s 的输出", step.fallback)
                    step_outputs[step.id] = step_outputs[step.fallback]
                    yield {"event": "step_done", "data": json.dumps({
                        "step_id": step.id,
                        "label": step.label,
                        "status": "fallback",
                    })}
                elif is_final:
                    yield {"event": "error", "data": json.dumps({
                        "message": f"步骤 {step.label} 失败: {e}",
                        "task_id": task_id,
                    })}
                    # 用上一步的输出兜底
                    if i > 0:
                        step_outputs[step.id] = step_outputs.get(pipeline.steps[i-1].id, "")
                    else:
                        return
                else:
                    # 中间步骤失败且无 fallback，终止管线
                    yield {"event": "error", "data": json.dumps({
                        "message": f"步骤 {step.label} 失败: {e}",
                        "task_id": task_id,
                    })}
                    return

        # 保存最终输出到文件
        final_output = step_outputs.get(pipeline.steps[-1].id, "")
        if final_output and target_file:
            original_content = ""
            frontmatter = None
            try:
                orig, fm = await self.file_service.read_file(f"{project_id}/{target_file}")
                original_content = orig
                frontmatter = fm
            except Exception as e:
                logger.warning("重新读取文件 %s/%s 失败: %s", project_id, target_file, e)

            if output_mode in ("rewrite", "overwrite"):
                await self.file_service.write_file(f"{project_id}/{target_file}", final_output, frontmatter)
            elif output_mode == "append":
                new_content = (original_content + "\n\n" + final_output).strip()
                await self.file_service.write_file(f"{project_id}/{target_file}", new_content, frontmatter)
            elif output_mode == "dimension_file":
                await self.file_service.write_file(f"{project_id}/{target_file}", final_output, frontmatter)

        yield {"event": "done", "data": json.dumps({
            "task_id": task_id,
            "message": "管线执行完成",
        })}

    def get_pipeline_detail(self, name: str) -> dict:
        """获取管线详情（含每步 prompt 内容）"""
        pipeline = self.load_pipeline(name)
        steps = []
        for step in pipeline.steps:
            prompt_path = self._get_step_prompt_path(name, step.id)
            prompt_content = ""
            if prompt_path.exists():
                prompt_content = prompt_path.read_text(encoding="utf-8")
            steps.append({
                "id": step.id,
                "label": step.label,
                "prompt_content": prompt_content,
                "fallback": step.fallback,
            })
        return {
            "name": pipeline.name,
            "label": pipeline.label,
            "steps": steps,
        }

    def save_step_prompt(self, pipeline_name: str, step_id: str, content: str) -> None:
        """保存步骤的 prompt 内容"""
        prompt_dir = self._get_pipeline_dir() / pipeline_name
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_dir / f"{step_id}.md"
        prompt_file.write_text(content, encoding="utf-8")

    def save_pipeline_yaml(self, name: str, label: str, steps: list[dict]) -> None:
        """保存管线 YAML 定义"""
        yaml_path = self._get_pipeline_yaml_path(name)
        data = {
            "name": name,
            "label": label,
            "steps": [
                {"id": s["id"], "label": s["label"], "prompt": f"pipeline/{name}/{s['id']}", "fallback": s.get("fallback")}
                for s in steps
            ],
        }
        yaml_path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
