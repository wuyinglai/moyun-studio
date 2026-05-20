"""墨韵 - 文件相关 Schemas"""

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from backend.core.exceptions import ValidationError


class FileReadResponse(BaseModel):
    path: str
    content: str
    frontmatter: dict | None = None
    mtime: float | None = None  # 文件修改时间（用于并发控制）


class FileWriteRequest(BaseModel):
    path: str = Field(..., description="相对于项目根目录的文件路径")
    content: str = Field(..., description="文件内容")
    frontmatter: dict | None = Field(default=None, description="Frontmatter 元数据")
    expected_mtime: float | None = Field(default=None, description="期望的文件修改时间（用于并发控制）")
    expected_hash: str | None = Field(default=None, description="期望的文件内容哈希（用于并发控制）")

    # 最大写入大小限制（5MB）
    MAX_CONTENT_SIZE: ClassVar[int] = 5 * 1024 * 1024

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        size = len(v.encode("utf-8"))
        if size > cls.MAX_CONTENT_SIZE:
            raise ValidationError(
                f"文件内容过大: {size / (1024*1024):.1f}MB > {cls.MAX_CONTENT_SIZE / (1024*1024):.0f}MB"
            )
        return v


class TreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"
    children: list["TreeNode"] = Field(default_factory=list)
    size: int | None = None


class FileTreeResponse(BaseModel):
    project_id: str
    tree: list[TreeNode]
