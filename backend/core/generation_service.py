"""墨韵 - 生成任务服务

职责：
- 批量生成编排
- 流式生成编排（回退模式）
- 任务停止信号管理
"""

import asyncio
from collections.abc import AsyncGenerator
import json
import logging
from pathlib import Path

from backend.application.scene_service import SceneService
from backend.config import Settings
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.pipeline import PipelineError, PipelineRunner
from backend.domain.events import (
    make_pipeline_started_event,
    make_pipeline_step_completed_event,
    make_pipeline_step_failed_event,
    make_task_completed_event,
)
from backend.policies.candidate_policy import should_create_candidate
from backend.schemas.llm import BatchGenerateItem, BatchGenerateResponse

logger = logging.getLogger(__name__)


# prompt_type → pipeline 映射
GENERATE_PIPELINE_MAP = {
    "generate/continuation": ("generate", "append"),
    "generate/rewrite": ("rewrite", "candidate"),
    "generate/title": ("title", "write_scene"),
}

# Action name compatibility mapping
ACTION_ALIAS = {
    "write_next_scene": "generate",
    "write_current_scene": "generate",
    "rewrite_current_scene": "rewrite",
    "polish_current_scene": "polish",
    "chat_edit_current_scene": "chat",
}


class GenerationService:
    """生成任务服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.file_service = FileService(
            settings.projects_path,
            max_file_write_size=settings.max_file_write_size,
        )
        self.scene_service = SceneService(self.file_service)
        self._stop_signals: dict[str, asyncio.Event] = {}

    # ─── 停止信号管理 ────────────────────────────────────

    def create_stop_signal(self, task_id: str) -> asyncio.Event:
        signal = asyncio.Event()
        self._stop_signals[task_id] = signal
        return signal

    def remove_stop_signal(self, task_id: str):
        self._stop_signals.pop(task_id, None)

    def stop_task(self, task_id: str | None = None):
        if task_id and task_id in self._stop_signals:
            self._stop_signals[task_id].set()
        else:
            for sig in self._stop_signals.values():
                sig.set()

    # ─── 流式生成 ────────────────────────────────────────

    async def generate_stream(
        self,
        project_id: str,
        file_path: str,
        prompt_type: str,
        extra_vars: dict,
        mode: str,
        task_id: str,
        event_bus=None,
    ) -> AsyncGenerator[dict, None]:
        """流式生成（支持管线模式和回退模式）

        Yields:
            SSE 事件字典: {"event": ..., "data": ...}
        """
        # Resolve action aliases for backward compatibility
        resolved_mode = ACTION_ALIAS.get(mode, mode)

        llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, self.settings)
        svc = LLMService.from_workspace_config(llm_cfg)
        runner = PipelineRunner(self.settings.prompts_path, svc, self.file_service, system_prompts_path=self.settings.system_prompts_path)

        # 构建 LLM 额外参数（含 thinking 和 reasoning_format 配置）
        llm_extra_kwargs = {}
        thinking = llm_cfg.get("thinking", self.settings.llm_thinking)
        if thinking and "claude" in svc.config.model:
            llm_extra_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2000}
        reasoning_format = llm_cfg.get("reasoningFormat", self.settings.llm_reasoning_format)
        if reasoning_format:
            llm_extra_kwargs["reasoning_format"] = reasoning_format

        # 管线模式
        if prompt_type in GENERATE_PIPELINE_MAP:
            pipeline_name, output_mode = GENERATE_PIPELINE_MAP[prompt_type]
            try:
                async for event in runner.run(
                    pipeline_name=pipeline_name,
                    project_id=project_id,
                    target_file=file_path,
                    user_input=extra_vars.get("user_prompt", ""),
                    output_mode=output_mode,
                    extra_vars=extra_vars,
                    stop_event=self._stop_signals.get(task_id),
                    llm_extra_kwargs=llm_extra_kwargs,
                    action=mode,
                ):
                    yield event
                    if event_bus and event.get("event") in ("generation", "done", "error"):
                        event_data = json.loads(event["data"]) if isinstance(event["data"], str) else event["data"]
                        await event_bus.publish(event["event"], event_data)
            except PipelineError as e:
                logger.error("管线生成失败: %s", e)
                yield {"event": "error", "data": json.dumps({"message": str(e), "task_id": task_id})}
            return

        # ——— 回退模式 ———
        if event_bus:
            evt = make_pipeline_started_event(
                project_id=project_id,
                pipeline_name=f"生成 {file_path}",
                task_id=task_id,
                source="generation_service",
            )
            await event_bus.publish(evt.type, evt.to_sse_dict())

        yield {"event": "task_start", "data": json.dumps({"task_id": task_id})}

        try:
            logger.info("开始生成任务", extra={"task_id": task_id, "project_id": project_id, "file_path": file_path})

            try:
                content, fm, _ = await self.file_service.read_file(f"{project_id}/{file_path}")
            except Exception:
                content, fm = "", None

            variables = {
                "file_content": content,
                "file_path": file_path,
                "project_id": project_id,
                **extra_vars,
            }
            try:
                prompt_text = runner.render_prompt(f"{prompt_type}/main.md", variables)
                prompt_text = await runner.resolve_references(prompt_text, project_id)
            except Exception:
                prompt_text = f"请根据以下内容进行创作：\n\n{content}"

            yield {"event": "prompt", "data": json.dumps({"prompt": prompt_text, "task_id": task_id})}

            # token 检查（使用模型实际的上下文窗口）
            try:
                if tiktoken is not None:
                    enc = tiktoken.get_encoding("cl100k_base")
                    prompt_tokens = len(enc.encode(prompt_text))
                else:
                    from backend.utils.token_utils import estimate_tokens_fallback
                    prompt_tokens = estimate_tokens_fallback(prompt_text)
                max_prompt_tokens = svc.config.max_prompt_tokens
                context_window = svc.config.context_window

                if prompt_tokens > max_prompt_tokens:
                    warning_msg = f"Prompt 过长（约 {prompt_tokens} tokens），超出模型建议限制 {max_prompt_tokens} tokens"
                    if prompt_tokens > context_window:
                        warning_msg += "，建议：减少 recent_context / 只引用当前场景摘要 / 分段执行"
                    yield {"event": "error", "data": json.dumps({
                        "message": warning_msg,
                        "task_id": task_id,
                        "warning": True,
                        "prompt_tokens": prompt_tokens,
                        "max_prompt_tokens": max_prompt_tokens,
                        "context_window": context_window,
                    })}
            except Exception:
                logger.debug("创建候选稿失败", exc_info=True)
            messages = [{"role": "user", "content": prompt_text}]
            stop_event = self._stop_signals.get(task_id)
            generated_text = ""
            async for chunk in svc.complete(messages, stop_event=stop_event, timeout=180, **llm_extra_kwargs):
                generated_text += chunk
                yield {
                    "event": "generation",
                    "data": json.dumps({"delta": chunk, "task_id": task_id}),
                }
                if event_bus:
                    await event_bus.publish("generation", {"delta": chunk, "task_id": task_id})

            if generated_text and not (stop_event and stop_event.is_set()):
                # 安全策略：优先使用候选稿机制，避免直接覆盖
                from backend.core.candidate_service import (
                    CandidateAction,
                    CandidateService,
                )

                target_exists = content and len(content.strip()) > 0

                if should_create_candidate(resolved_mode, file_path, target_exists, target_exists):
                    # Generate candidate
                    action = CandidateAction.REWRITE if resolved_mode == "rewrite" else CandidateAction.CONTINUE
                    try:
                        candidate_svc = CandidateService(self.file_service)
                        new_content = (content + "\n\n" + generated_text) if resolved_mode == "append" and target_exists else generated_text
                        candidate = await candidate_svc.create_candidate(
                            project_id=project_id,
                            source_path=file_path,
                            action=action,
                            content=new_content,
                        )
                        logger.info("Fallback %s 已保存为候选稿: %s -> %s", resolved_mode, file_path, candidate.id)
                        yield {"event": "candidate_created", "data": json.dumps({
                            "task_id": task_id,
                            "candidate_id": candidate.id,
                            "source_path": file_path,
                            "action": action.value,
                        })}
                    except Exception as e:
                        logger.warning("创建候选稿失败: %s", e)
                elif resolved_mode == "append":
                    new_content = content + "\n\n" + generated_text if content else generated_text
                    await self.file_service.write_file(f"{project_id}/{file_path}", new_content, fm)
                    logger.info("Fallback append 直接写入（目标文件为空）: %s", file_path)

            yield {"event": "done", "data": json.dumps({"task_id": task_id, "message": "生成完成"})}
            if event_bus:
                evt = make_task_completed_event(
                    project_id=project_id,
                    task_id=task_id,
                    source="generation_service",
                )
                await event_bus.publish(evt.type, evt.to_sse_dict())
                await event_bus.publish("done", {"task_id": task_id})

        except Exception as e:
            logger.error(f"生成任务异常: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e), "task_id": task_id})}
            if event_bus:
                evt = make_pipeline_step_failed_event(
                    project_id=project_id,
                    step_id="fallback",
                    error=str(e),
                    task_id=task_id,
                    source="generation_service",
                )
                await event_bus.publish(evt.type, evt.to_sse_dict())

    # ─── 批量生成 ────────────────────────────────────────

    async def batch_generate(
        self,
        project_id: str,
        prompt_type: str,
        volume_number: int | None,
        chapter_number: int | None,
        section_numbers: list[int] | None,
        temperature: float = 0.8,
        dry_run: bool = False,
    ) -> BatchGenerateResponse:
        """批量生成场景正文（sec = 单场景，默认800字，每章5场景）"""
        project_dir = self.settings.projects_path / project_id
        from backend.core.exceptions import ProjectNotFoundError
        if not await asyncio.to_thread(project_dir.exists):
            raise ProjectNotFoundError(project_id)

        logger.info("批量生成开始", extra={
            "project_id": project_id,
            "volume": volume_number,
            "chapter": chapter_number,
            "sections": section_numbers,
        })

        # 列出目标文件
        chapters_dir = project_dir / "chapters"
        targets: list[dict] = []

        if volume_number:
            vol_dirs = [chapters_dir / f"vol-{volume_number:02d}"]
        else:
            vol_dirs = sorted(await asyncio.to_thread(lambda: list(chapters_dir.glob("vol-*"))))

        for vol_dir in vol_dirs:
            if not await asyncio.to_thread(vol_dir.is_dir):
                continue

            if chapter_number:
                ch_dirs = [vol_dir / f"ch-{chapter_number:03d}"]
            else:
                ch_dirs = sorted(await asyncio.to_thread(lambda: list(vol_dir.glob("ch-*"))))

            for ch_dir in ch_dirs:
                if not await asyncio.to_thread(ch_dir.is_dir):
                    continue

                ch_num = int(ch_dir.name.split("-")[1])

                if section_numbers:
                    sec_nums = section_numbers
                else:
                    sec_nums = []
                    for sec_file in sorted(ch_dir.glob("sec-*.md")):
                        info = self.scene_service.parse_scene_path(
                            f"chapters/{vol_dir.name}/{ch_dir.name}/{sec_file.name}"
                        )
                        if info:
                            sec_nums.append(info.scene)

                for sec_num in sec_nums:
                    target_rel_path = self.scene_service.build_scene_path(
                        int(vol_dir.name.split("-")[1]),
                        int(ch_dir.name.split("-")[1]),
                        sec_num,
                    )
                    sec_file = ch_dir / f"sec-{sec_num:03d}.md"
                    if await asyncio.to_thread(sec_file.exists):
                        targets.append({
                            "ch_dir": ch_dir,
                            "ch_num": int(ch_dir.name.split("-")[1]),
                            "sec_num": sec_num,
                            "target_rel_path": target_rel_path,
                            "target_full_path": f"{project_id}/{target_rel_path}",
                        })

        if not targets:
            return BatchGenerateResponse(tasks=[], total=0, succeeded=0, failed=0)

        # 批量生成限制
        max_count = self.settings.batch_generate_max_count
        if len(targets) > max_count:
            logger.warning("批量生成数量 %d 超过限制 %d，截断", len(targets), max_count)
            targets = targets[:max_count]

        llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, self.settings)
        svc = LLMService.from_workspace_config(llm_cfg)
        runner = PipelineRunner(self.settings.prompts_path, svc, self.file_service, system_prompts_path=self.settings.system_prompts_path)

        shared_vars = await runner.load_system_variables(project_id)
        project_meta = await runner.load_project_meta(project_id)
        pov = project_meta.get("writing_style", "") or project_meta.get("pov", "第三人称")

        tasks: list[BatchGenerateItem] = []
        succeeded = 0
        failed = 0
        template_path = f"{prompt_type}/main.md"

        for tgt in targets:
            # 保持 target_file 字段名兼容，但使用新的 full_path
            item = BatchGenerateItem(target_file=tgt["target_full_path"])

            try:
                chapter_vars = await runner.load_chapter_vars(project_id, tgt["target_rel_path"])
                chapter_title = ""
                # 修复 ch_meta_path：使用带 project_id 的完整路径
                ch_meta_path = str(Path(tgt["target_full_path"]).parent / "ch-meta.json")
                try:
                    meta_content, _, _ = await self.file_service.read_file(ch_meta_path)
                    if meta_content:
                        ch_meta = json.loads(meta_content)
                        chapter_title = ch_meta.get("title", "")
                except Exception:
                    logger.debug("读取目标文件失败", exc_info=True)

                variables = {
                    "chapter_name": f"第{tgt['ch_num']}章 {chapter_title}".strip(),
                    "chapter_number": str(tgt["ch_num"]),
                    "section_number": str(tgt["sec_num"]),
                    "pov": pov,
                    **shared_vars,
                    **chapter_vars,
                }
                prompt_text = runner.render_prompt(template_path, variables)
                prompt_text = await runner.resolve_references(prompt_text, project_id)
                item.prompt = prompt_text

                messages = [{"role": "user", "content": prompt_text}]
                # 场景级 max_tokens：单场景目标800字，约2500 tokens
                max_output_tokens = 2500

                if dry_run:
                    # Dry-run：不调用真实 LLM，不写文件，不生成 candidate
                    generated = "[DRY-RUN] simulated batch generation result"
                    logger.info("[Batch dry-run] 模拟生成: %s", tgt["target_rel_path"])
                    item.status = "dry_run"
                    item.dry_run = True
                    item.dry_run_content = generated
                    tasks.append(item)
                    succeeded += 1
                    continue

                generated = await svc.complete_sync(
                    messages, temperature=temperature, max_tokens=max_output_tokens, timeout=180
                )

                # 安全策略：检查目标文件是否为空，空则直接写入，否则生成候选稿
                from backend.policies.candidate_policy import (
                    should_create_candidate as _should_candidate,
                )

                target_content = ""
                try:
                    target_content, _, _ = await self.file_service.read_file(tgt["target_full_path"])
                except Exception:
                    logger.debug("读取上下文文件失败", exc_info=True)
                target_has_content = bool(target_content and target_content.strip())

                if _should_candidate("batch_generate", tgt["target_rel_path"], bool(target_content), target_has_content):
                    # 目标文件已有内容：生成候选稿
                    # 注意：source_path 必须是项目内相对路径（不带 project_id）
                    try:
                        from backend.core.candidate_service import (
                            CandidateAction,
                            CandidateService,
                        )
                        candidate_svc = CandidateService(self.file_service)
                        candidate = await candidate_svc.create_candidate(
                            project_id=project_id,
                            source_path=tgt["target_rel_path"],  # 使用相对路径，不带 project_id  AI_GUARDRAIL_ALLOW
                            action=CandidateAction.CONTINUE,
                            content=generated.strip(),
                        )
                        logger.info("批量场景生成已保存为候选稿: %s -> %s", tgt["target_rel_path"], candidate.id)
                        item.status = "candidate"
                        item.candidate_id = candidate.id
                    except Exception as e:
                        logger.warning("创建候选稿失败，跳过: %s", e)
                        item.status = "skipped"
                        item.error = "目标文件已有内容，候选稿创建失败"
                        failed += 1
                        tasks.append(item)
                        continue
                else:
                    # 目标文件为空：直接写入
                    await self.file_service.write_file(tgt["target_full_path"], generated.strip())
                    logger.info("批量场景生成直接写入: %s", tgt["target_rel_path"])

                word_count = len(generated.replace(" ", ""))
                if item.status != "candidate":
                    item.status = "success"
                item.word_count = word_count
                succeeded += 1

                logger.info("场景生成完成", extra={"target": tgt["target_rel_path"], "words": word_count})

            except Exception as e:
                logger.error("场景生成失败", extra={"target": tgt["target_rel_path"], "error": str(e)[:200]})
                item.status = "error"
                item.error = str(e)[:200]
                failed += 1

            tasks.append(item)

        logger.info("批量生成完成", extra={"total": len(targets), "succeeded": succeeded, "failed": failed})

        return BatchGenerateResponse(tasks=tasks, total=len(tasks), succeeded=succeeded, failed=failed)
