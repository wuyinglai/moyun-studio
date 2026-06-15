"""墨韵 - 管线引擎

职责：
- 加载管线 YAML 定义
- 按步骤顺序执行 LLM 调用
- 失败时自动 fallback
- 以 AsyncGenerator 形式输出 SSE 事件

管线 YAML 路径：workspace/prompts/pipeline/{name}.yaml
每步 Prompt 路径：workspace/prompts/pipeline/{name}/{step_id}.md
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
import difflib
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any
import uuid

try:
    import tiktoken
except ImportError:
    tiktoken = None

from jinja2 import Environment, FileSystemLoader
import yaml

from backend.application.memory_service import MemoryService
from backend.application.pipeline.context import NodeResult, PipelineContext
from backend.application.pipeline.registry import NodeExecutorRegistry
from backend.config import get_settings
from backend.core.beat_validator import (
    RequiredBeatValidator,
    extract_beat_validation_inputs,
    is_beat_validation_enabled,
)
from backend.core.candidate_service import CandidateService
from backend.core.exceptions import MoyunFileNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService
from backend.core.prompt_versioning import archive_prompt
from backend.core.scene_plan_validator import validate_scene_plan, validate_scene_plan_target_binding
from backend.policies.generation_output_policy import (
    OutputDecision,
    decide_output,
    is_dangerous_output,
)
from backend.schemas.candidate import CandidateAction
from backend.schemas.pipeline import PipelineDef
from backend.schemas.scene_plan import ScenePlan

logger = logging.getLogger(__name__)

_LEGACY_DEFAULT_PROMPT_HASHES: dict[str, set[str]] = {
    # Old workspace defaults can shadow upgraded system prompts forever because
    # workspace/prompts has priority. Only bypass exact known legacy defaults;
    # user-edited prompts keep their normal override behavior.
    "blocks/writing-rules.md": {
        "b6ef56de4b810f8b9089d013c3a32f1a30688547a5d7dafd4aa528ae2ea1b7d5",
    },
    "pipeline/generate/write.md": {
        "a830fcadb3175f4bf965c0243abfee52e1168681310a238f0b759996e591451a",
    },
}

_COMMON_CHINESE_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋庞熊纪舒屈项祝董梁杜"
    "阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田胡凌霍虞万"
    "支柯昝管卢莫经房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉龚程嵇邢裴"
    "陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车"
    "侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘斜厉戎祖武符刘景詹龙叶幸司韶黎"
)

# Multi-char suffixes: unambiguous location/object markers, prefix up to 2 chars
_CONTINUITY_MULTI_SUFFIX_PATTERN = re.compile(
    r"[\u4e00-\u9fff]{1,2}(?:计划|项目|组织|集团|芯片|车票|钥匙|罗盘|玉佩"
    r"|月台|档案室|实验室|钟楼|教堂|宫殿|山庄|客栈|书院)"
)
# Single-char suffixes: can be verbs in narrative, restrict prefix to 1-2 chars
_CONTINUITY_SINGLE_SUFFIX_PATTERN = re.compile(
    r"[\u4e00-\u9fff]{1,2}(?:站|城|镇|村|港|楼|塔|盟|局|门|宗|刀|剑)"
)
# Location names preceded by a preposition — captures full name including
# suffix like 站/城 that would otherwise be ambiguous with a verb.
_LOCATION_WITH_PREP_PATTERN = re.compile(
    r"(?:在|从|到|去|回)([\u4e00-\u9fff]{2,4}(?:站|城|镇|村|港|楼|塔))"
)
# Standalone keywords: unambiguous entities that need no prefix
_STANDALONE_KEYWORDS = re.compile(r"追踪者|档案室|灰塔实验室|实验室|钟楼|灰塔|芯片|月台|山庄|客栈|书院|教堂|宫殿")
_CHINESE_NAME_PATTERN = re.compile(fr"[{_COMMON_CHINESE_SURNAMES}][\u4e00-\u9fff]{{1,2}}")
_QUOTED_ENTITY_PATTERN = re.compile(r"[“《]([^”》]{2,12})[”》]")
# Known false positives from the surname-based name pattern.
# These are common words/phrases that happen to start with a surname char.
_NAME_NOISE_WORDS = {"余温", "余地", "余光", "余额", "余生", "余款", "余粮"}


def _extract_continuity_anchors(text: str, limit: int = 12) -> list[str]:
    """Extract lightweight continuity anchors from prior scene text.

    Focuses on named entities (people, places, key objects) rather than
    sentence fragments.  Uses position-aware filtering to distinguish
    location suffixes (e.g. ``旧港站``) from homographic verbs
    (e.g. ``林澈站在``).
    """
    if not text:
        return []

    # Collect raw candidates as (matched_text, start_position, is_standalone).
    # Priority order: names (critical for continuity) → standalone keywords →
    # location-with-prep → multi-suffix → single-suffix.
    raw: list[tuple[str, int, bool]] = []
    for match in _CHINESE_NAME_PATTERN.finditer(text):
        raw.append((match.group(0), match.start(), False))
    for match in _QUOTED_ENTITY_PATTERN.finditer(text):
        raw.append((match.group(1), match.start(), True))
    for match in _STANDALONE_KEYWORDS.finditer(text):
        raw.append((match.group(0), match.start(), True))
    for match in _LOCATION_WITH_PREP_PATTERN.finditer(text):
        # Group 1 is the location name (without the preposition)
        loc = match.group(1)
        loc_start = match.start(1)
        raw.append((loc, loc_start, True))
    for match in _CONTINUITY_MULTI_SUFFIX_PATTERN.finditer(text):
        raw.append((match.group(0), match.start(), False))
    for match in _CONTINUITY_SINGLE_SUFFIX_PATTERN.finditer(text):
        raw.append((match.group(0), match.start(), False))

    ignored = {"第1卷", "第1章", "第1场", "下一秒", "这一刻", "那一刻", "计划", "车票", "蓝灯"}
    leading_noise = "在从向着被把将的了着过仍和与及那这自打朝"
    trailing_noise = "把在从向被将对与和的了着过仍背里上中下内外前后"
    _separators = ("的", "把", "将", "攥着", "拿着", "藏进")
    _name_following_verbs = "站靠坐走跑看说问答喊叫望盯瞪抱握攥拿提推拉躺跪趴把将被让给从在向"
    anchors: list[str] = []
    for item, start, standalone in raw:
        item = item.strip(" ：:，,。.；;、\n\t")
        if not item:
            continue
        # Strip leading particles/prepositions (keep at least 2 chars)
        if not standalone:
            while item and item[0] in leading_noise and len(item) > 2:
                item = item[1:]
                start += 1
        # Split on separators to keep only the entity part
        for separator in _separators:
            if separator in item and len(item.rsplit(separator, 1)[-1]) >= 2:
                new_item = item.rsplit(separator, 1)[-1]
                start += len(item) - len(new_item)
                item = new_item
        # If starts with a Chinese name followed by a verb, keep only the name.
        # Check 2-char names first (more common), then 3-char names.
        if len(item) > 2 and item[0] in _COMMON_CHINESE_SURNAMES:
            name = None
            rest = ""
            if len(item) >= 3 and '\u4e00' <= item[1] <= '\u9fff' and item[2] in _name_following_verbs:
                name = item[:2]
                rest = item[2:]
            elif len(item) >= 4 and '\u4e00' <= item[1] <= '\u9fff' and '\u4e00' <= item[2] <= '\u9fff' and item[3] in _name_following_verbs:
                name = item[:3]
                rest = item[3:]
            if name and rest:
                item = name
        # Context-aware trailing noise: strip trailing particles unless the
        # item is a standalone keyword or location-prep match (those are
        # already clean).
        if not standalone:
            while len(item) > 2 and item[-1] in trailing_noise:
                item = item[:-1]
        if len(item) < 2 or item in ignored:
            continue
        # Name noise filter: eliminate false positives from the surname-based
        # name pattern. Two complementary checks:
        # 1. Known noise words (common words starting with a surname char)
        # 2. 3-char candidates starting with grammar particles that never
        #    begin real Chinese names (经/已/被/将/从/向/让)
        if not standalone and item[0] in _COMMON_CHINESE_SURNAMES:
            if item in _NAME_NOISE_WORDS:
                continue
            _name_func_prefixes = "经已被将从向让"
            if len(item) == 3 and item[0] in _name_func_prefixes:
                continue
        if item not in anchors:
            anchors.append(item)
        if len(anchors) >= limit:
            break
    return anchors


def _continuity_anchor_hit_count(anchors: list[str], content: str) -> int:
    return sum(1 for anchor in anchors if anchor and anchor in content)


class PipelineError(Exception):
    pass


def _file_content(read_result: Any) -> str:
    """Return content from a FileService.read_file result."""
    if isinstance(read_result, tuple):
        return read_result[0]
    return str(read_result)


def _int_config(value: Any, default: int) -> int:
    """Return an integer config value, ignoring mocks or missing settings."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_scaffold_placeholder(path: str | None, content: str) -> bool:
    """Return True for project bootstrap templates that are safe to replace."""
    if not path or not content.strip():
        return False

    # Scaffold placeholders are always short (under 200 chars)
    if len(content.strip()) > 200:
        return False

    normalized_path = path.replace("\\", "/").rsplit("/", 1)[-1]
    stripped = content.strip()
    placeholder_markers = {
        "style-guide.md": ("# 文风指南", "在此描述写作风格"),
        "outline.md": ("大纲", "在此编写故事大纲"),
        "story-state.md": ("# 故事状态", "## 主角状态", "## 势力关系", "## 伏笔追踪", "## 主线进度"),
    }
    markers = placeholder_markers.get(normalized_path)
    if not markers:
        return False
    return all(marker in stripped for marker in markers)


def _has_substantive_content(path: str | None, content: str) -> bool:
    """Treat bootstrap placeholders as empty for first-run generation."""
    return bool(content and content.strip()) and not _is_scaffold_placeholder(path, content)


def _prompt_assembly_mode(extra_vars: dict | None) -> str:
    """Return the opt-in prompt assembly experiment mode."""
    if not extra_vars:
        return "default"
    mode = str(extra_vars.get("_prompt_assembly") or "").strip().lower()
    if mode == "facts_first":
        return "facts_first"
    return "default"


def _debug_prompt_export_enabled(extra_vars: dict | None) -> bool:
    """Return True only for explicit debug prompt export requests."""
    if not extra_vars:
        return False
    value = extra_vars.get("_debug_prompt_export")
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _select_prompt_template(relative_path: str, assembly_mode: str) -> str:
    """Map explicit experiment flags to alternate prompt templates."""
    normalized = relative_path.replace("\\", "/")
    if assembly_mode == "facts_first" and normalized == "pipeline/generate/write.md":
        return "pipeline/generate/write_facts_first.md"
    return relative_path


def _build_debug_prompt_payload(
    prompt_text: str,
    prompt_relative: str,
    assembly_mode: str,
    task_id: str,
    step_id: str,
    step_vars: dict[str, Any],
) -> dict[str, Any]:
    """Build a benchmark-friendly prompt export payload without secrets."""
    return {
        "task_id": task_id,
        "step_id": step_id,
        "template": prompt_relative,
        "assembly": assembly_mode,
        "prompt": prompt_text,
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "prompt_length": len(prompt_text),
        "summary": {
            "has_previous_text": bool(step_vars.get("previous_text")),
            "has_current_scene_text": bool(step_vars.get("current_scene_text")),
            "has_continuity_anchors": bool(step_vars.get("continuity_anchors")),
            "has_style_guide": bool(step_vars.get("style_guide")),
            "has_story_state": bool(step_vars.get("story_state")),
            "has_recent_context": bool(step_vars.get("recent_context")),
            "has_outline": bool(step_vars.get("outline")),
            "has_user_input": bool(step_vars.get("user_input")),
        },
    }


REFERENCE_PATTERN = re.compile(r"@\{([^}]+)\}")


class PipelineRunner:
    """管线执行引擎"""

    def __init__(
        self,
        prompts_path: Path,
        llm_service: LLMService,
        file_service: FileService,
        source: str = "system",
        system_prompts_path: Path | None = None,
    ):
        self.prompts_path = Path(prompts_path)
        self.system_prompts_path = system_prompts_path
        self.llm_service = llm_service
        self.file_service = file_service
        self.memory_service = MemoryService(file_service)
        self.source = source
        self.executor_registry = NodeExecutorRegistry()
        # 同一章内 context 步骤输出缓存，key=章目录路径 → context 文本
        self._context_cache: dict[str, str] = {}

        # 构建搜索路径：用户自定义路径优先，系统路径次之
        search_paths = [str(self.prompts_path)]
        if self.system_prompts_path:
            search_paths.append(str(self.system_prompts_path))
        self.env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=False,
        )

    def _get_pipeline_dir(self) -> Path:
        return self.prompts_path / "pipeline"

    def _get_pipeline_yaml_path(self, name: str) -> Path:
        return self._get_pipeline_dir() / f"{name}.yaml"

    def _get_step_prompt_path(self, pipeline_name: str, step_id: str) -> Path:
        return self._get_pipeline_dir() / pipeline_name / f"{step_id}.md"

    def render_prompt(self, relative_path: str, variables: dict) -> str:
        """使用 Jinja2 渲染 prompt 模板"""
        prompt_path = self._select_prompt_path(relative_path)
        if prompt_path:
            template_text = prompt_path.read_text(encoding="utf-8")
            template_text = self._inline_selected_includes(template_text)
            return self.env.from_string(template_text).render(**variables)

        template = self.env.get_template(relative_path)
        return template.render(**variables)

    def _select_prompt_path(self, relative_path: str) -> Path | None:
        normalized_path = relative_path.replace("\\", "/")
        user_path = self.prompts_path / normalized_path
        system_path = Path(self.system_prompts_path) / normalized_path if self.system_prompts_path else None

        if user_path.exists():
            if system_path and system_path.exists() and self._is_legacy_default_prompt(normalized_path, user_path):
                logger.warning("忽略过期默认 Prompt，使用系统新版: %s", normalized_path)
                return system_path
            return user_path

        if system_path and system_path.exists():
            return system_path
        return None

    def _is_legacy_default_prompt(self, relative_path: str, prompt_path: Path) -> bool:
        legacy_hashes = _LEGACY_DEFAULT_PROMPT_HASHES.get(relative_path)
        if not legacy_hashes:
            return False
        try:
            digest = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        except OSError:
            return False
        return digest in legacy_hashes

    def _inline_selected_includes(self, template_text: str) -> str:
        include_pattern = re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]\s*%}")

        def replace_include(match: re.Match[str]) -> str:
            include_path = match.group(1)
            selected_path = self._select_prompt_path(include_path)
            if not selected_path:
                return match.group(0)
            try:
                return selected_path.read_text(encoding="utf-8")
            except OSError:
                return match.group(0)

        return include_pattern.sub(replace_include, template_text)

    async def resolve_references(self, text: str, project_id: str) -> str:
        """解析 @{path} 引用为文件内容

        @{style-guide.md} -> 读取 {project_id}/style-guide.md 的内容
        只做单层解析（不递归处理被引用文件中的 @{}）。
        """
        if not text:
            return text

        result = text
        while True:
            match = REFERENCE_PATTERN.search(result)
            if not match:
                break
            file_path = match.group(1)
            try:
                content = _file_content(
                    await self.file_service.read_file(f"{project_id}/{file_path}")
                )
                replacement = content if content else ""
            except (MoyunFileNotFoundError, OSError):
                replacement = f"\n<!-- 文件 {file_path} 不存在 -->\n"
            result = result[:match.start()] + replacement + result[match.end():]

        return result

    async def load_project_meta(self, project_id: str) -> dict:
        """从项目 meta.json 加载项目配置变量

        返回 {变量名: 值} 字典，读取失败时返回空字典。
        映射关系：meta.json 的字段直接作为模板变量名（genre, theme, tone 等）。
        """
        try:
            content = _file_content(
                await self.file_service.read_file(f"{project_id}/meta.json")
            )
            if content:
                meta = json.loads(content)
                # 提取需要的字段，忽略内部字段（project_id, created_at 等）
                keys = ["genre", "theme", "tone", "background", "writing_style",
                        "target_word_count", "name"]
                return {k: meta.get(k, "") for k in keys}
        except (json.JSONDecodeError, MoyunFileNotFoundError, OSError):
            pass
        return {}

    async def load_system_variables(self, project_id: str) -> dict:
        """从项目目录加载系统变量

        返回 {变量名: 文件内容} 字典，文件不存在或读取失败时返回空字符串。

        额外从 target_file 对应的 ch-meta.json 加载 pending_foreshadowing 和 active_quests。
        """
        system_file_map = {
            "style_guide": "style-guide.md",
            "story_state": "story-state.md",
            "recent_context": "recent-context.md",
            "outline": "outline.md",
        }
        vars = {}
        for var_name, rel_path in system_file_map.items():
            try:
                content = _file_content(
                    await self.file_service.read_file(f"{project_id}/{rel_path}")
                )
                vars[var_name] = content
            except (MoyunFileNotFoundError, OSError):
                vars[var_name] = ""
        return vars

    async def load_chapter_vars(self, project_id: str, target_file: str) -> dict:
        """从章节元数据加载模板变量

        从 target_file（如 chapters/vol-01/ch-001/sec-001.md）推导 ch-meta.json 路径，
        提取 pending_foreshadowing 和 active_quests。
        """
        vars = {
            "pending_foreshadowing": "",
            "active_quests": "",
        }
        if not target_file or "/sec-" not in target_file:
            return vars

        parts = target_file.split("/")
        if len(parts) < 3:
            return vars
        chapter_dir = "/".join(parts[:-1])
        meta_path = f"{project_id}/{chapter_dir}/ch-meta.json"
        try:
            content = _file_content(await self.file_service.read_file(meta_path))
            if content:
                meta = json.loads(content)
                foreshadowing = meta.get("pending_foreshadowing", [])
                vars["pending_foreshadowing"] = json.dumps(foreshadowing, ensure_ascii=False) if foreshadowing else ""
                quests = meta.get("active_quests", [])
                vars["active_quests"] = json.dumps(quests, ensure_ascii=False) if quests else ""
        except (json.JSONDecodeError, MoyunFileNotFoundError, OSError):
            pass
        return vars

    def _find_pipeline_yaml(self, name: str) -> Path | None:
        """查找管线 YAML 文件（用户路径优先，系统路径次之）"""
        # 优先从用户路径查找
        user_path = self._get_pipeline_yaml_path(name)
        if user_path.exists():
            return user_path

        # 从系统路径查找
        if self.system_prompts_path:
            system_path = self.system_prompts_path / "pipeline" / f"{name}.yaml"
            if system_path.exists():
                return system_path

        return None

    def load_pipeline(self, name: str) -> PipelineDef:
        """加载管线 YAML 定义"""
        yaml_path = self._find_pipeline_yaml(name)
        if not yaml_path:
            raise PipelineError(f"管线不存在: {name}")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            return PipelineDef(**data)
        except Exception as e:
            raise PipelineError(f"加载管线定义失败 {name}: {e}") from e

    def list_pipelines(self) -> list[PipelineDef]:
        """列出所有可用管线（系统预置 + 用户自定义）"""
        pipelines = []
        seen = set()

        # 先从系统路径加载
        if self.system_prompts_path:
            system_pipeline_dir = self.system_prompts_path / "pipeline"
            if system_pipeline_dir.exists():
                for f in sorted(system_pipeline_dir.glob("*.yaml")):
                    try:
                        pipeline = self.load_pipeline(f.stem)
                        seen.add(pipeline.name)
                        pipelines.append(pipeline)
                    except Exception as e:
                        logger.warning("跳过无效系统管线定义 %s: %s", f.name, e)

        # 再从用户路径加载（覆盖同名系统管线）
        pipeline_dir = self._get_pipeline_dir()
        if pipeline_dir.exists():
            for f in sorted(pipeline_dir.glob("*.yaml")):
                try:
                    pipeline = self.load_pipeline(f.stem)
                    # 如果用户定义了同名管线，替换系统管线
                    if pipeline.name in seen:
                        idx = next(i for i, p in enumerate(pipelines) if p.name == pipeline.name)
                        pipelines[idx] = pipeline
                    else:
                        pipelines.append(pipeline)
                        seen.add(pipeline.name)
                except Exception as e:
                    logger.warning("跳过无效用户管线定义 %s: %s", f.name, e)

        return pipelines

    async def run(
        self,
        pipeline_name: str,
        project_id: str,
        target_file: str | None = None,
        user_input: str | None = None,
        output_mode: str = "write_scene",
        extra_vars: dict | None = None,
        stop_event: asyncio.Event | None = None,
        llm_extra_kwargs: dict | None = None,
        require_candidate: bool = False,
        action: str | None = None,
        scene_plan: ScenePlan | dict | None = None,
        dry_run: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """执行管线

        Yields:
            SSE 事件字典:
            - {"event": "task_start", "data": json}
            - {"event": "thinking", "data": json}
            - {"event": "step_done", "data": json}
            - {"event": "prompt", "data": json}
            - {"event": "generation", "data": json}
            - {"event": "done", "data": json}
            - {"event": "error", "data": json}
        """
        # Scene Plan 验证（如果提供）
        if scene_plan is not None:
            validation_result = validate_scene_plan(scene_plan)
            if not validation_result.valid:
                error_messages = [f"{e.field}: {e.message}" for e in validation_result.errors]
                yield {"event": "error", "data": json.dumps({"message": "Scene Plan 验证失败: " + "; ".join(error_messages), "task_id": f"pipeline-validate"})}
                return
            binding_result = validate_scene_plan_target_binding(scene_plan, target_file)
            if not binding_result.valid:
                error_messages = [f"{e.field}: {e.message}" for e in binding_result.errors]
                yield {"event": "error", "data": json.dumps({
                    "code": "SCENE_PLAN_TARGET_MISMATCH",
                    "message": "SCENE_PLAN_TARGET_MISMATCH: " + "; ".join(error_messages),
                    "task_id": "pipeline-validate",
                })}
                return
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning("Scene Plan 警告: %s: %s", warning.field, warning.message)
        
        pipeline = self.load_pipeline(pipeline_name)
        extra_vars = extra_vars or {}
        prompt_assembly = _prompt_assembly_mode(extra_vars)
        debug_prompt_export = _debug_prompt_export_enabled(extra_vars)
        continuity_source = str(
            extra_vars.get("previous_text")
            or extra_vars.get("current_scene_text")
            or ""
        )
        continuity_anchors = _extract_continuity_anchors(continuity_source)
        if continuity_anchors and not extra_vars.get("continuity_anchors"):
            extra_vars["continuity_anchors"] = "、".join(continuity_anchors)
        output_mode = await self._normalize_output_mode(
            pipeline_name=pipeline_name,
            project_id=project_id,
            target_file=target_file,
            output_mode=output_mode,
            require_candidate=require_candidate,
        )

        logger.info(
            "管线开始执行: %s (project=%s, target=%s, mode=%s)",
            pipeline_name, project_id, target_file, output_mode,
        )

        # 加载系统变量（文风指南、故事状态、近期上下文、大纲）
        system_vars = await self.load_system_variables(project_id)

        # 加载项目配置（genre, theme, tone 等）
        project_vars = await self.load_project_meta(project_id)

        # 加载章节变量（pending_foreshadowing, active_quests）
        chapter_vars = await self.load_chapter_vars(project_id, target_file or "")

        task_id = f"pipeline-{pipeline_name}-{uuid.uuid4().hex[:8]}"
        step_outputs: dict[str, str] = {}

        total_steps = len(pipeline.steps)
        yield {"event": "task_start", "data": json.dumps({
            "task_id": task_id,
            "pipeline": pipeline_name,
            "total_steps": total_steps,
        })}

        for i, step in enumerate(pipeline.steps):
            if stop_event and stop_event.is_set():
                yield {"event": "done", "data": json.dumps({"task_id": task_id, "message": "已取消"})}
                return

            is_final = (i == total_steps - 1)

            # 发送 thinking 事件
            yield {"event": "thinking", "data": json.dumps({
                "step_id": step.id,
                "label": step.label,
                "step": i + 1,
                "total": total_steps,
            })}

            try:
                # 读取文件内容
                file_content = ""
                if target_file:
                    try:
                        content = _file_content(
                            await self.file_service.read_file(f"{project_id}/{target_file}")
                        )
                        file_content = content
                    except Exception as e:
                        logger.warning("无法读取目标文件 %s/%s: %s", project_id, target_file, e)

                # 准备模板变量
                step_vars = {
                    "file_content": file_content,
                    "file_path": target_file or "",
                    "project_id": project_id,
                    "user_input": user_input or "",
                    "previous_output": step_outputs.get(step.fallback) if step.fallback else None,
                    **system_vars,
                    **project_vars,
                    **chapter_vars,
                    **extra_vars,
                }

                # 从 file_path 解析章节目录（作为 workflow loop_vars 的兜底）
                if target_file:
                    import re
                    m = re.search(r'vol-(\d+)/ch-(\d+)(?:/sec-(\d+))?', target_file)
                    if m:
                        step_vars.setdefault("vol", m.group(1))
                        step_vars.setdefault("ch", m.group(2))
                        step_vars.setdefault("sec", m.group(3) or "1")

                # 渲染 prompt 模板（使用 step.prompt 保证与 YAML 定义一致）
                prompt_relative = _select_prompt_template(f"{step.prompt}.md", prompt_assembly)
                prompt_text = self.render_prompt(prompt_relative, step_vars)

                # 解析 @{path} 引用为文件内容
                prompt_text = await self.resolve_references(prompt_text, project_id)

                # 发送渲染后的 prompt
                yield {"event": "prompt", "data": json.dumps({
                    "prompt": prompt_text,
                    "task_id": task_id,
                    "step_id": step.id,
                })}
                if debug_prompt_export:
                    yield {"event": "debug_prompt", "data": json.dumps(
                        _build_debug_prompt_payload(
                            prompt_text=prompt_text,
                            prompt_relative=prompt_relative,
                            assembly_mode=prompt_assembly,
                            task_id=task_id,
                            step_id=step.id,
                            step_vars=step_vars,
                        ),
                        ensure_ascii=False,
                    )}

                # G0118: 自动 token 检查 — 估算 prompt token 数，超限时发出警告
                prompt_tokens = self._estimate_tokens(prompt_text)
                max_prompt_tokens = _int_config(
                    getattr(self.llm_service.config, "max_prompt_tokens", None),
                    120000,
                )
                context_window = _int_config(
                    getattr(self.llm_service.config, "context_window", None),
                    max_prompt_tokens,
                )

                # RC1: ratio-based token budget warnings
                _soft_threshold = int(context_window * 0.75)
                _hard_threshold = int(context_window * 0.95)
                _usage_pct = prompt_tokens * 100 // context_window if context_window else 0

                if prompt_tokens > _hard_threshold:
                    yield {"event": "context_warning", "data": json.dumps({
                        "message": f"当前上下文较长（约 {prompt_tokens} tokens，占模型上下文 {_usage_pct}%），生成可能变慢或遗漏细节。建议缩短前文或分段生成。",
                        "severity": "hard",
                        "prompt_tokens": prompt_tokens,
                        "context_window": context_window,
                        "usage_pct": _usage_pct,
                        "task_id": task_id,
                    })}
                elif prompt_tokens > _soft_threshold:
                    yield {"event": "context_warning", "data": json.dumps({
                        "message": f"当前上下文已占模型上下文的 {_usage_pct}%（约 {prompt_tokens}/{context_window} tokens），请注意生成长度。",
                        "severity": "soft",
                        "prompt_tokens": prompt_tokens,
                        "context_window": context_window,
                        "usage_pct": _usage_pct,
                        "task_id": task_id,
                    })}

                if prompt_tokens > max_prompt_tokens:
                    warning_msg = f"Prompt 过长（约 {prompt_tokens} tokens），超出模型限制 {max_prompt_tokens} tokens"
                    if prompt_tokens > context_window:
                        warning_msg += "，建议：减少 recent_context / 只引用当前章摘要 / 分段执行"
                    yield {"event": "error", "data": json.dumps({
                        "message": warning_msg,
                        "task_id": task_id,
                        "warning": True,
                        "prompt_tokens": prompt_tokens,
                        "max_prompt_tokens": max_prompt_tokens,
                        "context_window": context_window,
                    })}

                # context 步骤缓存：同一章内复用已生成的上下文分析
                if step.id == "context" and target_file:
                    import re as _re
                    ch_match = _re.match(r"^(.*?ch-\d+)/", target_file)
                    if ch_match:
                        ch_key = ch_match.group(1)
                        cache_key = await self._build_context_cache_key(project_id, ch_key)
                        cached = self._context_cache.get(cache_key)
                        if cached is not None:
                            logger.info("复用 context 缓存: %s", ch_key)
                            step_output = cached
                            yield {"event": "prompt", "data": json.dumps({
                                "prompt": prompt_text,
                                "task_id": task_id,
                                "step_id": step.id,
                                "cached": True,
                            })}
                            step_outputs[step.id] = step_output
                            yield {"event": "step_done", "data": json.dumps({
                                "step_id": step.id,
                                "label": step.label,
                                "status": "done",
                            })}
                            continue

                # 构建执行上下文
                pipeline_context = PipelineContext(
                    project_id=project_id,
                    pipeline_name=pipeline_name,
                    target_file=target_file,
                    task_id=task_id,
                    output_mode=output_mode,
                    user_input=user_input,
                    step_outputs=dict(step_outputs),
                    system_vars=system_vars,
                    project_vars=project_vars,
                    chapter_vars=chapter_vars,
                    extra_vars=extra_vars,
                )

                # 通过 executor registry 执行步骤
                executor = self.executor_registry.get_executor(step)
                if dry_run:
                    step_output = f"[DRY-RUN] simulated output for step {step.id}"
                    step_outputs[step.id] = step_output
                    yield {"event": "generation", "data": json.dumps({
                        "step_id": step.id,
                        "task_id": task_id,
                        "dry_run": True,
                        "content": step_output,
                    })}
                else:
                    result = await executor.execute(
                        step=step,
                        context=pipeline_context,
                        prompt_text=prompt_text,
                        llm_service=self.llm_service,
                        file_service=self.file_service,
                        stop_event=stop_event,
                        llm_extra_kwargs=llm_extra_kwargs,
                    )

                    # 发送执行器产生的事件
                    for event in result.events:
                        yield event

                    step_output = result.output
                    step_outputs[step.id] = step_output

                # context 步骤完成后缓存到内存，同章后续 sec 复用
                if step.id == "context" and target_file:
                    import re as _re
                    ch_match = _re.match(r"^(.*?ch-\d+)/", target_file)
                    if ch_match:
                        ch_key = ch_match.group(1)
                        cache_key = await self._build_context_cache_key(project_id, ch_key)
                        self._context_cache[cache_key] = step_output

                # 如果步骤指定了 output 路径且执行器未处理，使用 FileOutputExecutor
                if not dry_run and step.output and step_output and not result.candidate_id:
                    file_executor = self.executor_registry.get_executor_by_name("file_output")
                    if file_executor:
                        # 更新上下文中的 step_outputs
                        pipeline_context.step_outputs[step.id] = step_output
                        file_result = await file_executor.execute(
                            step=step,
                            context=pipeline_context,
                            prompt_text=prompt_text,
                            llm_service=self.llm_service,
                            file_service=self.file_service,
                        )
                        for event in file_result.events:
                            yield event
                        if file_result.candidate_id:
                            result.candidate_id = file_result.candidate_id

                logger.info(
                    "管线步骤完成: %s/%s (output_len=%d)",
                    pipeline_name, step.id, len(step_output),
                )

                yield {"event": "step_done", "data": json.dumps({
                    "step_id": step.id,
                    "label": step.label,
                    "status": "done",
                })}

            except Exception as e:
                logger.error(
                    "管线步骤失败: %s/%s (fallback=%s, is_final=%s) - %s",
                    pipeline_name, step.id, step.fallback, is_final, e,
                )
                if step.fallback and step.fallback in step_outputs:
                    logger.info("回退到步骤 %s 的输出 (管线: %s)", step.fallback, pipeline_name)
                    step_outputs[step.id] = step_outputs[step.fallback]
                    # 回退时也使用统一方法写入步骤的 output 文件
                    if step.output and step_outputs[step.id]:
                        candidate_id = await self._write_step_output_or_candidate(
                            project_id, step.output, step_outputs[step.id], task_id, CandidateAction.MODIFY
                        )
                        if candidate_id:
                            yield {"event": "candidate_created", "data": json.dumps({
                                "task_id": task_id,
                                "candidate_id": candidate_id,
                                "source_path": step.output,
                                "action": CandidateAction.MODIFY.value,
                            })}
                    yield {"event": "step_done", "data": json.dumps({
                        "step_id": step.id,
                        "label": step.label,
                        "status": "fallback",
                    })}
                elif is_final:
                    _err_msg = e.message if hasattr(e, 'message') else str(e)
                    _err_code = getattr(e, 'code', None)
                    yield {"event": "error", "data": json.dumps({
                        "message": f"步骤 {step.label} 失败: {_err_msg}",
                        "task_id": task_id,
                        "error_code": _err_code,
                    })}
                    # 用上一步的输出兜底
                    if i > 0:
                        step_outputs[step.id] = step_outputs.get(pipeline.steps[i-1].id, "")
                    else:
                        return
                else:
                    # 中间步骤失败且无 fallback，终止管线
                    _err_msg = e.message if hasattr(e, 'message') else str(e)
                    _err_code = getattr(e, 'code', None)
                    yield {"event": "error", "data": json.dumps({
                        "message": f"步骤 {step.label} 失败: {_err_msg}",
                        "task_id": task_id,
                        "error_code": _err_code,
                    })}
                    return

        # 保存最终输出到文件
        # 注意：最后一步如果是 diff/update_story_state，输出不是章节内容，
        # 此时应使用上一步（润色/改写/生成）的输出作为文件内容
        last_step = pipeline.steps[-1]
        if last_step.id in ("diff", "update_story_state") and len(pipeline.steps) >= 2:
            final_output = step_outputs.get(pipeline.steps[-2].id, "")
        else:
            final_output = step_outputs.get(last_step.id, "")
        original_content = ""
        frontmatter = None
        candidate_id = None

        if final_output and target_file and not dry_run:
            try:
                orig, fm, _ = await self.file_service.read_file(f"{project_id}/{target_file}")
                original_content = orig
                frontmatter = fm
            except Exception as e:
                logger.warning("重新读取文件 %s/%s 失败: %s", project_id, target_file, e)

            # 判断是否需要生成候选稿
            should_use_candidate = output_mode == "candidate"
            if output_mode == "write_scene" and _has_substantive_content(target_file, original_content):
                should_use_candidate = True
            continuity_hit_count = _continuity_anchor_hit_count(continuity_anchors, final_output)
            continuity_required_hits = min(2, len(continuity_anchors))
            if (
                output_mode == "write_scene"
                and continuity_required_hits > 0
                and continuity_hit_count < continuity_required_hits
            ):
                should_use_candidate = True
                logger.warning(
                    "生成结果连续性不足，改存候选稿: target=%s anchors=%s hits=%d/%d",
                    target_file,
                    continuity_anchors,
                    continuity_hit_count,
                    continuity_required_hits,
                )
                yield {"event": "quality_warning", "data": json.dumps({
                    "task_id": task_id,
                    "target_file": target_file,
                    "code": "CONTINUITY_ANCHOR_MISS",
                    "message": "生成结果未能保留足够的上文关键元素，已改存为候选稿，未写入正式场景。",
                    "anchors": continuity_anchors,
                    "hit_count": continuity_hit_count,
                    "required_hits": continuity_required_hits,
                }, ensure_ascii=False)}

            if should_use_candidate:
                # 生成候选稿而不是直接覆盖
                candidate_service = CandidateService(self.file_service)
                action = self._infer_candidate_action(pipeline_name, output_mode, action=action)

                # 构建 continuity 信息（锚点保留度 + 严重等级）
                continuity_ratio = 0.0
                if continuity_anchors:
                    continuity_ratio = round(continuity_hit_count / len(continuity_anchors), 2)
                continuity_severity = "none"
                continuity_has_warning = False
                if continuity_anchors:
                    if continuity_hit_count == 0:
                        continuity_severity = "high"
                        continuity_has_warning = True
                    elif continuity_hit_count < continuity_required_hits:
                        continuity_severity = "medium"
                        continuity_has_warning = True
                    elif continuity_hit_count < len(continuity_anchors):
                        continuity_severity = "low"
                    else:
                        continuity_severity = "none"
                continuity_info = {
                    "has_warning": continuity_has_warning,
                    "severity": continuity_severity,
                    "anchors_missing": [a for a in continuity_anchors if a and a not in final_output],
                    "anchors_preserved": [a for a in continuity_anchors if a and a in final_output],
                    "continuity_ratio": continuity_ratio,
                }
                # 面向用户的简短警告摘要
                warning_message = None
                if continuity_has_warning:
                    if continuity_severity == "high":
                        warning_message = "可能与前文设定不一致，关键锚点几乎未保留，建议先预览再采纳。"
                    else:
                        warning_message = "部分上文关键元素未在生成结果中出现，建议先预览再采纳。"
                source_type = "dry-run" if dry_run else "llm"

                # 构建 Scene Plan provenance 信息
                generation_context = {}
                scene_plan_hash = ""
                scene_plan_path = ""

                if scene_plan:
                    generation_context["scene_plan_used"] = True
                    if isinstance(scene_plan, dict):
                        scene_plan_str = json.dumps(scene_plan, ensure_ascii=False, sort_keys=True)
                        scene_plan_hash = hashlib.md5(scene_plan_str.encode("utf-8")).hexdigest()
                    if "source_path" in scene_plan:
                        scene_plan_path = scene_plan["source_path"]
                else:
                    generation_context["scene_plan_used"] = False

                beat_validation = {}
                if is_beat_validation_enabled(extra_vars):
                    required_beats, forbidden_beats = extract_beat_validation_inputs(extra_vars)
                    generation_context["required_beats_input"] = [
                        {"id": f"beat-{idx + 1}", "text": beat}
                        for idx, beat in enumerate(required_beats)
                    ]
                    generation_context["forbidden_beats_input"] = [
                        {"id": f"forbid-{idx + 1}", "text": beat}
                        for idx, beat in enumerate(forbidden_beats)
                    ]
                    validator = RequiredBeatValidator(self.llm_service)
                    beat_validation = await validator.validate(
                        final_output,
                        required_beats=required_beats,
                        forbidden_beats=forbidden_beats,
                    )

                candidate = await candidate_service.create_candidate(
                    project_id=project_id,
                    source_path=target_file,
                    action=action,
                    content=final_output,
                    continuity=continuity_info,
                    source_type=source_type,
                    warning_message=warning_message,
                    generation_context=generation_context,
                    scene_plan_hash=scene_plan_hash,
                    scene_plan_path=scene_plan_path,
                    beat_validation=beat_validation,
                )
                candidate_id = candidate.id
                logger.info("已生成候选稿: %s -> %s (continuity=%s)", target_file, candidate_id, continuity_severity)
                yield {"event": "candidate_created", "data": json.dumps({
                    "task_id": task_id,
                    "candidate_id": candidate_id,
                    "source_path": target_file,
                    "action": action.value,
                    "continuity": continuity_info,
                    "source_type": source_type,
                    "warning_message": warning_message,
                    "beat_validation_status": beat_validation.get("status") if beat_validation else None,
                }, ensure_ascii=False)}
            elif output_mode == "write_scene":
                await self.file_service.write_file(f"{project_id}/{target_file}", final_output, frontmatter)
            elif output_mode == "append":
                new_content = (original_content + "\n\n" + final_output).strip()
                await self.file_service.write_file(f"{project_id}/{target_file}", new_content, frontmatter)
            elif output_mode == "dimension_file":
                # dimension_file 模式：各步骤已通过 step.output 写入各自文件
                # 不覆写目标文件（如正文章节），跳过 final write
                pass
        elif final_output and target_file and dry_run:
            yield {"event": "dry_run", "data": json.dumps({
                "task_id": task_id,
                "would_write_file": True,
                "would_create_candidate": bool(target_file),
                "output_mode": output_mode,
                "target_file": target_file,
                "final_output_len": len(final_output),
            })}

        # 生成完成后自动更新 story-state 和 recent-context
        if target_file and final_output and not candidate_id and not dry_run:
            await self._update_after_generation(project_id, target_file, final_output, original_content)

        # 内容有变化时生成 AI 修改摘要
        if original_content and final_output and final_output != original_content and not dry_run:
            try:
                summary = await self._generate_diff_summary(
                    project_id, target_file, original_content, final_output, task_id,
                    llm_extra_kwargs=llm_extra_kwargs,
                )
                if summary:
                    yield {"event": "diff_summary", "data": json.dumps({
                        "summary": summary,
                        "task_id": task_id,
                        "target_file": target_file,
                    })}
                    # 将摘要保存到 revision-log
                    await self._save_diff_summary_to_revision(project_id, target_file, summary)
            except Exception as e:
                logger.warning("生成修改摘要失败: %s", e)

        logger.info(
            "管线执行完成: %s (steps=%d, final_output_len=%d, dry_run=%s)",
            pipeline_name, total_steps, len(final_output), dry_run,
        )

        yield {"event": "done", "data": json.dumps({
            "task_id": task_id,
            "message": "管线执行完成",
            "dry_run": dry_run,
        })}

    async def _normalize_output_mode(
        self,
        pipeline_name: str,
        project_id: str,
        target_file: str | None,
        output_mode: str,
        require_candidate: bool = False,
    ) -> str:
        """Map legacy output modes to explicit safe behavior using GenerationOutputPolicy."""
        if require_candidate:
            return "candidate"

        # Check if target file has content
        file_has_content = False
        if target_file:
            try:
                content = _file_content(
                    await self.file_service.read_file(f"{project_id}/{target_file}")
                )
                file_has_content = _has_substantive_content(target_file, content)
            except Exception:
                logger.debug("文件内容检查失败", exc_info=True)

        decision = decide_output(
            action=pipeline_name,
            target_path=target_file or "",
            output_mode=output_mode,
            file_exists=True,  # if we got here, we're targeting something
            file_has_content=file_has_content,
            require_candidate=require_candidate,
            pipeline_name=pipeline_name,
        )

        # Map OutputDecision.mode back to output_mode strings
        # LEGACY_COMPAT: overwrite is accepted for old callers but normalized to safe modes.
        # New code should use write_scene / candidate / append.
        mode_map = {
            "write": "write_scene",
            "candidate": "candidate",
            "append": "append",
            "reject": "none",
        }
        return mode_map.get(decision.mode, output_mode)

    @staticmethod
    def _is_scene_file(path: str) -> bool:
        from backend.policies.generation_output_policy import is_scene_file as _is_scene
        return _is_scene(path)

    async def _update_after_generation(self, project_id: str, target_file: str, content: str, original_content: str = "") -> None:
        # — 更新 recent-context.md（仅对场景文件）—
        # 场景文件的 recent-context 追加由专门的场景记忆机制处理，
        # 避免为非场景文件（如 style-guide.md, 书名与创意.md）生成无意义的摘要。
        if "/sec-" in target_file:
            structured_summary = self.memory_service.build_scene_memory_prompt_output(target_file, content)
            await self.memory_service.append_scene_memory(project_id, target_file, structured_summary)

        # — 创建修改日志（仅当内容有变化且目标文件是章节文件） —
        if original_content and content != original_content and "/sec-" in target_file:
            try:
                # 从 target_file (如 chapters/vol-01/ch-001/sec-001.md) 提取章节目录
                parts = target_file.split("/")
                if len(parts) >= 3:
                    chapter_dir = "/".join(parts[:-1])  # chapters/vol-01/ch-001

                    # 生成 diff
                    before_lines = original_content.splitlines(keepends=True)
                    after_lines = content.splitlines(keepends=True)
                    diff = "".join(difflib.unified_diff(
                        before_lines, after_lines,
                        fromfile="修改前", tofile="修改后", lineterm=""
                    ))

                    # 统计字数
                    def _wc(text: str) -> int:
                        return len(re.findall(r'[一-鿿]', text)) + len(re.findall(r'[a-zA-Z]+', text))

                    log_entry = {
                        "id": f"rev-{uuid.uuid4().hex[:8]}",
                        "chapter_path": target_file,
                        "revision_type": "ai_rewrite",
                        "description": f"管线生成: {target_file.split('/')[-1]}",
                        "word_count_before": _wc(original_content),
                        "word_count_after": _wc(content),
                        "diff": diff,
                        "created_at": datetime.now().isoformat(),
                    }

                    log_path = f"{project_id}/{chapter_dir}/revision-log/{log_entry['id']}.json"
                    await self.file_service.write_file(log_path, json.dumps(log_entry, ensure_ascii=False, indent=2), None)
            except Exception as e:
                logger.warning("创建修改日志失败: %s", e)

    async def _build_context_cache_key(self, project_id: str, chapter_path: str) -> str:
        """构建 context 缓存键，包含相关文件的修改时间戳"""
        import hashlib

        # 需要监控的文件列表
        watched_files = [
            f"{project_id}/style-guide.md",
            f"{project_id}/story-state.md",
            f"{project_id}/recent-context.md",
            f"{project_id}/outline.md",
            f"{project_id}/meta.json",
        ]

        # 添加章节目录下的文件（.md 和 ch-meta.json）
        try:
            chapter_dir = self.file_service._resolve_path(f"{project_id}/{chapter_path}")
            if chapter_dir.exists() and chapter_dir.is_dir():
                for item in chapter_dir.iterdir():
                    if item.is_file():
                        if item.suffix == ".md":
                            watched_files.append(f"{project_id}/{chapter_path}/{item.name}")
                        elif item.name == "ch-meta.json":
                            watched_files.append(f"{project_id}/{chapter_path}/ch-meta.json")
        except Exception:
            logger.debug("构建缓存键：读取文件元数据失败", exc_info=True)
        mtimes = []
        for file_path in watched_files:
            try:
                full_path = self.file_service._resolve_path(file_path)
                if full_path.exists():
                    mtimes.append(str(full_path.stat().st_mtime))
                else:
                    mtimes.append("0")
            except Exception:
                mtimes.append("0")

        # 构建缓存键（带项目哈希前缀，便于按项目清除）
        key_parts = [project_id, chapter_path] + mtimes
        key_string = "|".join(key_parts)
        content_hash = hashlib.md5(key_string.encode()).hexdigest()

        # 添加项目哈希前缀
        project_hash = self._hash_project_id(project_id)
        return f"{project_hash}:{content_hash}"

    def clear_context_cache(self, project_id: str | None = None) -> None:
        """清除 context 缓存
        
        Args:
            project_id: 可选，只清除指定项目的缓存；不传则清除全部
        """
        if project_id:
            self._context_cache = {
                key: val for key, val in self._context_cache.items()
                if not key.startswith(self._hash_project_id(project_id))
            }
        else:
            self._context_cache.clear()
        logger.info("Context 缓存已清除 (project_id=%s)", project_id)

    def _hash_project_id(self, project_id: str) -> str:
        """生成项目ID的哈希值用于缓存键前缀"""
        import hashlib
        return hashlib.md5(project_id.encode()).hexdigest()[:8]

    def _infer_candidate_action(self, pipeline_name: str, output_mode: str, action: str | None = None) -> CandidateAction:
        """根据管线名称和输出模式推断候选稿动作类型"""
        # New action names take priority
        if action:
            action_lower = action.lower()
            if action_lower == "write_next_scene":
                return CandidateAction.CONTINUE
            elif action_lower == "write_current_scene":
                return CandidateAction.CONTINUE
            elif action_lower == "rewrite_current_scene":
                return CandidateAction.REWRITE
            elif action_lower == "polish_current_scene":
                return CandidateAction.POLISH
            elif action_lower == "chat_edit_current_scene":
                return CandidateAction.CHAT

        pipeline_name_lower = pipeline_name.lower()

        if "polish" in pipeline_name_lower or "润色" in pipeline_name:
            return CandidateAction.POLISH
        elif "expand" in pipeline_name_lower or "扩写" in pipeline_name:
            return CandidateAction.EXPAND
        elif "shrink" in pipeline_name_lower or "缩写" in pipeline_name:
            return CandidateAction.SHRINK
        elif "chat" in pipeline_name_lower or "对话" in pipeline_name:
            return CandidateAction.CHAT
        elif "continue" in pipeline_name_lower or "续写" in pipeline_name or output_mode == "append":
            return CandidateAction.CONTINUE
        elif "modify" in pipeline_name_lower or "修改" in pipeline_name:
            return CandidateAction.MODIFY
        else:
            return CandidateAction.REWRITE

    def _is_dangerous_output(self, output_path: str) -> bool:
        """判断输出路径是否为危险路径（需要候选稿保护）— 委托给 generation_output_policy"""
        return is_dangerous_output(output_path)

    async def _write_step_output_or_candidate(
        self,
        project_id: str,
        output_path: str,
        content: str,
        task_id: str | None = None,
        action: CandidateAction = CandidateAction.MODIFY,
    ) -> str | None:
        """统一写入步骤输出的方法

        如果输出路径是危险路径，创建候选稿；否则直接写入文件。

        Args:
            project_id: 项目ID
            output_path: 相对路径
            content: 要写入的内容
            task_id: 任务ID（用于 SSE 事件）
            action: 候选稿动作类型

        Returns:
            candidate_id 如果创建了候选稿，否则 None
        """
        if self._is_dangerous_output(output_path):
            logger.warning("跳过危险路径写入: %s (需要候选稿机制)", output_path)
            try:
                candidate_service = CandidateService(self.file_service)
                candidate = await candidate_service.create_candidate(
                    project_id=project_id,
                    source_path=output_path,
                    action=action,
                    content=content,
                )
                logger.info("危险路径输出已保存为候选稿: %s -> %s", output_path, candidate.id)
                return candidate.id
            except Exception as e:
                logger.warning("创建候选稿失败: %s", e)
                return None
        else:
            try:
                await self.file_service.write_file(
                    f"{project_id}/{output_path}", content, None
                )
                logger.info("步骤输出已写入: %s", output_path)
                return None
            except Exception as e:
                logger.warning("步骤输出写入失败 %s: %s", output_path, e)
                return None

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数

        优先使用 tiktoken，回退到字符估算。
        """
        if tiktoken:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text))
            except Exception:
                logger.debug("tiktoken 编码失败，回退到字符估算", exc_info=True)
        # 回退：字符估算
        from backend.utils.token_utils import estimate_tokens_fallback
        return estimate_tokens_fallback(text)

    async def _generate_diff_summary(
        self,
        project_id: str,
        target_file: str,
        original_content: str,
        modified_content: str,
        task_id: str,
        llm_extra_kwargs: dict | None = None,
    ) -> str | None:
        """生成 AI 修改摘要

        使用 diff-summary 管线的 analyze 步骤 prompt，调用 LLM 分析修改内容。
        返回结构化分析报告文本，失败时返回 None。

        llm_extra_kwargs：可选，用于 smoke 项目时强制 max_tokens。
        """
        try:
            # 加载 diff-summary 管线的 analyze 步骤
            prompt_rel = "pipeline/diff-summary/analyze.md"
            variables = {
                "original_content": original_content,
                "modified_content": modified_content,
                "file_content": modified_content,
                "project_id": project_id,
                "file_path": target_file,
                "user_input": "",
            }
            prompt_text = self.render_prompt(prompt_rel, variables)

            messages = [
                {"role": "system", "content": "你是一个文本处理工具。根据用户的指令处理文本，只输出处理结果本身，严禁输出任何解释、分析、问候、标题、编号或其他附加内容。"},
                {"role": "user", "content": prompt_text},
            ]
            summary_parts = []
            extra = llm_extra_kwargs or {}
            async for chunk in self.llm_service.complete(messages, timeout=60, **extra):
                summary_parts.append(chunk)

            summary = "".join(summary_parts)
            if summary.strip():
                return summary
        except Exception as e:
            logger.warning("生成修改摘要 LLM 调用失败: %s", e)
        return None

    async def _save_diff_summary_to_revision(
        self,
        project_id: str,
        target_file: str,
        summary: str,
    ) -> None:
        """将修改摘要保存到 revision-log 目录"""
        if "/sec-" not in target_file:
            return
        try:
            parts = target_file.split("/")
            if len(parts) >= 3:
                chapter_dir = "/".join(parts[:-1])
                entry_id = f"rev-ds-{uuid.uuid4().hex[:8]}"
                log_entry = {
                    "id": entry_id,
                    "chapter_path": target_file,
                    "revision_type": "diff_summary",
                    "description": f"AI 修改摘要: {target_file.split('/')[-1]}",
                    "summary": summary,
                    "created_at": datetime.now().isoformat(),
                }
                log_path = f"{project_id}/{chapter_dir}/revision-log/{entry_id}.json"
                await self.file_service.write_file(
                    log_path, json.dumps(log_entry, ensure_ascii=False, indent=2), None
                )
        except Exception as e:
            logger.warning("保存修改摘要到 revision-log 失败: %s", e)

    def get_pipeline_detail(self, name: str) -> dict:
        """获取管线详情（含每步 prompt 内容）"""
        pipeline = self.load_pipeline(name)
        steps = []
        for step in pipeline.steps:
            # 优先用 step.prompt 路径（实际用于生成的模板）
            prompt_content = ""
            if step.prompt:
                prompt_path = self._select_prompt_path(f"{step.prompt}.md")
                if prompt_path:
                    prompt_content = prompt_path.read_text(encoding="utf-8")
            # 如果 step.prompt 指向 pipeline 内置路径，补充尝试
            if not prompt_content:
                alt_path = self._get_step_prompt_path(name, step.id)
                if alt_path.exists():
                    prompt_content = alt_path.read_text(encoding="utf-8")
            steps.append({
                "id": step.id,
                "label": step.label,
                "prompt_content": prompt_content,
                "fallback": step.fallback,
                "confirm": step.confirm,
            })
        return {
            "name": pipeline.name,
            "label": pipeline.label,
            "source": self.source,
            "steps": steps,
        }

    def save_step_prompt(self, pipeline_name: str, step_id: str, content: str) -> None:
        """保存步骤的 prompt 内容（保存前自动归档旧版本）"""
        prompt_dir = self._get_pipeline_dir() / pipeline_name
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_dir / f"{step_id}.md"
        # 归档旧版本
        if prompt_file.exists():
            archive_prompt(prompt_file, self.prompts_path, note=f"更新 {pipeline_name}/{step_id}")
        prompt_file.write_text(content, encoding="utf-8")

    def save_pipeline_yaml(self, name: str, label: str, steps: list[dict]) -> None:
        """保存管线 YAML 定义（保存前自动归档旧版本）"""
        yaml_path = self._get_pipeline_yaml_path(name)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        # 归档旧版本
        if yaml_path.exists():
            archive_prompt(yaml_path, self.prompts_path, note=f"更新 {name} 定义")
        data = {
            "name": name,
            "label": label,
            "steps": [
                {"id": s["id"], "label": s["label"], "prompt": f"pipeline/{name}/{s['id']}", "fallback": s.get("fallback")}
                for s in steps
            ],
        }
        yaml_path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
