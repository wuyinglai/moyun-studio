"""Project-level continuity anchor storage and prompt helpers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from backend.core.exceptions import MoyunFileNotFoundError, ValidationError
from backend.core.file_ops import FileService
from backend.schemas.continuity_anchor import (
    ContinuityAnchor,
    ContinuityAnchorMetadata,
    ContinuityAnchorsDocument,
)


class ContinuityAnchorService:
    """Read, write, filter, and summarize continuity anchors."""

    ANCHORS_FILE = "continuity-anchors.json"

    def __init__(self, file_service: FileService):
        self.file_service = file_service

    def _path(self, project_id: str) -> str:
        return f"{project_id}/{self.ANCHORS_FILE}".replace("\\", "/").strip("/")

    async def read_document(self, project_id: str) -> ContinuityAnchorsDocument:
        try:
            read_result = await self.file_service.read_file(self._path(project_id))
            content = read_result[0] if isinstance(read_result, tuple) else str(read_result)
        except (MoyunFileNotFoundError, FileNotFoundError):
            return ContinuityAnchorsDocument()
        try:
            raw = json.loads(content or "{}")
            return ContinuityAnchorsDocument.model_validate(raw)
        except (json.JSONDecodeError, PydanticValidationError) as exc:
            raise ValidationError("Invalid continuity anchors document") from exc

    async def write_document(
        self,
        project_id: str,
        document: ContinuityAnchorsDocument,
    ) -> ContinuityAnchorsDocument:
        normalized = ContinuityAnchorsDocument.model_validate(document.model_dump(mode="json"))
        await self.file_service.write_file(
            self._path(project_id),
            normalized.model_dump_json(indent=2),
        )
        return normalized

    async def list_active(self, project_id: str) -> list[ContinuityAnchor]:
        document = await self.read_document(project_id)
        return self.active_anchors(document.anchors)

    @staticmethod
    def active_anchors(anchors: list[ContinuityAnchor]) -> list[ContinuityAnchor]:
        priority_order = {"high": 0, "normal": 1, "low": 2}
        active = [anchor for anchor in anchors if anchor.status.value == "active"]
        return sorted(active, key=lambda item: (priority_order.get(item.priority.value, 9), item.updated_at, item.id))

    @staticmethod
    def prompt_items(anchors: list[ContinuityAnchor]) -> list[dict[str, str]]:
        return [
            {
                "id": anchor.id,
                "type": anchor.type.value,
                "title": anchor.title,
                "content": anchor.content,
                "scope": anchor.scope.value,
                "priority": anchor.priority.value,
            }
            for anchor in anchors
        ]

    @staticmethod
    def metadata(anchors: list[ContinuityAnchor]) -> dict[str, Any]:
        if not anchors:
            return ContinuityAnchorMetadata(enabled=False).model_dump(mode="json")
        types: dict[str, int] = {}
        for anchor in anchors:
            types[anchor.type.value] = types.get(anchor.type.value, 0) + 1
        return ContinuityAnchorMetadata(
            enabled=True,
            used_count=len(anchors),
            anchor_ids=[anchor.id for anchor in anchors],
            types=types,
        ).model_dump(mode="json")
