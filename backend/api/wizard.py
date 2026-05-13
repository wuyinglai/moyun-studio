"""墨韵 - Wizard 新建项目流程 API

端点：
  POST /api/wizard/generate-idea       生成书名和创意
  POST /api/wizard/{project_id}/generate-outline  生成大纲
  POST /api/wizard/{project_id}/confirm-outline  确认大纲
"""

import json
import logging
import math
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.core.llm import (
    LLMService,
    load_llm_config_from_workspace,
)
from backend.api.projects import _load_meta, _load_context, _project_info, _meta_path, _context_path
from backend.core.prompt_engine import PromptEngine
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
        llm_cfg = load_llm_config_from_workspace(settings)
        svc = LLMService.from_workspace_config(llm_cfg)

        logger.info("Wizard LLM配置", extra={"api_type": llm_cfg.get("apiType", "openai"), "model": svc.config.model, "has_key": bool(llm_cfg.get("apiKey"))})

        logger.info("调用LLM生成书名", extra={"model": svc.config.model})
        content = await svc.complete_sync([{"role": "user", "content": prompt}], temperature=0.7)
        content = content.strip()
        logger.info("LLM返回内容", extra={"content_length": len(content), "content_preview": content[:100]})

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        result = json.loads(content)
        return ApiResponse.ok(BookIdeaResponse(**result))

    except Exception as e:
        logger.error(f"生成书名创意失败: {e}", exc_info=True)
        raise


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
        llm_cfg = load_llm_config_from_workspace(settings)
        svc = LLMService.from_workspace_config(llm_cfg)

        logger.info("Wizard LLM配置(大纲)", extra={"api_type": llm_cfg.get("apiType", "openai"), "model": svc.config.model, "has_key": bool(llm_cfg.get("apiKey"))})

        logger.info("调用LLM生成大纲", extra={"model": svc.config.model, "chapters": chapters})
        outline_content = await svc.complete_sync([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=4000)
        outline_content = outline_content.strip()
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
        logger.error(f"生成大纲失败: {e}", exc_info=True)
        raise


@router.post("/wizard/{project_id}/confirm-outline", response_model=ApiResponse)
async def confirm_outline(
    project_id: str,
    req: ConfirmOutlineRequest,
    settings: Settings = Depends(get_settings),
):
    """Wizard 步骤3：确认大纲并创建卷/章/节目录结构

    创建 3 级结构：
      chapters/vol-XX/ch-XXX/sec-XXX.md
      chapters/vol-XX/ch-XXX/feedback/
      chapters/vol-XX/ch-XXX/revision-log/
      chapters/vol-XX/vol-meta.json
      chapters/vol-XX/ch-XXX/ch-meta.json
    """
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    logger.info("确认大纲", extra={"project_id": project_id})

    # 更新 outline.md
    outline_path = project_dir / "outline.md"
    outline_path.write_text(req.outline, encoding="utf-8")

    # 解析章节
    chapter_pattern = r'#\s*第(\d+)章\s+(.+?)(?=\n#|\Z)'
    chapters = []
    for match in re.finditer(chapter_pattern, req.outline, re.DOTALL):
        chapters.append({
            "number": int(match.group(1)),
            "title": match.group(2).strip().split('\n')[0],
            "sections": 4,  # 每章默认 4 节
        })

    if not chapters:
        logger.warning("大纲中未解析到章节", extra={"project_id": project_id})
        return ApiResponse.ok(message="大纲已确认，但未解析到章节内容")

    total_chapters = len(chapters)

    # 计算卷分组：每卷 8-15 章
    num_volumes = max(1, min(3, total_chapters // 10 + (1 if total_chapters % 10 > 5 else 0)))
    chapters_per_volume = math.ceil(total_chapters / num_volumes)

    # 清理旧的目录结构（平级 chapter-* 和旧版 vol-*）
    chapters_dir = project_dir / "chapters"
    for old in list(chapters_dir.glob("chapter-*")) + list(chapters_dir.glob("vol-*")):
        if old.is_dir():
            shutil.rmtree(old)

    # 创建卷/章/节 3 级目录
    total_sections = 0
    for vol_idx in range(num_volumes):
        start = vol_idx * chapters_per_volume
        end = min(start + chapters_per_volume, total_chapters)
        vol_chapters = chapters[start:end]
        if not vol_chapters:
            continue

        vol_dir = chapters_dir / f"vol-{vol_idx + 1:02d}"
        vol_dir.mkdir(parents=True, exist_ok=True)

        # vol-meta.json
        (vol_dir / "vol-meta.json").write_text(
            json.dumps({
                "volume_number": vol_idx + 1,
                "chapter_range": f"{vol_chapters[0]['number']:03d}-{vol_chapters[-1]['number']:03d}",
                "total_chapters": len(vol_chapters),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        for ch in vol_chapters:
            ch_dir = vol_dir / f"ch-{ch['number']:03d}"
            ch_dir.mkdir(parents=True, exist_ok=True)

            safe_title = re.sub(r'[<>:"/\\|?*]', '', ch['title'])

            # ch-meta.json
            (ch_dir / "ch-meta.json").write_text(
                json.dumps({
                    "chapter_number": ch['number'],
                    "title": ch['title'],
                    "section_count": ch['sections'],
                    "word_count": 0,
                    "status": "draft",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # 子目录
            (ch_dir / "feedback").mkdir(exist_ok=True)
            (ch_dir / "revision-log").mkdir(exist_ok=True)

            # sec-001.md ~ sec-00N.md
            for sec_num in range(1, ch['sections'] + 1):
                sec_file = ch_dir / f"sec-{sec_num:03d}.md"
                if not sec_file.exists():
                    sec_file.write_text(
                        f"# 第{ch['number']}章 {ch['title']} - 第{sec_num}节\n\n",
                        encoding="utf-8"
                    )

            total_sections += ch['sections']

    # 更新 meta.json
    meta = _load_meta(project_dir)
    if meta:
        meta.update({
            "chapter_count": total_chapters,
            "volume_count": num_volumes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        _meta_path(project_dir).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # 更新 context.json
    context = _load_context(project_dir)
    if context:
        context["stats"].update({
            "total_sections": total_sections,
            "chapter_count": total_chapters,
            "volume_count": num_volumes,
        })
        context["updated_at"] = datetime.now(timezone.utc).isoformat()
        _context_path(project_dir).write_text(
            json.dumps(context, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    logger.info("目录结构创建完成", extra={
        "project_id": project_id,
        "volumes": num_volumes,
        "chapters": total_chapters,
        "sections": total_sections,
    })

    return ApiResponse.ok(message="大纲已确认，卷/章/节目录结构已创建")
