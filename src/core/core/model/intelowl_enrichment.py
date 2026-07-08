from datetime import datetime, timezone
from typing import Any

from models.cti import CTIEnrichment, normalize_ioc_type, normalize_ioc_value
from sqlalchemy import Index, UniqueConstraint, tuple_
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class IntelOwlEnrichment(BaseModel):
    __tablename__ = "intelowl_enrichment"
    __table_args__ = (
        UniqueConstraint("ioc_type", "value", name="uq_intelowl_enrichment_ioc"),
        Index("ix_intelowl_enrichment_type_value", "ioc_type", "value"),
    )

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    ioc_type: Mapped[str] = db.Column(db.String(32), nullable=False)
    value: Mapped[str] = db.Column(db.String(2048), nullable=False)
    status: Mapped[str | None] = db.Column(db.String(64), nullable=True)
    job_id: Mapped[str | None] = db.Column(db.String(255), nullable=True)
    job_url: Mapped[str | None] = db.Column(db.String(2048), nullable=True)
    analyzers: Mapped[list[dict[str, Any]]] = db.Column(db.JSON, nullable=False, default=list)
    errors: Mapped[list[dict[str, Any]]] = db.Column(db.JSON, nullable=False, default=list)
    submitted_at: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, onupdate=BaseModel.utcnow, nullable=False)

    @classmethod
    def get_by_ioc(cls, raw_type: str, raw_value: str) -> "IntelOwlEnrichment | None":
        if not (ioc_type := normalize_ioc_type(raw_type)):
            return None
        value = normalize_ioc_value(raw_value, ioc_type)
        if not value:
            return None
        return cls.get_first(db.select(cls).where(cls.ioc_type == ioc_type, cls.value == value))

    @classmethod
    def get_for_iocs(cls, iocs: set[tuple[str, str]]) -> dict[tuple[str, str], "IntelOwlEnrichment"]:
        if not iocs:
            return {}
        rows = db.session.execute(db.select(cls).where(tuple_(cls.ioc_type, cls.value).in_(sorted(iocs)))).scalars()
        return {(row.ioc_type, row.value): row for row in rows}

    @classmethod
    def upsert_many(cls, enrichments: list[dict[str, Any]]) -> None:
        changed = False
        for payload in enrichments:
            if not (ioc_type := normalize_ioc_type(payload.get("type") or payload.get("ioc_type"))):
                continue
            value = normalize_ioc_value(str(payload.get("value") or ""), ioc_type)
            if not value:
                continue
            row = cls.get_by_ioc(ioc_type, value)
            if row is None:
                row = cls()
                row.ioc_type = ioc_type
                row.value = value
                db.session.add(row)
            row.status = str(payload.get("status") or row.status or "")
            row.job_id = str(payload.get("job_id") or row.job_id or "")
            row.job_url = str(payload.get("url") or payload.get("job_url") or row.job_url or "")
            row.analyzers = cls._dict_list(payload.get("analyzers")) or row.analyzers or []
            row.errors = cls._dict_list(payload.get("errors")) or row.errors or []
            row.submitted_at = cls._parse_datetime(payload.get("submitted_at")) or row.submitted_at
            row.completed_at = cls._parse_datetime(payload.get("completed_at")) or row.completed_at
            row.updated_at = BaseModel.utcnow()
            changed = True
        if changed:
            db.session.commit()

    def to_cti_model(self) -> CTIEnrichment:
        if not (ioc_type := normalize_ioc_type(self.ioc_type)):
            raise ValueError(f"Invalid IntelOwl IOC type: {self.ioc_type}")
        return CTIEnrichment(
            ioc_type=ioc_type,
            value=self.value,
            status=self.status,
            job_id=self.job_id,
            job_url=self.job_url,
            analyzers=self.analyzers or [],
            errors=self.errors or [],
            submitted_at=self.submitted_at,
            completed_at=self.completed_at,
            updated_at=self.updated_at,
        )

    @staticmethod
    def _dict_list(value: Any) -> list[dict[str, Any]] | None:
        if not isinstance(value, list):
            return None
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo else value
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return None
            return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
        return None
