"""墨韵 - 文件相关 Schemas"""

from pydantic import BaseModel, Field


class FileReadResponse(BaseModel):
    path: str
    content: str
    frontmatter: dict | None = None


class FileWriteRequest(BaseModel):
    path: str = Field(..., description="相对于项目根目录的文件路径")
    content: str = Field(..., description="文件内容")
    frontmatter: dict | None = Field(default=None, description="Frontmatter 元数据")


class TreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"
    children: list["TreeNode"] = []
    size: int | None = None


class FileTreeResponse(BaseModel):
    project_id: str
    tree: list[TreeNode]
