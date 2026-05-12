"""异常体系单元测试 — 覆盖所有 20+ 异常类

测试要点：
1. 每个异常类的初始化（message, code, details）
2. to_dict() 序列化
3. 错误码与 HTTP 状态码映射
4. 继承关系
"""

import pytest

from backend.core.exceptions import (
    MoyunException,
    ProjectError,
    ProjectNotFoundError,
    ProjectAlreadyExistsError,
    MoyunFileError,
    FileNotFoundError as MoyunFileNotFoundError,
    DirectoryNotFoundError,
    TemplateError,
    TemplateNotFoundError,
    TemplateRenderError,
    LLMError,
    LLMConfigError,
    LLMAPIError,
    TaskError,
    TaskNotFoundError,
    TaskCancelledError,
    ValidationError,
    ConfigError,
    ContextLengthError,
    ResourceNotFoundError,
    RateLimitError,
)

from backend.main import _moyun_to_http_status


# ─── 基类测试 ────────────────────────────────────────────

class TestMoyunException:
    """MoyunException 基类测试"""

    def test_init_basic(self):
        exc = MoyunException("错误消息", "TEST_CODE")
        assert exc.message == "错误消息"
        assert exc.code == "TEST_CODE"
        assert exc.details is None

    def test_init_with_details(self):
        exc = MoyunException("错误消息", "TEST_CODE", {"key": "value"})
        assert exc.details == {"key": "value"}

    def test_to_dict(self):
        exc = MoyunException("测试错误", "TEST_CODE", {"field": "name"})
        d = exc.to_dict()
        assert d == {
            "code": "TEST_CODE",
            "message": "测试错误",
            "details": {"field": "name"},
        }

    def test_to_dict_no_details(self):
        exc = MoyunException("测试", "CODE")
        d = exc.to_dict()
        assert d["details"] is None

    def test_is_exception(self):
        exc = MoyunException("test", "CODE")
        assert isinstance(exc, Exception)


class TestMoyunExceptionInheritance:
    """异常继承关系测试"""

    def test_project_error_is_moyun(self):
        assert issubclass(ProjectError, MoyunException)

    def test_file_error_is_moyun(self):
        assert issubclass(MoyunFileError, MoyunException)

    def test_template_error_is_moyun(self):
        assert issubclass(TemplateError, MoyunException)

    def test_llm_error_is_moyun(self):
        assert issubclass(LLMError, MoyunException)

    def test_task_error_is_moyun(self):
        assert issubclass(TaskError, MoyunException)

    def test_validation_error_is_moyun(self):
        assert issubclass(ValidationError, MoyunException)

    def test_config_error_is_moyun(self):
        assert issubclass(ConfigError, MoyunException)

    def test_context_length_error_is_moyun(self):
        assert issubclass(ContextLengthError, MoyunException)

    def test_resource_not_found_is_moyun(self):
        assert issubclass(ResourceNotFoundError, MoyunException)

    def test_rate_limit_is_moyun(self):
        assert issubclass(RateLimitError, MoyunException)


# ─── 项目异常 ────────────────────────────────────────────

class TestProjectError:
    """ProjectError 测试"""

    def test_default_code(self):
        exc = ProjectError("项目错误")
        assert exc.code == "PROJECT_ERROR"

    def test_with_details(self):
        exc = ProjectError("项目错误", {"name": "test"})
        assert exc.details == {"name": "test"}


class TestProjectNotFoundError:
    """ProjectNotFoundError 测试"""

    def test_message_contains_id(self):
        exc = ProjectNotFoundError("proj-123")
        assert "proj-123" in exc.message

    def test_code(self):
        exc = ProjectNotFoundError("proj-123")
        assert exc.code == "PROJECT_NOT_FOUND"

    def test_details_contain_id(self):
        exc = ProjectNotFoundError("proj-123")
        assert exc.details == {"project_id": "proj-123"}


class TestProjectAlreadyExistsError:
    """ProjectAlreadyExistsError 测试"""

    def test_message(self):
        exc = ProjectAlreadyExistsError("我的项目")
        assert "我的项目" in exc.message

    def test_details(self):
        exc = ProjectAlreadyExistsError("我的项目")
        assert exc.details == {"project_name": "我的项目"}


# ─── 文件异常 ────────────────────────────────────────────

class TestMoyunFileError:
    """MoyunFileError 测试"""

    def test_default_code(self):
        exc = MoyunFileError("文件错误")
        assert exc.code == "FILE_ERROR"


class TestMoyunFileNotFoundError:
    """FileNotFoundError 测试"""

    def test_message(self):
        exc = MoyunFileNotFoundError("chapters/test.md")
        assert "chapters/test.md" in exc.message

    def test_code(self):
        exc = MoyunFileNotFoundError("chapters/test.md")
        assert exc.code == "FILE_NOT_FOUND"

    def test_details(self):
        exc = MoyunFileNotFoundError("chapters/test.md")
        assert exc.details == {"file_path": "chapters/test.md"}


class TestDirectoryNotFoundError:
    """DirectoryNotFoundError 测试"""

    def test_message(self):
        exc = DirectoryNotFoundError("backup")
        assert "backup" in exc.message

    def test_code(self):
        exc = DirectoryNotFoundError("backup")
        assert exc.code == "FILE_NOT_FOUND"


# ─── 模板异常 ────────────────────────────────────────────

class TestTemplateError:
    """TemplateError 测试"""

    def test_default_code(self):
        exc = TemplateError("模板错误")
        assert exc.code == "TEMPLATE_ERROR"


class TestTemplateNotFoundError:
    """TemplateNotFoundError 测试"""

    def test_with_category_and_type(self):
        exc = TemplateNotFoundError(category="generate", template_type="chapter")
        assert "generate/chapter" in exc.message
        assert exc.code == "TEMPLATE_NOT_FOUND"
        assert exc.details["category"] == "generate"
        assert exc.details["template_type"] == "chapter"

    def test_with_template_path(self):
        exc = TemplateNotFoundError(template="custom/path/template.md")
        assert "custom/path/template.md" in exc.message

    def test_empty_fields(self):
        exc = TemplateNotFoundError()
        assert exc.message is not None
        assert exc.code == "TEMPLATE_NOT_FOUND"


class TestTemplateRenderError:
    """TemplateRenderError 测试"""

    def test_message_and_reason(self):
        exc = TemplateRenderError("generate/chapter", "变量未定义")
        assert "generate/chapter" in exc.message
        assert exc.details["reason"] == "变量未定义"


# ─── LLM 异常 ────────────────────────────────────────────

class TestLLMError:
    """LLMError 测试"""

    def test_default_code(self):
        exc = LLMError("LLM错误")
        assert exc.code == "LLM_ERROR"


class TestLLMConfigError:
    """LLMConfigError 测试"""

    def test_message(self):
        exc = LLMConfigError("API Key 未设置")
        assert "API Key 未设置" in exc.message
        assert exc.details["reason"] == "API Key 未设置"


class TestLLMAPIError:
    """LLMAPIError 测试"""

    def test_message(self):
        exc = LLMAPIError("gpt-4", "连接超时")
        assert "gpt-4" in exc.message
        assert exc.details["model"] == "gpt-4"
        assert exc.details["reason"] == "连接超时"

    def test_with_status_code(self):
        exc = LLMAPIError("gpt-4", "Rate limit", status_code=429)
        assert exc.details["status_code"] == 429

    def test_without_status_code(self):
        exc = LLMAPIError("gpt-4", "unknown error")
        assert exc.details["status_code"] is None


# ─── 任务异常 ────────────────────────────────────────────

class TestTaskError:
    """TaskError 测试"""

    def test_default_code(self):
        exc = TaskError("任务错误")
        assert exc.code == "TASK_ERROR"


class TestTaskNotFoundError:
    """TaskNotFoundError 测试"""

    def test_message(self):
        exc = TaskNotFoundError("task-456")
        assert "task-456" in exc.message
        assert exc.code == "TASK_NOT_FOUND"
        assert exc.details == {"task_id": "task-456"}


class TestTaskCancelledError:
    """TaskCancelledError 测试"""

    def test_message(self):
        exc = TaskCancelledError("task-789")
        assert "task-789" in exc.message
        assert exc.details == {"task_id": "task-789"}


# ─── 验证异常 ────────────────────────────────────────────

class TestValidationError:
    """ValidationError 测试"""

    def test_with_field(self):
        exc = ValidationError("名称不能为空", field="name")
        assert exc.code == "VALIDATION_ERROR"
        assert exc.details == {"field": "name"}

    def test_without_field(self):
        exc = ValidationError("输入无效")
        assert exc.code == "VALIDATION_ERROR"
        assert exc.details is None


# ─── 配置异常 ────────────────────────────────────────────

class TestConfigError:
    """ConfigError 测试"""

    def test_with_key(self):
        exc = ConfigError("配置项无效", key="llm_provider")
        assert exc.code == "CONFIG_ERROR"
        assert exc.details == {"key": "llm_provider"}

    def test_without_key(self):
        exc = ConfigError("配置错误")
        assert exc.code == "CONFIG_ERROR"
        assert exc.details is None


# ─── 上下文长度异常 ──────────────────────────────────────

class TestContextLengthError:
    """ContextLengthError 测试"""

    def test_message(self):
        exc = ContextLengthError(200000, 128000)
        assert exc.code == "CONTEXT_LENGTH_ERROR"
        assert exc.details["token_count"] == 200000
        assert exc.details["max_tokens"] == 128000


# ─── 通用资源不存在 ──────────────────────────────────────

class TestResourceNotFoundError:
    """ResourceNotFoundError 测试"""

    def test_with_resource_id(self):
        exc = ResourceNotFoundError(resource="快照", resource_id="snap-001")
        assert exc.code == "RESOURCE_NOT_FOUND"
        assert exc.details["resource_id"] == "snap-001"

    def test_with_identifier(self):
        exc = ResourceNotFoundError(resource="file", identifier="chapters/test.md")
        assert "chapters/test.md" in exc.message

    def test_empty_fields(self):
        exc = ResourceNotFoundError()
        assert exc.code == "RESOURCE_NOT_FOUND"


# ─── 速率限制 ────────────────────────────────────────────

class TestRateLimitError:
    """RateLimitError 测试"""

    def test_message(self):
        exc = RateLimitError(30)
        assert exc.code == "RATE_LIMIT"
        assert exc.details["retry_after"] == 30
        assert "30" in exc.message


# ─── HTTP 状态码映射 ─────────────────────────────────────

class TestExceptionToHttpStatus:
    """异常码到 HTTP 状态码的映射测试"""

    @pytest.mark.parametrize("code,expected_status", [
        ("PROJECT_ERROR", 400),
        ("PROJECT_NOT_FOUND", 404),
        ("FILE_ERROR", 400),
        ("FILE_NOT_FOUND", 404),
        ("RESOURCE_NOT_FOUND", 404),
        ("FILE_ALREADY_EXISTS", 409),
        ("TEMPLATE_ERROR", 400),
        ("TEMPLATE_NOT_FOUND", 404),
        ("INVALID_TEMPLATE", 422),
        ("INVALID_VARIABLE", 422),
        ("VALIDATION_ERROR", 422),
        ("LLM_ERROR", 503),
        ("LLM_TIMEOUT", 504),
        ("TASK_ERROR", 400),
        ("TASK_NOT_FOUND", 404),
        ("RATE_LIMIT", 429),
        ("CONFIG_ERROR", 400),
        ("CONTEXT_LENGTH_ERROR", 413),
    ])
    def test_known_codes(self, code, expected_status):
        assert _moyun_to_http_status(code) == expected_status

    def test_unknown_code_returns_500(self):
        assert _moyun_to_http_status("UNKNOWN_CODE_XYZ") == 500
