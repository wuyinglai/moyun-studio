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
import difflib
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

try:
    import tiktoken
except ImportError:
    tiktoken = None

import yaml
from jinja2 import Environment, FileSystemLoader

from backend.core.llm import LLMService
from backend.core.file_ops import FileService
from backend.core.exceptions import MoyunFileNotFoundError
from backend.core.prompt_versioning import archive_prompt
from backend.schemas.pipeline import PipelineDef, PipelineStepDef

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


REFERENCE_PATTERN = re.compile(r"@\{([^}]+)\}")


class PipelineRunner:
    """管线执行引擎"""

    def __init__(
        self,
        prompts_path: Path,
        llm_service: LLMService,
        file_service: FileService,
        source: str = "system",
    ):
        self.prompts_path = Path(prompts_path)
        self.llm_service = llm_service
        self.file_service = file_service
        self.source = source
        # 同一章内 context 步骤输出缓存，key=章目录路径 → context 文本
        self._context_cache: dict[str, str] = {}
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

    def render_prompt(self, relative_path: str, variables: dict) -> str:
        """使用 Jinja2 渲染 prompt 模板"""
        template = self.env.get_template(relative_path)
        return template.render(**variables)

    async def resolve_references(self, text: str, project_id: str) -> str:
        """解析 @{path} 引用为文件内容

        @{style-guide.md} -> 读取 {project_id}/style-guide.md 的内容
        只做单层解析（不递归处理被引用文件中的 @{}）。
        """
        if not text:
            return text

        result = text
        while True:
            match = REFERENCE_PATTERN.search(result)
            if not match:
                break
            file_path = match.group(1)
            try:
                content, _ = await self.file_service.read_file(f"{project_id}/{file_path}")
                replacement = content if content else ""
            except (MoyunFileNotFoundError, OSError):
                replacement = f"\n<!-- 文件 {file_path} 不存在 -->\n"
            result = result[:match.start()] + replacement + result[match.end():]

        return result

    async def load_project_meta(self, project_id: str) -> dict:
        """从项目 meta.json 加载项目配置变量

        返回 {变量名: 值} 字典，读取失败时返回空字典。
        映射关系：meta.json 的字段直接作为模板变量名（genre, theme, tone 等）。
        """
        try:
            content, _ = await self.file_service.read_file(f"{project_id}/meta.json")
            if content:
                meta = json.loads(content)
                # 提取需要的字段，忽略内部字段（project_id, created_at 等）
                keys = ["genre", "theme", "tone", "background", "writing_style",
                        "target_word_count", "name"]
                return {k: meta.get(k, "") for k in keys}
        except (json.JSONDecodeError, MoyunFileNotFoundError, OSError):
            pass
        return {}

    async def load_system_variables(self, project_id: str) -> dict:
        """从项目目录加载系统变量

        返回 {变量名: 文件内容} 字典，文件不存在或读取失败时返回空字符串。

        额外从 target_file 对应的 ch-meta.json 加载 pending_foreshadowing 和 active_quests。
        """
        system_file_map = {
            "style_guide": "style-guide.md",
            "story_state": "story-state.md",
            "recent_context": "recent-context.md",
            "outline": "outline.md",
        }
        vars = {}
        for var_name, rel_path in system_file_map.items():
            try:
                content, _ = await self.file_service.read_file(f"{project_id}/{rel_path}")
                vars[var_name] = content
            except (MoyunFileNotFoundError, OSError):
                vars[var_name] = ""
        return vars

    async def load_chapter_vars(self, project_id: str, target_file: str) -> dict:
        """从章节元数据加载模板变量

        从 target_file（如 chapters/vol-01/ch-001/sec-001.md）推导 ch-meta.json 路径，
        提取 pending_foreshadowing 和 active_quests。
        """
        vars = {
            "pending_foreshadowing": "",
            "active_quests": "",
        }
        if not target_file or "/sec-" not in target_file:
            return vars

        parts = target_file.split("/")
        if len(parts) < 3:
            return vars
        chapter_dir = "/".join(parts[:-1])
        meta_path = f"{project_id}/{chapter_dir}/ch-meta.json"
        try:
            content, _ = await self.file_service.read_file(meta_path)
            if content:
                meta = json.loads(content)
                foreshadowing = meta.get("pending_foreshadowing", [])
                vars["pending_foreshadowing"] = json.dumps(foreshadowing, ensure_ascii=False) if foreshadowing else ""
                quests = meta.get("active_quests", [])
                vars["active_quests"] = json.dumps(quests, ensure_ascii=False) if quests else ""
        except (json.JSONDecodeError, MoyunFileNotFoundError, OSError):
            pass
        return vars

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
        llm_extra_kwargs: dict | None = None,
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

        logger.info(
            "管线开始执行: %s (project=%s, target=%s, mode=%s)",
            pipeline_name, project_id, target_file, output_mode,
        )

        # 加载系统变量（文风指南、故事状态、近期上下文、大纲）
        system_vars = await self.load_system_variables(project_id)

        # 加载项目配置（genre, theme, tone 等）
        project_vars = await self.load_project_meta(project_id)

        # 加载章节变量（pending_foreshadowing, active_quests）
        chapter_vars = await self.load_chapter_vars(project_id, target_file or "")

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
                    **system_vars,
                    **project_vars,
                    **chapter_vars,
                    **extra_vars,
                }

                # 渲染 prompt 模板（使用 step.prompt 保证与 YAML 定义一致）
                prompt_relative = f"{step.prompt}.md"
                prompt_text = self.render_prompt(prompt_relative, step_vars)

                # 解析 @{path} 引用为文件内容
                prompt_text = await self.resolve_references(prompt_text, project_id)

                # 发送渲染后的 prompt
                yield {"event": "prompt", "data": json.dumps({
                    "prompt": prompt_text,
                    "task_id": task_id,
                    "step_id": step.id,
                })}

                # G0118: 自动 token 检查 — 估算 prompt token 数，超限时发出警告
                prompt_tokens = self._estimate_tokens(prompt_text)
                if prompt_tokens > 120000:
                    yield {"event": "error", "data": json.dumps({
                        "message": f"Prompt 过长（约 {prompt_tokens} tokens），可能超出模型上下文限制",
                        "task_id": task_id,
                        "warning": True,
                    })}

                # context 步骤缓存：同一章内复用已生成的上下文分析
                if step.id == "context" and target_file:
                    import re as _re
                    ch_match = _re.match(r"^(.*?ch-\d+)/", target_file)
                    if ch_match:
                        ch_key = ch_match.group(1)
                        cached = self._context_cache.get(ch_key)
                        if cached is not None:
                            logger.info("复用 context 缓存: %s", ch_key)
                            step_output = cached
                            yield {"event": "prompt", "data": json.dumps({
                                "prompt": prompt_text,
                                "task_id": task_id,
                                "step_id": step.id,
                                "cached": True,
                            })}
                            step_outputs[step.id] = step_output
                            yield {"event": "step_done", "data": json.dumps({
                                "step_id": step.id,
                                "label": step.label,
                                "status": "done",
                            })}
                            continue

                # 调用 LLM
                messages = [
                    {"role": "system", "content": "你是一个文本处理工具。根据用户的指令处理文本，只输出处理结果本身，严禁输出任何解释、分析、问候、标题、编号或其他附加内容。"},
                    {"role": "user", "content": prompt_text},
                ]
                step_output = ""
                extra_kwargs = dict(llm_extra_kwargs or {})

                async for chunk in self.llm_service.complete(
                    messages,
                    stop_event=stop_event,
                    timeout=180,
                    **extra_kwargs,
                ):
                    step_output += chunk
                    # 所有步骤的 LLM 输出实时流式到前端
                    yield {"event": "generation", "data": json.dumps({
                        "delta": chunk,
                        "task_id": task_id,
                    })}

                step_outputs[step.id] = step_output

                # context 步骤完成后缓存到内存，同章后续 sec 复用
                if step.id == "context" and target_file:
                    import re as _re
                    ch_match = _re.match(r"^(.*?ch-\d+)/", target_file)
                    if ch_match:
                        self._context_cache[ch_match.group(1)] = step_output

                # 如果步骤指定了 output 路径，将步骤输出写入对应文件
                if step.output and step_output:
                    try:
                        await self.file_service.write_file(
                            f"{project_id}/{step.output}", step_output, None
                        )
                        logger.info("步骤输出已写入: %s", step.output)
                    except Exception as e:
                        logger.warning("步骤输出写入失败 %s: %s", step.output, e)

                logger.info(
                    "管线步骤完成: %s/%s (output_len=%d)",
                    pipeline_name, step.id, len(step_output),
                )

                yield {"event": "step_done", "data": json.dumps({
                    "step_id": step.id,
                    "label": step.label,
                    "status": "done",
                })}

            except Exception as e:
                logger.error(
                    "管线步骤失败: %s/%s (fallback=%s, is_final=%s) - %s",
                    pipeline_name, step.id, step.fallback, is_final, e,
                )
                if step.fallback and step.fallback in step_outputs:
                    logger.info("回退到步骤 %s 的输出 (管线: %s)", step.fallback, pipeline_name)
                    step_outputs[step.id] = step_outputs[step.fallback]
                    # 回退时也尝试写入步骤的 output 文件
                    if step.output and step_outputs[step.id]:
                        try:
                            await self.file_service.write_file(
                                f"{project_id}/{step.output}", step_outputs[step.id], None
                            )
                        except Exception as e:
                            logger.warning("步骤输出写入失败 %s: %s", step.output, e)
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
        # 注意：最后一步如果是 diff 摘要步骤，输出是修改摘要而非实际内容，
        # 此时应使用上一步（润色/改写/生成）的输出作为文件内容
        last_step = pipeline.steps[-1]
        if last_step.id == "diff" and len(pipeline.steps) >= 2:
            final_output = step_outputs.get(pipeline.steps[-2].id, "")
        else:
            final_output = step_outputs.get(last_step.id, "")
        original_content = ""
        frontmatter = None
        if final_output and target_file:
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

        # 生成完成后自动更新 story-state 和 recent-context
        if target_file and final_output:
            await self._update_after_generation(project_id, target_file, final_output, original_content)

        # 内容有变化时生成 AI 修改摘要
        if original_content and final_output and final_output != original_content:
            try:
                summary = await self._generate_diff_summary(
                    project_id, target_file, original_content, final_output, task_id
                )
                if summary:
                    yield {"event": "diff_summary", "data": json.dumps({
                        "summary": summary,
                        "task_id": task_id,
                        "target_file": target_file,
                    })}
                    # 将摘要保存到 revision-log
                    await self._save_diff_summary_to_revision(project_id, target_file, summary)
            except Exception as e:
                logger.warning("生成修改摘要失败: %s", e)

        logger.info(
            "管线执行完成: %s (steps=%d, final_output_len=%d)",
            pipeline_name, total_steps, len(final_output),
        )

        yield {"event": "done", "data": json.dumps({
            "task_id": task_id,
            "message": "管线执行完成",
        })}

    async def _update_after_generation(self, project_id: str, target_file: str, content: str, original_content: str = "") -> None:
        # — 创建修改日志（仅当内容有变化且目标文件是章节文件） —
        if original_content and content != original_content and "/sec-" in target_file:
            try:
                # 从 target_file (如 chapters/vol-01/ch-001/sec-001.md) 提取章节目录
                parts = target_file.split("/")
                if len(parts) >= 3:
                    chapter_dir = "/".join(parts[:-1])  # chapters/vol-01/ch-001

                    # 生成 diff
                    before_lines = original_content.splitlines(keepends=True)
                    after_lines = content.splitlines(keepends=True)
                    diff = "".join(difflib.unified_diff(
                        before_lines, after_lines,
                        fromfile="修改前", tofile="修改后", lineterm=""
                    ))

                    # 统计字数
                    def _wc(text: str) -> int:
                        return len(re.findall(r'[一-鿿]', text)) + len(re.findall(r'[a-zA-Z]+', text))

                    log_entry = {
                        "id": f"rev-{uuid.uuid4().hex[:8]}",
                        "chapter_path": target_file,
                        "revision_type": "ai_rewrite",
                        "description": f"管线生成: {target_file.split('/')[-1]}",
                        "word_count_before": _wc(original_content),
                        "word_count_after": _wc(content),
                        "diff": diff,
                        "created_at": datetime.now().isoformat(),
                    }

                    log_path = f"{project_id}/{chapter_dir}/revision-log/{log_entry['id']}.json"
                    await self.file_service.write_file(log_path, json.dumps(log_entry, ensure_ascii=False, indent=2), None)
            except Exception as e:
                logger.warning("创建修改日志失败: %s", e)

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数

        优先使用 tiktoken，回退到字符估算。
        """
        if tiktoken:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text))
            except Exception:
                pass
        # 回退：字符估算
        from backend.utils.token_utils import estimate_tokens_fallback
        return estimate_tokens_fallback(text)

    async def _generate_diff_summary(
        self,
        project_id: str,
        target_file: str,
        original_content: str,
        modified_content: str,
        task_id: str,
    ) -> str | None:
        """生成 AI 修改摘要

        使用 diff-summary 管线的 analyze 步骤 prompt，调用 LLM 分析修改内容。
        返回结构化分析报告文本，失败时返回 None。
        """
        try:
            # 加载 diff-summary 管线的 analyze 步骤
            prompt_rel = "pipeline/diff-summary/analyze.md"
            variables = {
                "original_content": original_content,
                "modified_content": modified_content,
                "file_content": modified_content,
                "project_id": project_id,
                "file_path": target_file,
                "user_input": "",
            }
            prompt_text = self.render_prompt(prompt_rel, variables)

            messages = [
                {"role": "system", "content": "你是一个文本处理工具。根据用户的指令处理文本，只输出处理结果本身，严禁输出任何解释、分析、问候、标题、编号或其他附加内容。"},
                {"role": "user", "content": prompt_text},
            ]
            summary_parts = []
            async for chunk in self.llm_service.complete(messages, timeout=60):
                summary_parts.append(chunk)

            summary = "".join(summary_parts)
            if summary.strip():
                return summary
        except Exception as e:
            logger.warning("生成修改摘要 LLM 调用失败: %s", e)
        return None

    async def _save_diff_summary_to_revision(
        self,
        project_id: str,
        target_file: str,
        summary: str,
    ) -> None:
        """将修改摘要保存到 revision-log 目录"""
        if "/sec-" not in target_file:
            return
        try:
            parts = target_file.split("/")
            if len(parts) >= 3:
                chapter_dir = "/".join(parts[:-1])
                entry_id = f"rev-ds-{uuid.uuid4().hex[:8]}"
                log_entry = {
                    "id": entry_id,
                    "chapter_path": target_file,
                    "revision_type": "diff_summary",
                    "description": f"AI 修改摘要: {target_file.split('/')[-1]}",
                    "summary": summary,
                    "created_at": datetime.now().isoformat(),
                }
                log_path = f"{project_id}/{chapter_dir}/revision-log/{entry_id}.json"
                await self.file_service.write_file(
                    log_path, json.dumps(log_entry, ensure_ascii=False, indent=2), None
                )
        except Exception as e:
            logger.warning("保存修改摘要到 revision-log 失败: %s", e)

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
            "source": self.source,
            "steps": steps,
        }

    def save_step_prompt(self, pipeline_name: str, step_id: str, content: str) -> None:
        """保存步骤的 prompt 内容（保存前自动归档旧版本）"""
        prompt_dir = self._get_pipeline_dir() / pipeline_name
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_dir / f"{step_id}.md"
        # 归档旧版本
        if prompt_file.exists():
            archive_prompt(prompt_file, self.prompts_path, note=f"更新 {pipeline_name}/{step_id}")
        prompt_file.write_text(content, encoding="utf-8")

    def save_pipeline_yaml(self, name: str, label: str, steps: list[dict]) -> None:
        """保存管线 YAML 定义（保存前自动归档旧版本）"""
        yaml_path = self._get_pipeline_yaml_path(name)
        # 归档旧版本
        if yaml_path.exists():
            archive_prompt(yaml_path, self.prompts_path, note=f"更新 {name} 定义")
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
