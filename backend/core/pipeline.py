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
from backend.core.candidate_service import CandidateService
from backend.core.exceptions import MoyunFileNotFoundError
from backend.core.prompt_versioning import archive_prompt
from backend.schemas.pipeline import PipelineDef, PipelineStepDef
from backend.schemas.candidate import CandidateAction

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
        system_prompts_path: Path | None = None,
    ):
        self.prompts_path = Path(prompts_path)
        self.system_prompts_path = system_prompts_path
        self.llm_service = llm_service
        self.file_service = file_service
        self.source = source
        # 同一章内 context 步骤输出缓存，key=章目录路径 → context 文本
        self._context_cache: dict[str, str] = {}
        
        # 构建搜索路径：用户自定义路径优先，系统路径次之
        search_paths = [str(self.prompts_path)]
        if self.system_prompts_path:
            search_paths.append(str(self.system_prompts_path))
        self.env = Environment(
            loader=FileSystemLoader(search_paths),
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

    def _find_pipeline_yaml(self, name: str) -> Path | None:
        """查找管线 YAML 文件（用户路径优先，系统路径次之）"""
        # 优先从用户路径查找
        user_path = self._get_pipeline_yaml_path(name)
        if user_path.exists():
            return user_path
        
        # 从系统路径查找
        if self.system_prompts_path:
            system_path = self.system_prompts_path / "pipeline" / f"{name}.yaml"
            if system_path.exists():
                return system_path
        
        return None

    def load_pipeline(self, name: str) -> PipelineDef:
        """加载管线 YAML 定义"""
        yaml_path = self._find_pipeline_yaml(name)
        if not yaml_path:
            raise PipelineError(f"管线不存在: {name}")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            return PipelineDef(**data)
        except Exception as e:
            raise PipelineError(f"加载管线定义失败 {name}: {e}")

    def list_pipelines(self) -> list[PipelineDef]:
        """列出所有可用管线（系统预置 + 用户自定义）"""
        pipelines = []
        seen = set()

        # 先从系统路径加载
        if self.system_prompts_path:
            system_pipeline_dir = self.system_prompts_path / "pipeline"
            if system_pipeline_dir.exists():
                for f in sorted(system_pipeline_dir.glob("*.yaml")):
                    try:
                        pipeline = self.load_pipeline(f.stem)
                        seen.add(pipeline.name)
                        pipelines.append(pipeline)
                    except Exception as e:
                        logger.warning("跳过无效系统管线定义 %s: %s", f.name, e)

        # 再从用户路径加载（覆盖同名系统管线）
        pipeline_dir = self._get_pipeline_dir()
        if pipeline_dir.exists():
            for f in sorted(pipeline_dir.glob("*.yaml")):
                try:
                    pipeline = self.load_pipeline(f.stem)
                    # 如果用户定义了同名管线，替换系统管线
                    if pipeline.name in seen:
                        idx = next(i for i, p in enumerate(pipelines) if p.name == pipeline.name)
                        pipelines[idx] = pipeline
                    else:
                        pipelines.append(pipeline)
                        seen.add(pipeline.name)
                except Exception as e:
                    logger.warning("跳过无效用户管线定义 %s: %s", f.name, e)

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
        require_candidate: bool = False,
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

                # 从 file_path 解析章节目录（作为 workflow loop_vars 的兜底）
                if target_file:
                    import re
                    m = re.search(r'vol-(\d+)/ch-(\d+)(?:/sec-(\d+))?', target_file)
                    if m:
                        step_vars.setdefault("vol", m.group(1))
                        step_vars.setdefault("ch", m.group(2))
                        step_vars.setdefault("sec", m.group(3) or "1")

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
                max_prompt_tokens = self.llm_service.config.max_prompt_tokens
                
                if prompt_tokens > max_prompt_tokens:
                    warning_msg = f"Prompt 过长（约 {prompt_tokens} tokens），超出模型限制 {max_prompt_tokens} tokens"
                    if prompt_tokens > self.llm_service.config.context_window:
                        warning_msg += "，建议：减少 recent_context / 只引用当前章摘要 / 分段执行"
                    yield {"event": "error", "data": json.dumps({
                        "message": warning_msg,
                        "task_id": task_id,
                        "warning": True,
                        "prompt_tokens": prompt_tokens,
                        "max_prompt_tokens": max_prompt_tokens,
                        "context_window": self.llm_service.config.context_window,
                    })}

                # context 步骤缓存：同一章内复用已生成的上下文分析
                if step.id == "context" and target_file:
                    import re as _re
                    ch_match = _re.match(r"^(.*?ch-\d+)/", target_file)
                    if ch_match:
                        ch_key = ch_match.group(1)
                        cache_key = await self._build_context_cache_key(project_id, ch_key)
                        cached = self._context_cache.get(cache_key)
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
                    # update_story_state 的输出是结构化状态数据，不流式到编辑器
                    if step.id == "update_story_state":
                        continue
                    # 其他步骤的 LLM 输出实时流式到前端
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
                        ch_key = ch_match.group(1)
                        cache_key = await self._build_context_cache_key(project_id, ch_key)
                        self._context_cache[cache_key] = step_output

                # 如果步骤指定了 output 路径，将步骤输出写入对应文件
                if step.output and step_output:
                    output_path = step.output
                    if self._is_dangerous_output(output_path):
                        logger.warning("跳过危险路径写入: %s (需要候选稿机制)", output_path)
                        # 将输出保存为候选稿
                        try:
                            candidate_service = CandidateService(self.file_service)
                            candidate = await candidate_service.create_candidate(
                                project_id=project_id,
                                source_path=output_path,
                                action=CandidateAction.MODIFY,
                                content=step_output,
                            )
                            logger.info("危险路径输出已保存为候选稿: %s -> %s", output_path, candidate.id)
                            yield {"event": "candidate_created", "data": json.dumps({
                                "task_id": task_id,
                                "candidate_id": candidate.id,
                                "source_path": output_path,
                                "action": CandidateAction.MODIFY.value,
                            })}
                        except Exception as e:
                            logger.warning("创建候选稿失败: %s", e)
                    else:
                        try:
                            await self.file_service.write_file(
                                f"{project_id}/{output_path}", step_output, None
                            )
                            logger.info("步骤输出已写入: %s", output_path)
                        except Exception as e:
                            logger.warning("步骤输出写入失败 %s: %s", output_path, e)

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
        # 注意：最后一步如果是 diff/update_story_state，输出不是章节内容，
        # 此时应使用上一步（润色/改写/生成）的输出作为文件内容
        last_step = pipeline.steps[-1]
        if last_step.id in ("diff", "update_story_state") and len(pipeline.steps) >= 2:
            final_output = step_outputs.get(pipeline.steps[-2].id, "")
        else:
            final_output = step_outputs.get(last_step.id, "")
        original_content = ""
        frontmatter = None
        candidate_id = None
        
        if final_output and target_file:
            try:
                orig, fm = await self.file_service.read_file(f"{project_id}/{target_file}")
                original_content = orig
                frontmatter = fm
            except Exception as e:
                logger.warning("重新读取文件 %s/%s 失败: %s", project_id, target_file, e)

            # 判断是否需要生成候选稿
            should_use_candidate = require_candidate or (output_mode == "rewrite" and original_content)
            
            if should_use_candidate and original_content:
                # 生成候选稿而不是直接覆盖
                candidate_service = CandidateService(self.file_service)
                action = self._infer_candidate_action(pipeline_name, output_mode)
                candidate = await candidate_service.create_candidate(
                    project_id=project_id,
                    source_path=target_file,
                    action=action,
                    content=final_output,
                )
                candidate_id = candidate.id
                logger.info("已生成候选稿: %s -> %s", target_file, candidate_id)
                yield {"event": "candidate_created", "data": json.dumps({
                    "task_id": task_id,
                    "candidate_id": candidate_id,
                    "source_path": target_file,
                    "action": action.value,
                })}
            elif output_mode in ("rewrite", "overwrite"):
                await self.file_service.write_file(f"{project_id}/{target_file}", final_output, frontmatter)
            elif output_mode == "append":
                new_content = (original_content + "\n\n" + final_output).strip()
                await self.file_service.write_file(f"{project_id}/{target_file}", new_content, frontmatter)
            elif output_mode == "dimension_file":
                # dimension_file 模式：各步骤已通过 step.output 写入各自文件
                # 不覆写目标文件（如正文章节），跳过 final write
                pass

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
        # — 更新 recent-context.md —
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            file_name = target_file.split("/")[-1]
            
            # 生成结构化摘要
            structured_summary = self._generate_structured_summary(target_file, content)
            
            entry = f"\n## {timestamp} - {file_name}\n{structured_summary}\n"

            try:
                existing, _ = await self.file_service.read_file(f"{project_id}/recent-context.md")
                blocks = [b for b in existing.split("\n## ") if b.strip()]
                blocks = blocks[-4:]
                new_content = "\n## ".join(blocks).strip()
                if not new_content.startswith("# "):
                    new_content = "# 近期上下文\n" + new_content
                new_content += entry
            except Exception:
                new_content = f"# 近期上下文\n{entry}"

            await self.file_service.write_file(f"{project_id}/recent-context.md", new_content, None)
        except Exception as e:
            logger.warning("更新 recent-context.md 失败: %s", e)

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

    def _generate_structured_summary(self, target_file: str, content: str) -> str:
        """生成结构化的上下文摘要"""
        lines = content.strip().split('\n')[:20]
        text_preview = '\n'.join(lines)
        
        # 提取关键信息
        chars = self._extract_characters(content)
        locations = self._extract_locations(content)
        
        summary = []
        
        # 场景摘要
        summary.append("【场景摘要】")
        summary.append(text_preview[:200].strip() + "..." if len(text_preview) > 200 else text_preview)
        
        # 人物
        if chars:
            summary.append("\n【人物】")
            summary.append(", ".join(chars[:5]))
        
        # 地点
        if locations:
            summary.append("\n【地点】")
            summary.append(", ".join(locations[:3]))
        
        # 下一场承接点（取最后几句）
        last_lines = content.strip().split('\n')[-3:]
        last_text = '\n'.join(last_lines).strip()
        if last_text:
            summary.append("\n【承接点】")
            summary.append(last_text[:100].strip())
        
        return '\n'.join(summary)

    def _extract_characters(self, content: str) -> list[str]:
        """简单提取人物名称（基于中文姓名模式和常见角色特征）"""
        import re
        chars = []
        
        # 匹配中文姓名（2-4个汉字）
        name_pattern = re.compile(r'([\u4e00-\u9fa5]{2,4})(?=[：:，,。！!？?、])')
        matches = name_pattern.findall(content)
        chars.extend(matches)
        
        # 匹配带称呼的人名
        title_pattern = re.compile(r'(先生|小姐|夫人|公子|大侠|掌门|帮主|陛下|殿下|将军|丞相)\s*([\u4e00-\u9fa5]{1,4})')
        for match in title_pattern.findall(content):
            chars.append(f"{match[0]}{match[1]}")
        
        # 去重并返回
        return list(set(chars))

    def _extract_locations(self, content: str) -> list[str]:
        """简单提取地点名称"""
        import re
        locations = []
        
        # 匹配常见地点后缀
        loc_pattern = re.compile(r'([\u4e00-\u9fa5]{2,6})(城|镇|村|庄|府|殿|宫|楼|阁|山|谷|湖|河|海|路|街|巷|院|馆|寺|庙|庵|观)')
        matches = loc_pattern.findall(content)
        for match in matches:
            locations.append(f"{match[0]}{match[1]}")
        
        # 匹配方位词
        dir_pattern = re.compile(r'(东|南|西|北|中|前|后|左|右|上|下)([\u4e00-\u9fa5]{1,4})(宫|殿|厅|房|室|门|院)')
        for match in dir_pattern.findall(content):
            locations.append(f"{match[0]}{match[1]}{match[2]}")
        
        return list(set(locations))

    async def _build_context_cache_key(self, project_id: str, chapter_path: str) -> str:
        """构建 context 缓存键，包含相关文件的修改时间戳"""
        import hashlib
        
        # 需要监控的文件列表
        watched_files = [
            f"{project_id}/style-guide.md",
            f"{project_id}/story-state.md",
            f"{project_id}/recent-context.md",
            f"{project_id}/outline.md",
            f"{project_id}/meta.json",
        ]
        
        # 添加章节目录下的文件（.md 和 ch-meta.json）
        try:
            chapter_dir = self.file_service._resolve_path(f"{project_id}/{chapter_path}")
            if chapter_dir.exists() and chapter_dir.is_dir():
                for item in chapter_dir.iterdir():
                    if item.is_file():
                        if item.suffix == ".md":
                            watched_files.append(f"{project_id}/{chapter_path}/{item.name}")
                        elif item.name == "ch-meta.json":
                            watched_files.append(f"{project_id}/{chapter_path}/ch-meta.json")
        except Exception:
            pass
        
        # 获取所有文件的修改时间
        mtimes = []
        for file_path in watched_files:
            try:
                full_path = self.file_service._resolve_path(file_path)
                if full_path.exists():
                    mtimes.append(str(full_path.stat().st_mtime))
                else:
                    mtimes.append("0")
            except Exception:
                mtimes.append("0")
        
        # 构建缓存键（带项目哈希前缀，便于按项目清除）
        key_parts = [project_id, chapter_path] + mtimes
        key_string = "|".join(key_parts)
        content_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        # 添加项目哈希前缀
        project_hash = self._hash_project_id(project_id)
        return f"{project_hash}:{content_hash}"

    def clear_context_cache(self, project_id: str | None = None) -> None:
        """清除 context 缓存
        
        Args:
            project_id: 可选，只清除指定项目的缓存；不传则清除全部
        """
        if project_id:
            self._context_cache = {
                key: val for key, val in self._context_cache.items()
                if not key.startswith(self._hash_project_id(project_id))
            }
        else:
            self._context_cache.clear()
        logger.info("Context 缓存已清除 (project_id=%s)", project_id)

    def _hash_project_id(self, project_id: str) -> str:
        """生成项目ID的哈希值用于缓存键前缀"""
        import hashlib
        return hashlib.md5(project_id.encode()).hexdigest()[:8]

    def _infer_candidate_action(self, pipeline_name: str, output_mode: str) -> CandidateAction:
        """根据管线名称和输出模式推断候选稿动作类型"""
        pipeline_name_lower = pipeline_name.lower()
        
        if "polish" in pipeline_name_lower or "润色" in pipeline_name:
            return CandidateAction.POLISH
        elif "expand" in pipeline_name_lower or "扩写" in pipeline_name:
            return CandidateAction.EXPAND
        elif "shrink" in pipeline_name_lower or "缩写" in pipeline_name:
            return CandidateAction.SHRINK
        elif "chat" in pipeline_name_lower or "对话" in pipeline_name:
            return CandidateAction.CHAT
        elif "continue" in pipeline_name_lower or "续写" in pipeline_name:
            return CandidateAction.CONTINUE
        elif output_mode == "append":
            return CandidateAction.CONTINUE
        elif "modify" in pipeline_name_lower or "修改" in pipeline_name:
            return CandidateAction.MODIFY
        else:
            return CandidateAction.REWRITE

    def _is_dangerous_output(self, output_path: str) -> bool:
        """判断输出路径是否为危险路径（需要候选稿保护）
        
        危险路径包括：
        - 章节文件（chapters/vol-xx/ch-xx/sec-xx.md）
        - 核心状态文件（style-guide.md, story-state.md, recent-context.md, outline.md）
        
        安全路径包括：
        - materials/extracted/ 目录
        - .candidates/ 目录
        - revision-log/ 目录
        - logs/ 目录
        """
        output_path_lower = output_path.lower()
        
        # 安全路径白名单
        safe_prefixes = (
            "materials/extracted/",
            "materials/drafts/",
            ".candidates/",
            "revision-log/",
            "logs/",
        )
        for prefix in safe_prefixes:
            if output_path_lower.startswith(prefix):
                return False
        
        # 危险路径检测
        dangerous_patterns = (
            "/sec-",           # 章节文件
            "style-guide.md",  # 文风指南
            "story-state.md",  # 故事状态
            "recent-context.md", # 近期上下文
            "outline.md",      # 大纲
            "meta.json",       # 项目元数据
            "ch-meta.json",    # 章节元数据
        )
        for pattern in dangerous_patterns:
            if pattern in output_path_lower:
                return True
        
        return False

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
            # 优先用 step.prompt 路径（实际用于生成的模板）
            prompt_content = ""
            if step.prompt:
                prompt_path = self.prompts_path / f"{step.prompt}.md"
                if prompt_path.exists():
                    prompt_content = prompt_path.read_text(encoding="utf-8")
            # 如果 step.prompt 指向 pipeline 内置路径，补充尝试
            if not prompt_content:
                alt_path = self._get_step_prompt_path(name, step.id)
                if alt_path.exists():
                    prompt_content = alt_path.read_text(encoding="utf-8")
            steps.append({
                "id": step.id,
                "label": step.label,
                "prompt_content": prompt_content,
                "fallback": step.fallback,
                "confirm": step.confirm,
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
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
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
