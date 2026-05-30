"""墨韵 - 文风指南 API

端点：
  GET  /api/style-guide/{project_id}  获取文风指南内容
  POST /api/style-guide/{project_id}  保存文风指南内容
"""

import asyncio
from datetime import datetime
import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["文风指南"], prefix="/style-guide")


# ─── Schema ──────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    """AI 生成文风指南请求"""
    genre: str = ""
    theme: str = ""
    tone: str = ""
    writing_style: str = ""




class StyleGuideContent(BaseModel):
    """文风指南内容"""
    content: str = Field(..., description="文风指南Markdown内容")
    last_modified: str | None = Field(None, description="最后修改时间")


class SaveStyleGuideRequest(BaseModel):
    """保存文风指南请求"""
    content: str = Field(..., description="文风指南Markdown内容")


# ─── AI 生成文风指南 ────────────────────────────────────────────────


_GENERATE_PROMPT = """你是一名资深文学编辑。请根据以下项目信息，生成一份文风指南。

## 项目信息
- 题材：{genre}
- 核心主题：{theme}
- 作品基调：{tone}
- 写作风格：{writing_style}

## 要求
请按以下结构输出完整的文风指南（Markdown 格式）：

### 一、文风定位
- 整体风格：根据题材和基调确定
- 句子节奏：长短句搭配方式
- 描写密度：场景/心理/对话的比例
- 语言特点：用词偏好、修辞风格

### 二、写作风格要点
- 叙述方式（如第三人称有限视角）
- 对话风格（如自然口语化）
- 心理描写（如适度、点到即止）
- 场景描写（如注重氛围烘托）

### 三、写作禁忌
- 针对本题材应避免的表达方式

### 四、题材特点
- 本题材特有的表达习惯和术语规范

直接输出文风指南内容，不要添加说明。
"""


@router.post("/{project_id}/generate", response_model=ApiResponse[StyleGuideContent])
async def generate_style_guide(
    project_id: str,
    req: GenerateRequest | None = None,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[StyleGuideContent]:
    """AI 生成文风指南

    从项目 meta.json 读取题材/主题/基调等信息，调用 LLM 生成文风指南。
    也支持通过请求体传入自定义参数覆盖 meta.json。
    """
    fs = _make_file_service(settings)

    # 检查项目是否存在
    if not await fs.exists(project_id):
        raise ProjectNotFoundError(project_id)

    # 读取 meta.json
    meta = {}
    meta_rel_path = _meta_rel_path(project_id)
    if await fs.exists(meta_rel_path):
        meta_raw, _, _ = await fs.read_file(meta_rel_path)
        meta = json.loads(meta_raw)

    genre = req.genre if req and req.genre else meta.get("genre", "")
    theme = req.theme if req and req.theme else meta.get("theme", "")
    tone = req.tone if req and req.tone else meta.get("tone", "")
    writing_style = req.writing_style if req and req.writing_style else meta.get("writing_style", "")

    if not any([genre, theme, tone, writing_style]):
        return ApiResponse.ok(StyleGuideContent(
            content=DEFAULT_STYLE_GUIDE,
            last_modified=datetime.now().isoformat(),
        ))

    # 调用 LLM
    prompt = _GENERATE_PROMPT.format(genre=genre, theme=theme, tone=tone, writing_style=writing_style)
    llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, settings)
    svc = LLMService(llm_cfg)
    messages = [{"role": "user", "content": prompt}]
    try:
        generated = await svc.complete_sync(messages, timeout=60)
    except Exception as e:
        logger.warning("AI 生成文风指南失败: %s", e)
        return ApiResponse.ok(StyleGuideContent(
            content=DEFAULT_STYLE_GUIDE,
            last_modified=datetime.now().isoformat(),
        ))

    content = generated.strip()
    if not content:
        content = DEFAULT_STYLE_GUIDE

    # 写入文件
    rel_path = _style_guide_rel_path(project_id)
    await fs.write_file(rel_path, content)
    logger.info("文风指南已通过 AI 生成: %s", project_id)

    return ApiResponse.ok(StyleGuideContent(
        content=content,
        last_modified=datetime.now().isoformat(),
    ))


# ─── 默认文风指南模板 ─────────────────────────────────────────────────

DEFAULT_STYLE_GUIDE = """# 文风指南

## 一、文风定位
- 整体风格：简洁干练 / 华丽优美 / 口语化 / 古风典雅 / 冷峻硬朗 / 温暖治愈
- 句子节奏：
- 描写密度：
- 语言特点：

## 二、示范文字
（用户上传的示范文字片段，用于参考学习）

## 三、写作风格要点
- 叙述方式：
- 对话风格：
- 心理描写：
- 场景描写：

## 四、写作禁忌
- 避免的表达方式1：
- 避免的表达方式2：
- 避免的表达方式3：

## 五、题材特点
- 本题材特有的表达习惯：
- 行业术语/设定术语的使用规范：

## 六、角色说话风格
### 主角
- 说话风格：
- 口头禅：
- 语言习惯：

### 其他角色
- 说话风格：
- 语言特点：

## 七、参考范例
（用户认可的优秀文风范例）
"""


# ─── 工具函数 ────────────────────────────────────────────────────────

def _make_file_service(settings: Settings) -> FileService:
    """创建 FileService 实例"""
    return FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)


def _style_guide_rel_path(project_id: str) -> str:
    """获取 style-guide.md 的 FileService 相对路径"""
    return f"{project_id}/style-guide.md"


def _meta_rel_path(project_id: str) -> str:
    """获取 meta.json 的 FileService 相对路径"""
    return f"{project_id}/meta.json"


# ─── 路由 ────────────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ApiResponse[StyleGuideContent])
async def get_style_guide(
    project_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[StyleGuideContent]:
    """获取文风指南内容

    Args:
        project_id: 项目ID

    Returns:
        文风指南内容和最后修改时间

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    fs = _make_file_service(settings)
    rel_path = _style_guide_rel_path(project_id)

    # 检查项目是否存在
    if not await fs.exists(project_id):
        raise ProjectNotFoundError(project_id)

    # 如果文件不存在，创建默认模板
    if not await fs.exists(rel_path):
        logger.info("文风指南文件不存在，创建默认模板: %s", project_id)
        await fs.write_file(rel_path, DEFAULT_STYLE_GUIDE)
        return ApiResponse.ok(StyleGuideContent(
            content=DEFAULT_STYLE_GUIDE,
            last_modified=datetime.now().isoformat()
        ))

    # 读取文件
    content, _, mtime = await fs.read_file(rel_path)
    last_modified = datetime.fromtimestamp(mtime).isoformat() if mtime else None

    logger.debug("获取文风指南成功: %s", project_id)
    return ApiResponse.ok(StyleGuideContent(
        content=content,
        last_modified=last_modified
    ))


@router.post("/{project_id}", response_model=ApiResponse[None])
async def save_style_guide(
    project_id: str,
    req: SaveStyleGuideRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    """保存文风指南内容

    Args:
        project_id: 项目ID
        req: 保存请求，包含新的文风指南内容

    Returns:
        保存成功响应

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    fs = _make_file_service(settings)
    rel_path = _style_guide_rel_path(project_id)

    # 检查项目是否存在
    if not await fs.exists(project_id):
        raise ProjectNotFoundError(project_id)

    # 写入文件
    await fs.write_file(rel_path, req.content)

    logger.info("文风指南已保存: %s", project_id)
    return ApiResponse.ok(message="文风指南已保存")
