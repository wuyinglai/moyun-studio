"""墨韵 - Pipeline YAML 配置校验器

启动时校验 prompts/pipeline/*.yaml 的结构正确性：
- YAML 解析是否成功
- 必填字段是否存在
- step id 是否重复
- prompt 文件是否存在
- fallback / depends_on 是否引用已存在的 step id
- output_mode 是否合法
- 危险 output 路径警告
"""

import logging
import re
from pathlib import Path

import yaml

from backend.schemas.pipeline_config import (
    ALLOWED_OUTPUT_MODES,
    DANGEROUS_OUTPUT_PATTERNS,
    DEPRECATED_OUTPUT_MODES,
    PipelineConfig,
    PipelineValidationError,
    PipelineValidationResult,
    PipelineValidationWarning,
)

logger = logging.getLogger(__name__)

# Jinja2 include 语句的正则
_INCLUDE_PATTERN = re.compile(r"\{%[-\s]+include\s+['\"]([^'\"]+)['\"]\s*[-\s]*%\}")


def validate_pipeline_file(
    path: Path,
    prompts_root: Path | None = None,
) -> PipelineValidationResult:
    """校验单个 pipeline YAML 文件

    Args:
        path: YAML 文件路径
        prompts_root: prompts 根目录，用于校验 prompt 文件是否存在。
                      默认取 path 向上 2 级（pipeline/*.yaml → prompts/）

    Returns:
        PipelineValidationResult
    """
    result = PipelineValidationResult(file=path.name)

    # ── 1. 解析 YAML ────────────────────────────────────────────
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        result.valid = False
        result.errors.append(PipelineValidationError(
            message=f"YAML 解析失败: {e}",
        ))
        return result

    if not isinstance(data, dict):
        result.valid = False
        result.errors.append(PipelineValidationError(
            message="YAML 顶层必须是字典",
        ))
        return result

    # ── 2. Pydantic 结构校验 ────────────────────────────────────
    try:
        config = PipelineConfig(**data)
    except Exception as e:
        result.valid = False
        result.errors.append(PipelineValidationError(
            message=f"结构校验失败: {e}",
        ))
        return result

    # ── 3. step id 唯一性 ───────────────────────────────────────
    seen_ids: set[str] = set()
    for step in config.steps:
        if step.id in seen_ids:
            result.valid = False
            result.errors.append(PipelineValidationError(
                step_id=step.id,
                field="id",
                message=f"step id 重复: {step.id}",
            ))
        seen_ids.add(step.id)

    # ── 4. fallback 引用校验 ────────────────────────────────────
    for step in config.steps:
        if step.fallback is not None and step.fallback not in seen_ids:
            result.valid = False
            result.errors.append(PipelineValidationError(
                step_id=step.id,
                field="fallback",
                message=f"fallback 引用了不存在的 step id: {step.fallback}",
            ))

    # ── 5. depends_on 引用校验 ──────────────────────────────────
    for step in config.steps:
        if step.depends_on:
            for dep_id in step.depends_on:
                if dep_id not in seen_ids:
                    result.valid = False
                    result.errors.append(PipelineValidationError(
                        step_id=step.id,
                        field="depends_on",
                        message=f"depends_on 引用了不存在的 step id: {dep_id}",
                    ))

    # ── 6. prompt 文件存在性 ────────────────────────────────────
    if prompts_root is None:
        # 默认: pipeline/*.yaml → 向上 2 级到 prompts/
        prompts_root = path.parent.parent

    for step in config.steps:
        prompt_path = prompts_root / f"{step.prompt}.md"
        if not prompt_path.exists():
            result.valid = False
            result.errors.append(PipelineValidationError(
                step_id=step.id,
                field="prompt",
                message=f"prompt 文件不存在: {step.prompt}.md (查找路径: {prompt_path})",
            ))
        else:
            # 尝试检测 include block 是否存在
            _check_includes(prompt_path, prompts_root, step.id, result)

    # ── 7. output_mode 校验 ─────────────────────────────────────
    for step in config.steps:
        if step.output_mode is not None:
            if step.output_mode not in ALLOWED_OUTPUT_MODES:
                result.valid = False
                result.errors.append(PipelineValidationError(
                    step_id=step.id,
                    field="output_mode",
                    message=f"output_mode 非法: {step.output_mode}，允许值: {sorted(ALLOWED_OUTPUT_MODES)}",
                ))
            elif step.output_mode in DEPRECATED_OUTPUT_MODES:
                result.warnings.append(PipelineValidationWarning(
                    step_id=step.id,
                    field="output_mode",
                    message=f"output_mode='{step.output_mode}' 已不推荐，建议使用 'candidate' 或 'write_scene'",
                ))

    # ── 8. 危险 output 路径警告 ─────────────────────────────────
    for step in config.steps:
        if step.output:
            for pattern in DANGEROUS_OUTPUT_PATTERNS:
                if pattern in step.output:
                    result.warnings.append(PipelineValidationWarning(
                        step_id=step.id,
                        field="output",
                        message=f"output 路径包含危险目标 '{pattern}'，建议使用候选稿机制保护",
                    ))
                    break  # 每个步骤只报一次

    # ── 9. name 与文件名一致性警告 ──────────────────────────────
    expected_name = path.stem
    if config.name != expected_name:
        result.warnings.append(PipelineValidationWarning(
            field="name",
            message=f"pipeline name='{config.name}' 与文件名 '{expected_name}.yaml' 不一致",
        ))

    return result


def _check_includes(
    prompt_path: Path,
    prompts_root: Path,
    step_id: str,
    result: PipelineValidationResult,
) -> None:
    """检测 prompt 文件中的 {% include %} 引用是否存在

    仅做单层检测，不递归。找不到时作为 warning 而非 error，
    因为 include 路径可能依赖 Jinja2 的搜索路径机制。
    """
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError:
        return

    for match in _INCLUDE_PATTERN.finditer(content):
        include_ref = match.group(1)
        # include 路径相对于模板目录
        include_path = prompts_root / include_ref
        if not include_path.exists():
            result.warnings.append(PipelineValidationWarning(
                step_id=step_id,
                field="prompt",
                message=f"include 引用的文件可能不存在: {include_ref} (查找路径: {include_path})",
            ))


def validate_all_pipelines(
    prompts_root: Path,
    pipeline_subdir: str = "pipeline",
) -> list[PipelineValidationResult]:
    """校验所有 pipeline YAML 文件

    Args:
        prompts_root: prompts 根目录
        pipeline_subdir: pipeline 子目录名

    Returns:
        校验结果列表
    """
    pipeline_dir = prompts_root / pipeline_subdir
    if not pipeline_dir.exists():
        logger.warning("Pipeline 目录不存在: %s", pipeline_dir)
        return []

    results: list[PipelineValidationResult] = []
    for yaml_file in sorted(pipeline_dir.glob("*.yaml")):
        r = validate_pipeline_file(yaml_file, prompts_root)
        results.append(r)

        if r.errors:
            for err in r.errors:
                step_info = f" (step={err.step_id})" if err.step_id else ""
                logger.error(
                    "Pipeline 校验错误 [%s]%s: %s",
                    r.file, step_info, err.message,
                )
        if r.warnings:
            for warn in r.warnings:
                step_info = f" (step={warn.step_id})" if warn.step_id else ""
                logger.warning(
                    "Pipeline 校验警告 [%s]%s: %s",
                    r.file, step_info, warn.message,
                )

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.valid)
    error_count = sum(len(r.errors) for r in results)
    warning_count = sum(len(r.warnings) for r in results)
    logger.info(
        "Pipeline 校验完成: %d/%d 通过, %d 错误, %d 警告",
        passed, total, error_count, warning_count,
    )

    return results
