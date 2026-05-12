"""墨韵 - 统一异常体系

所有业务异常在此定义，形成统一的异常层次结构。
异常码与 main.py 中的 _moyun_to_http_status() 映射表对齐。
"""

from typing import Any


class MoyunException(Exception):
    """墨韵应用异常基类"""

    def __init__(
        self,
        message: str,
        code: str,
        details: Any | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ProjectError(MoyunException):
    """项目相关错误（默认 code: PROJECT_ERROR）"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "PROJECT_ERROR", details)


class ProjectNotFoundError(ProjectError):
    """项目不存在（code: PROJECT_NOT_FOUND，对应 HTTP 404）"""

    def __init__(self, project_id: str):
        super().__init__(
            f"项目不存在: {project_id}",
            {"project_id": project_id},
        )
        self.code = "PROJECT_NOT_FOUND"


class ProjectAlreadyExistsError(ProjectError):
    """项目已存在"""

    def __init__(self, project_name: str):
        super().__init__(
            f"项目已存在: {project_name}",
            {"project_name": project_name},
        )


class MoyunFileError(MoyunException):
    """文件相关错误（默认 code: FILE_ERROR）"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "FILE_ERROR", details)


class FileNotFoundError(MoyunFileError):
    """文件不存在（code: FILE_NOT_FOUND，对应 HTTP 404）

    注意：命名为 FileNotFoundError 以保持向后兼容，
    但这与 Python 内置异常同名，使用时需注意导入来源。
    """

    def __init__(self, file_path: str):
        super().__init__(
            f"文件不存在: {file_path}",
            {"file_path": file_path},
        )
        self.code = "FILE_NOT_FOUND"


class DirectoryNotFoundError(MoyunFileError):
    """目录不存在（code: FILE_NOT_FOUND，对应 HTTP 404）"""

    def __init__(self, dir_path: str):
        super().__init__(
            f"目录不存在: {dir_path}",
            {"dir_path": dir_path},
        )
        self.code = "FILE_NOT_FOUND"


class TemplateError(MoyunException):
    """模板相关错误（默认 code: TEMPLATE_ERROR）"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "TEMPLATE_ERROR", details)


class TemplateNotFoundError(TemplateError):
    """模板不存在（code: TEMPLATE_NOT_FOUND，对应 HTTP 404）"""

    def __init__(self, template: str = "", category: str = "", template_type: str = ""):
        template_path = template or f"{category}/{template_type}"
        super().__init__(
            f"模板不存在: {template_path}",
            {"category": category, "template_type": template_type, "template": template_path},
        )
        self.code = "TEMPLATE_NOT_FOUND"


class TemplateRenderError(TemplateError):
    """模板渲染错误"""

    def __init__(self, template_path: str, reason: str):
        super().__init__(
            f"模板渲染失败: {template_path}",
            {"template_path": template_path, "reason": reason},
        )


class LLMError(MoyunException):
    """LLM相关错误（默认 code: LLM_ERROR）"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "LLM_ERROR", details)


class LLMConfigError(LLMError):
    """LLM配置错误"""

    def __init__(self, reason: str):
        super().__init__(
            f"LLM配置错误: {reason}",
            {"reason": reason},
        )


class LLMAPIError(LLMError):
    """LLM API调用错误"""

    def __init__(self, model: str, reason: str, status_code: int | None = None):
        super().__init__(
            f"LLM API调用失败: {model}",
            {"model": model, "reason": reason, "status_code": status_code},
        )


class TaskError(MoyunException):
    """任务相关错误（默认 code: TASK_ERROR）"""

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message, "TASK_ERROR", details)


class TaskNotFoundError(TaskError):
    """任务不存在（code: TASK_NOT_FOUND，对应 HTTP 404）"""

    def __init__(self, task_id: str):
        super().__init__(
            f"任务不存在: {task_id}",
            {"task_id": task_id},
        )
        self.code = "TASK_NOT_FOUND"


class TaskCancelledError(TaskError):
    """任务已取消"""

    def __init__(self, task_id: str):
        super().__init__(
            f"任务已取消: {task_id}",
            {"task_id": task_id},
        )


class ValidationError(MoyunException):
    """验证错误（code: VALIDATION_ERROR，对应 HTTP 422）"""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            message,
            "VALIDATION_ERROR",
            {"field": field} if field else None,
        )


class ConfigError(MoyunException):
    """配置错误（code: CONFIG_ERROR，对应 HTTP 400）"""

    def __init__(self, message: str, key: str | None = None):
        super().__init__(
            message,
            "CONFIG_ERROR",
            {"key": key} if key else None,
        )


class ContextLengthError(MoyunException):
    """上下文超长（code: CONTEXT_LENGTH_ERROR，对应 HTTP 413）"""

    def __init__(self, token_count: int, max_tokens: int):
        super().__init__(
            f"上下文超出限制: {token_count} > {max_tokens}",
            "CONTEXT_LENGTH_ERROR",
            {"token_count": token_count, "max_tokens": max_tokens},
        )


class ResourceNotFoundError(MoyunException):
    """通用资源不存在错误（code: RESOURCE_NOT_FOUND，对应 HTTP 404）"""

    def __init__(self, resource: str = "", identifier: str = "", resource_id: str = ""):
        res_id = resource_id or identifier or resource
        super().__init__(
            f"资源不存在: {res_id}",
            "RESOURCE_NOT_FOUND",
            {"resource": resource, "identifier": identifier, "resource_id": resource_id},
        )


class RateLimitError(MoyunException):
    """速率限制错误（code: RATE_LIMIT，对应 HTTP 429）"""

    def __init__(self, retry_after: int):
        super().__init__(
            f"请求过于频繁，请{retry_after}秒后再试",
            "RATE_LIMIT",
            {"retry_after": retry_after},
        )
