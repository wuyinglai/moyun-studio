"""墨韵 - 节点执行器注册表

PipelineRunner 通过注册表查找对应步骤类型的执行器。
"""

import logging

from backend.application.pipeline.executors import (
    CandidateOutputExecutor,
    FileOutputExecutor,
    LLMNodeExecutor,
    MemoryUpdateExecutor,
    NodeExecutor,
)
from backend.schemas.pipeline import PipelineStepDef

logger = logging.getLogger(__name__)


class NodeExecutorRegistry:
    """节点执行器注册表"""

    def __init__(self):
        self._executors: dict[str, NodeExecutor] = {}
        # 注册内置执行器
        self.register(LLMNodeExecutor())
        self.register(FileOutputExecutor())
        self.register(MemoryUpdateExecutor())
        self.register(CandidateOutputExecutor())

    def register(self, executor: NodeExecutor) -> None:
        """注册执行器"""
        self._executors[executor.name] = executor
        logger.debug("注册执行器: %s", executor.name)

    def get_executor(self, step: PipelineStepDef) -> NodeExecutor:
        """根据步骤定义获取执行器

        规则：
        - step.id == "update_story_state" → MemoryUpdateExecutor
        - step.output 存在且步骤需要文件输出 → FileOutputExecutor
        - 默认 → LLMNodeExecutor
        """
        # 记忆更新步骤
        if step.id == "update_story_state":
            return self._executors.get("memory_update", self._executors["llm"])

        # 有 output 字段的步骤（文件输出）
        if step.output:
            return self._executors.get("file_output", self._executors["llm"])

        # 默认使用 LLM 执行器
        return self._executors["llm"]

    def get_executor_by_name(self, name: str) -> NodeExecutor | None:
        """按名称获取执行器"""
        return self._executors.get(name)

    def list_executors(self) -> list[str]:
        """列出所有已注册的执行器名称"""
        return list(self._executors.keys())
