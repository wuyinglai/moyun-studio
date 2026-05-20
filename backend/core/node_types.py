"""墨韵 - 节点类型定义

统一节点类型映射，将旧步骤类型映射为新节点类型。
参考：docs/产品架构-人机协同工作流.md
"""

from enum import Enum
from typing import Literal


class NodeType(str, Enum):
    """节点类型枚举"""
    # Prompt 节点
    PROMPT = "prompt"           # AI 执行的 Prompt 节点（原 pipeline）
    
    # Human 节点
    HUMAN_REVIEW = "human_review"       # 用户审核
    HUMAN_EDIT = "human_edit"           # 用户编辑
    HUMAN_CHOICE = "human_choice"      # 用户选择
    HUMAN_CONFIRM = "human_confirm"     # 用户确认
    
    # File 节点
    FILE_READ = "file_read"             # 读取文件
    FILE_WRITE = "file_write"           # 写入文件
    FILE_MKDIR = "file_mkdir"          # 创建目录
    FILE_COPY = "file_copy"            # 复制文件
    FILE_DELETE = "file_delete"         # 删除文件
    FILE_PATCH = "file_patch"           # 补丁文件
    FILE_SNAPSHOT = "file_snapshot"     # 快照
    FILE_CANDIDATE = "file_candidate"  # 创建候选稿
    FILE_ADOPT = "file_adopt"          # 采用候选稿
    
    # Memory 节点
    MEMORY_UPDATE = "memory_update"     # 更新记忆
    MEMORY_REVIEW = "memory_review"    # 审核记忆更新
    
    # Quality 节点
    QUALITY_REVIEW = "quality_review"  # 质量审稿
    QUALITY_JUDGE = "quality_judge"    # 质量判断
    
    # Control 节点
    CONDITION = "condition"            # 条件分支
    LOOP = "loop"                      # 循环（原 loop）
    
    # Retrieval 节点
    RETRIEVAL = "retrieval"            # 检索
    
    # Unknown
    UNKNOWN = "unknown"


class ExecutorType(str, Enum):
    """执行者类型"""
    AI = "ai"           # AI 执行
    HUMAN = "human"     # 用户执行
    SYSTEM = "system"   # 系统执行


# 旧步骤类型到新节点类型的映射
STEP_TYPE_TO_NODE_TYPE: dict[str, NodeType] = {
    # pipeline -> Prompt 节点
    "pipeline": NodeType.PROMPT,
    
    # loop -> Control 循环节点
    "loop": NodeType.LOOP,
    
    # file actions -> File 节点
    "file": NodeType.UNKNOWN,  # 需要根据 action 确定
}

# 旧 file action 到节点类型的映射
FILE_ACTION_TO_NODE_TYPE: dict[str, NodeType] = {
    "mkdir": NodeType.FILE_MKDIR,
    "copy": NodeType.FILE_COPY,
    "delete": NodeType.FILE_DELETE,
    "write": NodeType.FILE_WRITE,
    "read": NodeType.FILE_READ,
    "patch": NodeType.FILE_PATCH,
    "snapshot": NodeType.FILE_SNAPSHOT,
    "create_candidate": NodeType.FILE_CANDIDATE,
    "adopt_candidate": NodeType.FILE_ADOPT,
}


def get_node_type(step_type: str, action: str | None = None) -> NodeType:
    """根据步骤类型和 action 获取节点类型"""
    if step_type == "file" and action:
        return FILE_ACTION_TO_NODE_TYPE.get(action, NodeType.UNKNOWN)
    return STEP_TYPE_TO_NODE_TYPE.get(step_type, NodeType.UNKNOWN)


def get_executor(node_type: NodeType) -> ExecutorType:
    """根据节点类型获取执行者"""
    if node_type in (
        NodeType.HUMAN_REVIEW,
        NodeType.HUMAN_EDIT,
        NodeType.HUMAN_CHOICE,
        NodeType.HUMAN_CONFIRM,
    ):
        return ExecutorType.HUMAN
    
    if node_type in (
        NodeType.MEMORY_REVIEW,
        NodeType.QUALITY_JUDGE,
    ):
        return ExecutorType.HUMAN  # 这些是 AI+Human 协作
    
    if node_type in (
        NodeType.FILE_READ,
        NodeType.FILE_WRITE,
        NodeType.FILE_MKDIR,
        NodeType.FILE_COPY,
        NodeType.FILE_DELETE,
        NodeType.FILE_PATCH,
        NodeType.FILE_SNAPSHOT,
        NodeType.FILE_CANDIDATE,
        NodeType.FILE_ADOPT,
    ):
        return ExecutorType.SYSTEM
    
    if node_type in (
        NodeType.CONDITION,
        NodeType.LOOP,
        NodeType.RETRIEVAL,
    ):
        return ExecutorType.SYSTEM
    
    # 默认：AI 执行
    return ExecutorType.AI


def node_type_label(node_type: NodeType) -> str:
    """获取节点类型的中文标签"""
    labels = {
        NodeType.PROMPT: "AI 生成",
        NodeType.HUMAN_REVIEW: "用户审核",
        NodeType.HUMAN_EDIT: "用户编辑",
        NodeType.HUMAN_CHOICE: "用户选择",
        NodeType.HUMAN_CONFIRM: "用户确认",
        NodeType.FILE_READ: "读取文件",
        NodeType.FILE_WRITE: "写入文件",
        NodeType.FILE_MKDIR: "创建目录",
        NodeType.FILE_COPY: "复制文件",
        NodeType.FILE_DELETE: "删除文件",
        NodeType.FILE_PATCH: "补丁文件",
        NodeType.FILE_SNAPSHOT: "快照",
        NodeType.FILE_CANDIDATE: "候选稿",
        NodeType.FILE_ADOPT: "采用候选",
        NodeType.MEMORY_UPDATE: "更新记忆",
        NodeType.MEMORY_REVIEW: "审核记忆",
        NodeType.QUALITY_REVIEW: "质量审稿",
        NodeType.QUALITY_JUDGE: "质量判断",
        NodeType.CONDITION: "条件分支",
        NodeType.LOOP: "循环",
        NodeType.RETRIEVAL: "检索",
        NodeType.UNKNOWN: "未知",
    }
    return labels.get(node_type, "未知")


def executor_label(executor: ExecutorType) -> str:
    """获取执行者的中文标签"""
    labels = {
        ExecutorType.AI: "AI",
        ExecutorType.HUMAN: "用户",
        ExecutorType.SYSTEM: "系统",
    }
    return labels.get(executor, "未知")


# Human 节点可用动作
HUMAN_ACTIONS = ["approve", "edit_and_approve", "regenerate", "stop"]


def build_node_info(step_type: str, action: str | None = None, label: str = "") -> dict:
    """构建节点信息字典"""
    node_type = get_node_type(step_type, action)
    executor = get_executor(node_type)
    
    info = {
        "node_type": node_type.value,
        "node_label": node_type_label(node_type),
        "executor": executor.value,
        "executor_label": executor_label(executor),
    }
    
    # Human 节点添加等待动作
    if executor == ExecutorType.HUMAN:
        info["actions"] = HUMAN_ACTIONS
        info["waiting_reason"] = f"请{node_type_label(node_type)}"
    
    return info
