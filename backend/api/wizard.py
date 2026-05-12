"""墨韵 - Wizard 新建项目流程 API

端点：
  POST /api/wizard/generate-idea       生成书名和创意
  POST /api/wizard/{project_id}/generate-outline  生成大纲
  POST /api/wizard/{project_id}/confirm-outline  确认大纲
"""

import json
import logging
import litellm
import re

from fastapi import APIRouter, Depends
from backend.config import Settings, get_settings
from backend.schemas.common import ApiResponse
from backend.schemas.project import (
    BookIdeaRequest,
    BookIdeaResponse,
    GenerateOutlineRequest,
    OutlineResponse,
    ConfirmOutlineRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["wizard"])


@router.post("/wizard/generate-idea", response_model=ApiResponse[BookIdeaResponse])
async def generate_book_idea(
    req: BookIdeaRequest,
    settings: Settings = Depends(get_settings),
):
    """Wizard 步骤1：生成书名和创意"""
    logger.info("生成书名创意", extra={"genre": req.genre, "tone": req.tone})

    prompt = f"""你是一位资深网文编辑。请根据以下参数，为作者生成一个吸引人的书名和创意描述。

## 创作参数
- 题材：{req.genre}
- 基调：{req.tone or '任意'}
- 主题：{req.theme or '待定'}
- 风格：{req.writing_style or '待定'}
- 目标字数：{req.target_word_count // 10000}万字

请以JSON格式返回，格式如下：
{{
    "name": "书名（简洁有力，2-8字）",
    "description": "创意描述（200-400字，描述故事的核心卖点、主角设定、世界观特色等）"
}}

请直接返回JSON，不要添加任何前缀或解释。"""

    try:
        cfg_file = settings.workspace_path / ".config.json"
        llm_cfg = {}
        if cfg_file.exists():
            try:
                raw_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                # 优先使用嵌套的 llm 配置
                llm_cfg = raw_cfg.get("llm", {})
                # 如果 llm 配置为空或 apiType 为空，回退到顶层配置（兼容旧格式）
                if not llm_cfg or not llm_cfg.get("apiType"):
                    llm_cfg = {
                        "apiType": raw_cfg.get("apiType", "openai"),
                        "apiUrl": raw_cfg.get("apiUrl", ""),
                        "apiKey": raw_cfg.get("apiKey", ""),
                        "model": raw_cfg.get("model", ""),
                    }
            except Exception:
                pass

        model = llm_cfg.get("model", settings.llm_model)
        api_type = llm_cfg.get("apiType", "openai")
        # 对于 DeepSeek，确保模型名包含 provider 前缀
        if api_type == "deepseek" and model and not model.startswith("deepseek/"):
            model = "deepseek/" + model
        elif api_type == "deepseek" and not model:
            model = "deepseek/deepseek-chat"

        logger.info("Wizard LLM配置", extra={"api_type": api_type, "model": model, "has_key": bool(llm_cfg.get("apiKey"))})

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        if llm_cfg.get("apiKey"):
            kwargs["api_key"] = llm_cfg["apiKey"]
        if llm_cfg.get("apiUrl"):
            kwargs["api_base"] = llm_cfg["apiUrl"]

        logger.info("调用LLM生成书名", extra={"model": model})
        response = await litellm.acompletion(**kwargs)
        content = response.choices[0].message.content.strip()
        logger.info("LLM返回内容", extra={"content_length": len(content), "content_preview": content[:100]})

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        result = json.loads(content)
        return ApiResponse.ok(BookIdeaResponse(**result))

    except Exception as e:
        logger.error(f"生成书名创意失败: {e}")
        default_name = f"《{req.genre}故事》"
        default_desc = f"这是一个关于{req.genre}的精彩故事，充满了{req.tone or '引人入胜'}的情节。"
        return ApiResponse.ok(BookIdeaResponse(name=default_name, description=default_desc))


@router.post("/wizard/{project_id}/generate-outline", response_model=ApiResponse[OutlineResponse])
async def generate_outline(
    project_id: str,
    req: GenerateOutlineRequest,
    settings: Settings = Depends(get_settings),
):
    """Wizard 步骤2：生成章节大纲"""
    logger.info("生成大纲", extra={"project_id": project_id, "genre": req.genre})

    sections = req.target_word_count // 1800
    chapters = max(5, sections // 4)

    prompt = f"""你是一位资深网文大纲师。请为以下小说生成详细的章节大纲。

## 作品信息
- 书名：{req.book_name or '待定'}
- 题材：{req.genre}
- 基调：{req.tone or '待定'}
- 主题：{req.theme or '待定'}
- 风格：{req.writing_style or '待定'}
- 目标字数：{req.target_word_count // 10000}万字

## 创意描述
{req.book_description or '请根据题材自主发挥'}

## 要求
1. 生成{chapters}章的大纲
2. 每章包含：章节名、章节简介（100-150字）、主要情节点（3-5个）
3. 使用Markdown格式

请直接返回大纲内容，使用以下格式：

# 第1章 章节名
## 简介
...
## 情节点
...
"""

    try:
        cfg_file = settings.workspace_path / ".config.json"
        llm_cfg = {}
        if cfg_file.exists():
            try:
                raw_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                # 优先使用嵌套的 llm 配置
                llm_cfg = raw_cfg.get("llm", {})
                # 如果 llm 配置为空或 apiType 为空，回退到顶层配置（兼容旧格式）
                if not llm_cfg or not llm_cfg.get("apiType"):
                    llm_cfg = {
                        "apiType": raw_cfg.get("apiType", "openai"),
                        "apiUrl": raw_cfg.get("apiUrl", ""),
                        "apiKey": raw_cfg.get("apiKey", ""),
                        "model": raw_cfg.get("model", ""),
                    }
            except Exception:
                pass

        model = llm_cfg.get("model", settings.llm_model)
        api_type = llm_cfg.get("apiType", "openai")
        # 对于 DeepSeek，确保模型名包含 provider 前缀
        if api_type == "deepseek" and model and not model.startswith("deepseek/"):
            model = "deepseek/" + model
        elif api_type == "deepseek" and not model:
            model = "deepseek/deepseek-chat"

        logger.info("Wizard LLM配置(大纲)", extra={"api_type": api_type, "model": model, "has_key": bool(llm_cfg.get("apiKey"))})

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4000,
        }
        if llm_cfg.get("apiKey"):
            kwargs["api_key"] = llm_cfg["apiKey"]
        if llm_cfg.get("apiUrl"):
            kwargs["api_base"] = llm_cfg["apiUrl"]

        logger.info("调用LLM生成大纲", extra={"model": model, "chapters": chapters})
        response = await litellm.acompletion(**kwargs)
        outline_content = response.choices[0].message.content.strip()
        logger.info("LLM返回大纲内容", extra={"content_length": len(outline_content), "content_preview": outline_content[:200]})

        chapters_info = []
        chapter_pattern = r'#\s*第(\d+)章\s+(.+?)(?=\n#|\Z)'
        for match in re.finditer(chapter_pattern, outline_content, re.DOTALL):
            chapter_num = match.group(1)
            chapter_title = match.group(2).strip().split('\n')[0]
            chapters_info.append({
                "id": f"chapter-{chapter_num}",
                "name": chapter_title,
                "sections": 4,
            })

        return ApiResponse.ok(OutlineResponse(
            outline=outline_content,
            chapters=chapters_info
        ))

    except Exception as e:
        logger.error(f"生成大纲失败: {e}")
        default_outline = f"# {req.book_name or '新作品'} - 大纲\n\n待生成详细大纲...\n"
        return ApiResponse.ok(OutlineResponse(outline=default_outline, chapters=[]))


@router.post("/wizard/{project_id}/confirm-outline", response_model=ApiResponse)
async def confirm_outline(
    project_id: str,
    req: ConfirmOutlineRequest,
    settings: Settings = Depends(get_settings),
):
    """Wizard 步骤3：确认大纲并创建目录结构"""
    from pathlib import Path
    from backend.api.projects import _load_meta, _project_info, _meta_path
    from datetime import datetime, timezone

    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(project_id)

    logger.info("确认大纲", extra={"project_id": project_id})

    # 更新 outline.md
    outline_path = project_dir / "outline.md"
    outline_path.write_text(req.outline, encoding="utf-8")

    # 解析章节并创建目录
    chapters_dir = project_dir / "chapters"
    import re
    chapter_pattern = r'#\s*第(\d+)章\s+(.+?)(?=\n#|\Z)'

    for match in re.finditer(chapter_pattern, req.outline, re.DOTALL):
        chapter_num = match.group(1).zfill(3)
        chapter_title = match.group(2).strip().split('\n')[0]
        chapter_dir = chapters_dir / f"chapter-{chapter_num}"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        chapter_file = chapter_dir / f"{chapter_num}-{chapter_title}.md"
        if not chapter_file.exists():
            chapter_file.write_text(
                f"# 第{chapter_num}章 {chapter_title}\n\n",
                encoding="utf-8"
            )

    # 更新 meta.json
    meta = _load_meta(project_dir)
    if meta:
        chapter_count = len(list(chapters_dir.glob("chapter-*")))
        meta["chapter_count"] = chapter_count
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        _meta_path(project_dir).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    return ApiResponse.ok(message="大纲已确认，目录结构已创建")
