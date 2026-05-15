"""墨韵 - 角色管理服务

职责：
- 角色档案的 CRUD
- 角色文件的读取/写入
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.config import Settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class CharacterService:
    """角色服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.projects_path = settings.projects_path

    # ─── 路径辅助 ────────────────────────────────────────

    def _characters_dir(self, project_dir: Path) -> Path:
        return project_dir / "characters"

    def _ensure_characters_dir(self, project_dir: Path) -> Path:
        cd = self._characters_dir(project_dir)
        cd.mkdir(parents=True, exist_ok=True)
        return cd

    def _character_file(self, project_dir: Path, character_id: str) -> Path:
        return self._characters_dir(project_dir) / f"{character_id}.json"

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_path / project_id

    # ─── 数据读写 ────────────────────────────────────────

    def _load_character(self, project_dir: Path, character_id: str) -> dict | None:
        cf = self._character_file(project_dir, character_id)
        if not cf.exists():
            return None
        return json.loads(cf.read_text(encoding="utf-8"))

    def _save_character(self, project_dir: Path, character: dict) -> None:
        cf = self._character_file(project_dir, character["character_id"])
        cf.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    # ─── 业务方法 ────────────────────────────────────────

    def list_characters(self, project_id: str) -> list[dict]:
        """获取项目角色列表，返回原始 dict 列表"""
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        char_dir = self._characters_dir(project_dir)
        if not char_dir.exists():
            return []

        characters: list[dict] = []
        for cf in char_dir.glob("*.json"):
            data = json.loads(cf.read_text(encoding="utf-8"))
            characters.append(data)

        characters.sort(key=lambda c: c.get("name", ""))
        return characters

    def get_character(self, project_id: str, character_id: str) -> dict:
        """获取角色详情"""
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        data = self._load_character(project_dir, character_id)
        if data is None:
            raise ResourceNotFoundError(resource="character", identifier=character_id)
        return data

    def create_character(self, project_id: str, req) -> dict:
        """创建新角色"""
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        self._ensure_characters_dir(project_dir)

        character_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        character = {
            "character_id": character_id,
            "name": req.name,
            "role": req.role,
            "age": req.age,
            "appearance": req.appearance,
            "personality": req.personality,
            "background": req.background,
            "abilities": req.abilities,
            "relationships": req.relationships,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        self._save_character(project_dir, character)
        return character

    def update_character(self, project_id: str, character_id: str, req) -> dict:
        """更新角色信息"""
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        data = self._load_character(project_dir, character_id)
        if data is None:
            raise ResourceNotFoundError(resource="character", identifier=character_id)

        for field in ["name", "role", "age", "appearance", "personality", "background", "abilities", "relationships"]:
            value = getattr(req, field, None)
            if value is not None:
                data[field] = value

        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_character(project_dir, data)
        return data

    def deactivate_character(self, project_id: str, character_id: str) -> dict:
        """将角色标记为 inactive"""
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        data = self._load_character(project_dir, character_id)
        if data is None:
            raise ResourceNotFoundError(resource="character", identifier=character_id)

        data["status"] = "inactive"
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_character(project_dir, data)
        return data
