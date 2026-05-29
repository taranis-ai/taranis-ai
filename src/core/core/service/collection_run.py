from typing import Any

from core.model.collection_run import CollectionRun


class CollectionRunService:
    @classmethod
    def get_statistics_summary(cls, source_id: str | None = None) -> tuple[dict[str, Any], int]:
        return CollectionRun.get_summary(source_id=source_id), 200
