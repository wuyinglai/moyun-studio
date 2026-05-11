"""墨韵 - 通用响应 Schema

所有 API 均返回此统一结构：
{
  "success": true/false,
  "data": {...} | null,
  "message": "...",
  "error": null | {"code": "...", "details": ...}
}
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    message: str = ""
    error: ErrorDetail | None = None

    @classmethod
    def ok(cls, data: T | None = None, message: str = "操作成功") -> "ApiResponse[T]":
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(
        cls,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Any = None,
    ) -> "ApiResponse[None]":
        return cls(
            success=False,
            data=None,
            message=message,
            error=ErrorDetail(code=code, message=message, details=details),
        )
