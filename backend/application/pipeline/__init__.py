"""墨韵 - 管线模块

提供管线执行器的模块化架构。
PipelineRunner 仍然保持原有行为，但内部执行步骤时通过 NodeExecutorRegistry 找 executor。
"""

from backend.application.pipeline.context import NodeResult, PipelineContext
from backend.application.pipeline.executors import (
    CandidateOutputExecutor,
    FileOutputExecutor,
    LLMNodeExecutor,
    MemoryUpdateExecutor,
    NodeExecutor,
)
from backend.application.pipeline.registry import NodeExecutorRegistry

__all__ = [
    "NodeResult",
    "PipelineContext",
    "NodeExecutor",
    "LLMNodeExecutor",
    "FileOutputExecutor",
    "MemoryUpdateExecutor",
    "CandidateOutputExecutor",
    "NodeExecutorRegistry",
]
