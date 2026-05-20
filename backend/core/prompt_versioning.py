"""墨韵 - Prompts 版本管理

修改 prompt 前自动归档旧版本到 prompts/.archive/<timestamp>/。
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)


def archive_prompt(prompt_path: Path, archive_root: Path, note: str = "") -> str | None:
    """归档 prompt 文件的当前版本

    保存 prompt_path 的快照到:
        {archive_root}/.archive/{timestamp}/{prompt_path.relative_to(archive_root)}

    同时写入 .metadata.json 记录修改信息。

    Args:
        prompt_path: prompt 文件或目录的绝对路径
        archive_root: prompts 根目录
        note: 修改说明（可选）

    Returns:
        归档路径的字符串，如果无需归档（文件不存在）则返回 None
    """
    if not prompt_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        rel = prompt_path.relative_to(archive_root)
    except ValueError:
        rel = prompt_path.name

    archive_dir = archive_root / ".archive" / f"{timestamp}_{rel}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    if prompt_path.is_file():
        shutil.copy2(prompt_path, archive_dir / prompt_path.name)
    elif prompt_path.is_dir():
        shutil.copytree(prompt_path, archive_dir / rel, dirs_exist_ok=True)

    # 写入元数据
    metadata = {
        "timestamp": timestamp,
        "source": str(prompt_path),
        "note": note,
        "type": "file" if prompt_path.is_file() else "directory",
    }
    (archive_dir / ".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Prompt 已归档: %s -> %s", prompt_path, archive_dir)
    return str(archive_dir)


def list_archives(archive_root: Path, pipeline_name: str | None = None) -> list[dict]:
    """列出所有归档版本

    Args:
        archive_root: prompts 根目录
        pipeline_name: 可选，筛选特定管线的归档

    Returns:
        按时间倒序排列的归档列表，每项含 timestamp、source、note、path
    """
    archive_dir = archive_root / ".archive"
    if not archive_dir.exists():
        return []

    versions = []
    for entry in sorted(archive_dir.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        meta_file = entry / ".metadata.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {"timestamp": entry.name, "note": "", "type": "unknown"}
        else:
            meta = {"timestamp": entry.name, "note": "", "type": "unknown"}

        meta["path"] = str(entry)
        meta["name"] = entry.name

        if pipeline_name and pipeline_name not in str(entry):
            continue

        versions.append(meta)

    return versions


def restore_archive(archive_path: Path, target_path: Path) -> bool:
    """从归档恢复 prompt 到指定位置

    Args:
        archive_path: 归档目录路径
        target_path: 恢复到目标路径（文件或目录）

    Returns:
        是否成功恢复
    """
    if not archive_path.exists():
        logger.warning("归档路径不存在: %s", archive_path)
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if target_path.is_dir() or archive_path.is_dir():
            # 从归档目录复制内容到目标目录
            for item in archive_path.iterdir():
                if item.name == ".metadata.json":
                    continue
                if item.is_file():
                    shutil.copy2(item, target_path / item.name)
                elif item.is_dir():
                    shutil.copytree(item, target_path / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(archive_path, target_path)

        logger.info("Prompt 已从归档恢复: %s -> %s", archive_path, target_path)
        return True
    except OSError as e:
        logger.error("恢复归档失败: %s", e)
        return False
