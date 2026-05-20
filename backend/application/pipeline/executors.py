"""墨韵 - 管线节点执行器

每个 Executor 负责一种类型的节点执行逻辑。
PipelineRunner 通过 NodeExecutorRegistry 查找并调用对应执行器。

执行器接收已渲染的 prompt 和上下文，返回 NodeResult。
"""

import json
import logging
from abc import ABC, abstractmethod

from backend.core.file_ops import FileService
from backend.core.llm import LLMService
from backend.core.candidate_service import CandidateService
from backend.application.memory_service import MemoryService
from backend.application.pipeline.context import NodeResult, PipelineContext
from backend.schemas.candidate import CandidateAction
from backend.schemas.pipeline import PipelineStepDef

logger = logging.getLogger(__name__)


class NodeExecutor(ABC):
    """节点执行器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """执行器名称"""

    @abstractmethod
    async def execute(
        self,
        step: PipelineStepDef,
        context: PipelineContext,
        prompt_text: str,
        llm_service: LLMService,
        file_service: FileService,
        **kwargs,
    ) -> NodeResult:
        """执行节点

        Args:
            step: 管线步骤定义
            context: 管线执行上下文
            prompt_text: 已渲染的 prompt 文本
            llm_service: LLM 服务
            file_service: 文件服务
            **kwargs: 额外参数（如 stop_event, llm_extra_kwargs）

        Returns:
            NodeResult
        """


class LLMNodeExecutor(NodeExecutor):
    """LLM 调用执行器

    调用 LLM 生成文本，流式产出 delta 事件。
    """

    @property
    def name(self) -> str:
        return "llm"

    async def execute(
        self,
        step: PipelineStepDef,
        context: PipelineContext,
        prompt_text: str,
        llm_service: LLMService,
        file_service: FileService,
        **kwargs,
    ) -> NodeResult:
        stop_event = kwargs.get("stop_event")
        llm_extra_kwargs = kwargs.get("llm_extra_kwargs") or {}

        messages = [
            {"role": "system", "content": "你是一个文本处理工具。根据用户的指令处理文本，只输出处理结果本身，严禁输出任何解释、分析、问候、标题、编号或其他附加内容。"},
            {"role": "user", "content": prompt_text},
        ]

        step_output = ""
        events: list[dict] = []

        async for chunk in llm_service.complete(
            messages,
            stop_event=stop_event,
            timeout=180,
            **llm_extra_kwargs,
        ):
            step_output += chunk
            # update_story_state 的输出是结构化状态数据，不流式到编辑器
            if step.id == "update_story_state":
                continue
            events.append({"event": "generation", "data": json.dumps({
                "delta": chunk,
                "task_id": context.task_id,
            })})

        return NodeResult(output=step_output, events=events)


class FileOutputExecutor(NodeExecutor):
    """文件输出执行器

    将步骤输出写入文件，危险路径自动创建候选稿。
    """

    @property
    def name(self) -> str:
        return "file_output"

    async def execute(
        self,
        step: PipelineStepDef,
        context: PipelineContext,
        prompt_text: str,
        llm_service: LLMService,
        file_service: FileService,
        **kwargs,
    ) -> NodeResult:
        output_path = step.output
        content = context.step_outputs.get(step.id, "")
        if not output_path or not content:
            return NodeResult(output=content)

        candidate_id = await self._write_output_or_candidate(
            file_service, context.project_id, output_path, content,
            context.task_id, CandidateAction.MODIFY,
        )

        events: list[dict] = []
        if candidate_id:
            events.append({"event": "candidate_created", "data": json.dumps({
                "task_id": context.task_id,
                "candidate_id": candidate_id,
                "source_path": output_path,
                "action": CandidateAction.MODIFY.value,
            })})

        return NodeResult(output=content, candidate_id=candidate_id, events=events)

    @staticmethod
    def _is_dangerous_output(output_path: str) -> bool:
        """判断输出路径是否为危险路径"""
        output_path_lower = output_path.lower()
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

        dangerous_patterns = (
            "/sec-",
            "style-guide.md",
            "story-state.md",
            "recent-context.md",
            "outline.md",
            "meta.json",
            "ch-meta.json",
        )
        for pattern in dangerous_patterns:
            if pattern in output_path_lower:
                return True
        return False

    async def _write_output_or_candidate(
        self,
        file_service: FileService,
        project_id: str,
        output_path: str,
        content: str,
        task_id: str | None = None,
        action: CandidateAction = CandidateAction.MODIFY,
    ) -> str | None:
        """写入步骤输出，危险路径创建候选稿"""
        if self._is_dangerous_output(output_path):
            logger.warning("跳过危险路径写入: %s (需要候选稿机制)", output_path)
            try:
                candidate_service = CandidateService(file_service)
                candidate = await candidate_service.create_candidate(
                    project_id=project_id,
                    source_path=output_path,
                    action=action,
                    content=content,
                )
                logger.info("危险路径输出已保存为候选稿: %s -> %s", output_path, candidate.id)
                return candidate.id
            except Exception as e:
                logger.warning("创建候选稿失败: %s", e)
                return None
        else:
            try:
                await file_service.write_file(
                    f"{project_id}/{output_path}", content, None
                )
                logger.info("步骤输出已写入: %s", output_path)
                return None
            except Exception as e:
                logger.warning("步骤输出写入失败 %s: %s", output_path, e)
                return None


class MemoryUpdateExecutor(NodeExecutor):
    """记忆更新执行器

    更新 recent-context.md 和 story-state.md。
    """

    @property
    def name(self) -> str:
        return "memory_update"

    async def execute(
        self,
        step: PipelineStepDef,
        context: PipelineContext,
        prompt_text: str,
        llm_service: LLMService,
        file_service: FileService,
        **kwargs,
    ) -> NodeResult:
        content = context.step_outputs.get(step.id, "")
        target_file = context.target_file or ""

        if not content or not target_file:
            return NodeResult(output=content)

        memory_service = MemoryService(file_service)

        # 更新 recent-context.md
        structured_summary = memory_service.build_scene_memory_prompt_output(target_file, content)
        await memory_service.append_scene_memory(context.project_id, target_file, structured_summary)

        return NodeResult(output=content)


class CandidateOutputExecutor(NodeExecutor):
    """候选稿输出执行器

    为最终输出创建候选稿（而非直接覆盖）。
    """

    @property
    def name(self) -> str:
        return "candidate_output"

    async def execute(
        self,
        step: PipelineStepDef,
        context: PipelineContext,
        prompt_text: str,
        llm_service: LLMService,
        file_service: FileService,
        **kwargs,
    ) -> NodeResult:
        content = context.step_outputs.get(step.id, "")
        target_file = context.target_file

        if not content or not target_file:
            return NodeResult(output=content)

        action = self._infer_candidate_action(context.pipeline_name, context.output_mode)
        candidate_service = CandidateService(file_service)
        candidate = await candidate_service.create_candidate(
            project_id=context.project_id,
            source_path=target_file,
            action=action,
            content=content,
        )

        events: list[dict] = []
        events.append({"event": "candidate_created", "data": json.dumps({
            "task_id": context.task_id,
            "candidate_id": candidate.id,
            "source_path": target_file,
            "action": action.value,
        })})

        return NodeResult(output=content, candidate_id=candidate.id, events=events)

    @staticmethod
    def _infer_candidate_action(pipeline_name: str, output_mode: str) -> CandidateAction:
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
        elif "continue" in pipeline_name_lower or "续写" in pipeline_name or output_mode == "append":
            return CandidateAction.CONTINUE
        elif "modify" in pipeline_name_lower or "修改" in pipeline_name:
            return CandidateAction.MODIFY
        else:
            return CandidateAction.REWRITE
