"""墨韵 - 版本对比 API

端点：
  POST /api/compare  对比两个文本的差异
"""

import difflib
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["版本对比"], prefix="")


# ─── Schema ──────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    """对比请求"""
    old_text: str = Field(..., description="旧版本内容")
    new_text: str = Field(..., description="新版本内容")
    fromfile: str = Field(default="版本1", description="旧版本文件名")
    tofile: str = Field(default="版本2", description="新版本文件名")


class CompareResponse(BaseModel):
    """对比响应"""
    diff: str = Field(..., description="统一差异格式（unified diff）")
    has_diff: bool = Field(..., description="是否有差异")
    added_lines: int = Field(default=0, ge=0, description="新增行数")
    removed_lines: int = Field(default=0, ge=0, description="删除行数")


# ─── 工具函数 ────────────────────────────────────────────────────────

def _generate_unified_diff(
    old_text: str,
    new_text: str,
    fromfile: str = "版本1",
    tofile: str = "版本2"
) -> tuple[str, int, int]:
    """生成统一差异格式

    Args:
        old_text: 旧版本内容
        new_text: 新版本内容
        fromfile: 旧版本文件名
        tofile: 新版本文件名

    Returns:
        (diff_text, added_lines, removed_lines)
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=fromfile,
        tofile=tofile,
        lineterm=""
    )

    diff_text = "".join(diff)

    # 统计变化行数
    added_lines = 0
    removed_lines = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines += 1

    return diff_text, added_lines, removed_lines


def _generate_side_by_side_diff(
    old_text: str,
    new_text: str
) -> list[dict[str, str]]:
    """生成并排对比格式

    Args:
        old_text: 旧版本内容
        new_text: 新版本内容

    Returns:
        行对比列表，每行包含 old_line, new_line, change_type
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                result.append({
                    "old_line": old_lines[i],
                    "new_line": new_lines[i] if i < len(new_lines) else "",
                    "change_type": "unchanged",
                    "line_num": i + 1
                })
        elif tag == "delete":
            for i in range(i1, i2):
                result.append({
                    "old_line": old_lines[i],
                    "new_line": "",
                    "change_type": "removed",
                    "line_num": i + 1
                })
        elif tag == "insert":
            for j in range(j1, j2):
                # 尝试找到对应的旧行位置
                old_line = ""
                if i1 < len(old_lines):
                    old_line = old_lines[i1]
                result.append({
                    "old_line": old_line,
                    "new_line": new_lines[j],
                    "change_type": "added",
                    "line_num": j + 1
                })
        elif tag == "replace":
            for i in range(i1, i2):
                j = j1 + (i - i1) if j1 + (i - i1) < j2 else -1
                new_line = new_lines[j] if j >= 0 else ""
                result.append({
                    "old_line": old_lines[i],
                    "new_line": new_line,
                    "change_type": "modified",
                    "line_num": i + 1
                })

    return result


# ─── 路由 ────────────────────────────────────────────────────────────

@router.post("/compare", response_model=ApiResponse[CompareResponse])
async def compare_texts(
    req: CompareRequest,
) -> ApiResponse[CompareResponse]:
    """对比两个文本的差异

    生成统一差异格式（unified diff），用于版本对比。

    Args:
        req: 对比请求

    Returns:
        差异结果
    """
    diff_text, added_lines, removed_lines = _generate_unified_diff(
        req.old_text,
        req.new_text,
        req.fromfile,
        req.tofile
    )

    has_diff = bool(diff_text.strip())

    logger.debug(
        "版本对比: 新增行=%d, 删除行=%d, 有差异=%s",
        added_lines, removed_lines, has_diff
    )

    return ApiResponse.ok(CompareResponse(
        diff=diff_text,
        has_diff=has_diff,
        added_lines=added_lines,
        removed_lines=removed_lines
    ))


@router.post("/compare/side-by-side", response_model=ApiResponse[dict])
async def compare_texts_side_by_side(
    req: CompareRequest,
) -> ApiResponse[dict]:
    """对比两个文本的差异（并排格式）

    生成并排对比格式，便于前端渲染。

    Args:
        req: 对比请求

    Returns:
        并排对比结果
    """
    side_by_side = _generate_side_by_side_diff(req.old_text, req.new_text)

    # 统计
    stats = {
        "unchanged": sum(1 for l in side_by_side if l["change_type"] == "unchanged"),
        "added": sum(1 for l in side_by_side if l["change_type"] == "added"),
        "removed": sum(1 for l in side_by_side if l["change_type"] == "removed"),
        "modified": sum(1 for l in side_by_side if l["change_type"] == "modified"),
    }

    logger.debug(
        "版本对比(并排): 不变=%d, 新增=%d, 删除=%d, 修改=%d",
        stats["unchanged"], stats["added"], stats["removed"], stats["modified"]
    )

    return ApiResponse.ok({
        "lines": side_by_side,
        "stats": stats,
        "has_diff": stats["added"] > 0 or stats["removed"] > 0 or stats["modified"] > 0
    })


@router.post("/compare/chapters", response_model=ApiResponse[CompareResponse])
async def compare_chapters(
    project_id: str,
    chapter_path: str,
    version_a: str,
    version_b: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[CompareResponse]:
    """对比章节的两个版本

    从章节的修改日志中获取两个版本进行对比。

    Args:
        project_id: 项目ID
        chapter_path: 章节路径
        version_a: 版本A的日志ID
        version_b: 版本B的日志ID

    Returns:
        对比结果
    """
    # 简化实现：需要从revision-log中读取具体版本内容
    # 完整实现需要调用 revision_log API 获取历史内容

    logger.info(
        "章节版本对比",
        extra={
            "project_id": project_id,
            "chapter_path": chapter_path,
            "version_a": version_a,
            "version_b": version_b
        }
    )

    return ApiResponse.ok(CompareResponse(
        diff="（需要实现从修改日志读取历史版本）",
        has_diff=True,
        added_lines=0,
        removed_lines=0
    ))
