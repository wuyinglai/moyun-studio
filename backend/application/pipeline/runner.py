"""墨韵 - 管线 Runner 模块

从 core/pipeline.py 导入 PipelineRunner，并为其附加 NodeExecutorRegistry。
PipelineRunner 仍然保持原有行为，但内部执行步骤时通过 registry 查找 executor。
"""

from backend.application.pipeline.registry import NodeExecutorRegistry

# 全局默认注册表实例
default_registry = NodeExecutorRegistry()
