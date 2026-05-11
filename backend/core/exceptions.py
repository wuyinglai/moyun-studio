"""墨韵 - 统一异常体系

所有业务异常在此定义，形成统一的异常层次结构。
"""

from typing import Any


class MoyunException(Exception):
    """墨韵应用异常基类"""

    def __init__(
        self,
        message: str,
        code: str,
        details: Any | None = None
    ):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class ProjectError(MoyunException):
    """项目相关错误"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "PROJECT_ERROR", details)


class ProjectNotFoundError(ProjectError):
    """项目不存在"""
    def __init__(self, project_id: str):
        super().__init__(
            f"项目不存在: {project_id}",
            {"project_id": project_id}
        )


class ProjectAlreadyExistsError(ProjectError):
    """项目已存在"""
    def __init__(self, project_name: str):
        super().__init__(
            f"项目已存在: {project_name}",
            {"project_name": project_name}
        )


class FileError(MoyunException):
    """文件相关错误"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "FILE_ERROR", details)


class FileNotFoundError(FileError):
    """文件不存在"""
    def __init__(self, file_path: str):
        super().__init__(
            f"文件不存在: {file_path}",
            {"file_path": file_path}
        )


class DirectoryNotFoundError(FileError):
    """目录不存在"""
    def __init__(self, dir_path: str):
        super().__init__(
            f"目录不存在: {dir_path}",
            {"dir_path": dir_path}
        )


class TemplateError(MoyunException):
    """模板相关错误"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "TEMPLATE_ERROR", details)


class TemplateNotFoundError(TemplateError):
    """模板不存在"""
    def __init__(self, category: str, template_type: str):
        super().__init__(
            f"模板不存在: {category}/{template_type}",
            {"category": category, "template_type": template_type}
        )


class TemplateRenderError(TemplateError):
    """模板渲染错误"""
    def __init__(self, template_path: str, reason: str):
        super().__init__(
            f"模板渲染失败: {template_path}",
            {"template_path": template_path, "reason": reason}
        )


class LLMError(MoyunException):
    """LLM相关错误"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "LLM_ERROR", details)


class LLMConfigError(LLMError):
    """LLM配置错误"""
    def __init__(self, reason: str):
        super().__init__(
            f"LLM配置错误: {reason}",
            {"reason": reason}
        )


class LLMAPIError(LLMError):
    """LLM API调用错误"""
    def __init__(self, model: str, reason: str, status_code: int | None = None):
        super().__init__(
            f"LLM API调用失败: {model}",
            {"model": model, "reason": reason, "status_code": status_code}
        )


class TaskError(MoyunException):
    """任务相关错误"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "TASK_ERROR", details)


class TaskNotFoundError(TaskError):
    """任务不存在"""
    def __init__(self, task_id: str):
        super().__init__(
            f"任务不存在: {task_id}",
            {"task_id": task_id}
        )


class TaskCancelledError(TaskError):
    """任务已取消"""
    def __init__(self, task_id: str):
        super().__init__(
            f"任务已取消: {task_id}",
            {"task_id": task_id}
        )


class ValidationError(MoyunException):
    """验证错误"""
    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            message,
            "VALIDATION_ERROR",
            {"field": field} if field else None
        )


class ConfigError(MoyunException):
    """配置错误"""
    def __init__(self, message: str, key: str | None = None):
        super().__init__(
            message,
            "CONFIG_ERROR",
            {"key": key} if key else None
        )


class ContextLengthError(MoyunException):
    """上下文超长"""
    def __init__(self, token_count: int, max_tokens: int):
        super().__init__(
            f"上下文超出限制: {token_count} > {max_tokens}",
            "CONTEXT_LENGTH_ERROR",
            {"token_count": token_count, "max_tokens": max_tokens}
        )
