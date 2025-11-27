from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import BaseModel

if TYPE_CHECKING:
    from core.model.story import Story
    from core.model.report_item import ReportItem
    from core.model.user import User


def _next_revision_number(query) -> int:
    last_revision = db.session.execute(query).scalar()
    return (last_revision or 0) + 1


class StoryRevision(BaseModel):
    __tablename__ = "story_revision"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = db.Column(db.Integer, nullable=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    created_by_id: Mapped[int | None] = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped["User | None"] = relationship("User")
    note: Mapped[str | None] = db.Column(db.Text)
    data: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)

    __table_args__ = (UniqueConstraint("story_id", "revision", name="uq_story_revision_story_rev"),)

    @staticmethod
    def snapshot_story(story: "Story") -> dict[str, Any]:
        return story.to_detail_dict()

    @classmethod
    def create_from_story(cls, story: "Story", created_by_id: int | None = None, note: str | None = None) -> "StoryRevision":
        next_revision = _next_revision_number(db.select(cls.revision).filter(cls.story_id == story.id).order_by(cls.revision.desc()).limit(1))
        revision = cls(
            story_id=story.id,
            revision=next_revision,
            created_by_id=created_by_id,
            note=note,
            data=cls.snapshot_story(story),
        )
        db.session.add(revision)
        return revision


class ReportRevision(BaseModel):
    __tablename__ = "report_revision"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    report_item_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = db.Column(db.Integer, nullable=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    created_by_id: Mapped[int | None] = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped["User | None"] = relationship("User")
    note: Mapped[str | None] = db.Column(db.Text)
    data: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)

    __table_args__ = (UniqueConstraint("report_item_id", "revision", name="uq_report_revision_report_rev"),)

    @staticmethod
    def snapshot_report(report: "ReportItem") -> dict[str, Any]:
        return report.to_detail_dict()

    @classmethod
    def create_from_report(cls, report: "ReportItem", created_by_id: int | None = None, note: str | None = None) -> "ReportRevision":
        next_revision = _next_revision_number(
            db.select(cls.revision).filter(cls.report_item_id == report.id).order_by(cls.revision.desc()).limit(1)
        )
        revision = cls(
            report_item_id=report.id,
            revision=next_revision,
            created_by_id=created_by_id,
            note=note,
            data=cls.snapshot_report(report),
        )
        db.session.add(revision)
        return revision
