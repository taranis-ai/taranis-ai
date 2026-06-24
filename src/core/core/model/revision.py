from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story
    from core.model.user import User


def _increment_parent_revision(item: "Story | ReportItem") -> int:
    db.session.flush()

    table = getattr(item, "__table__")
    next_revision = db.session.execute(
        table.update().where(table.c.id == item.id).values(revision=func.coalesce(table.c.revision, 0) + 1).returning(table.c.revision)
    ).scalar_one()
    item.revision = next_revision
    return next_revision


class StoryRevision(BaseModel):
    __tablename__ = "story_revision"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    story_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("story.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = db.Column(db.Integer, nullable=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    created_by_id: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped["User | None"] = relationship("User")
    note: Mapped[str | None] = db.Column(db.Text)
    data: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)

    __table_args__ = (UniqueConstraint("story_id", "revision", name="uq_story_revision_story_rev"),)

    @staticmethod
    def snapshot_story(story: "Story") -> dict[str, Any]:
        return story.to_detail_dict()

    @classmethod
    def create_from_story(cls, story: "Story", created_by_id: str | None = None, note: str | None = None) -> "StoryRevision":
        next_revision = _increment_parent_revision(story)
        revision = cls()
        revision.story_id = story.id
        revision.revision = next_revision
        revision.created_by_id = created_by_id
        revision.note = note
        revision.data = cls.snapshot_story(story)
        db.session.add(revision)
        return revision


class ReportRevision(BaseModel):
    __tablename__ = "report_revision"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    report_item_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("report_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision: Mapped[int] = db.Column(db.Integer, nullable=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    created_by_id: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped["User | None"] = relationship("User")
    note: Mapped[str | None] = db.Column(db.Text)
    data: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)

    __table_args__ = (UniqueConstraint("report_item_id", "revision", name="uq_report_revision_report_rev"),)

    @staticmethod
    def snapshot_report(report: "ReportItem") -> dict[str, Any]:
        return report.to_detail_dict()

    @classmethod
    def create_from_report(cls, report: "ReportItem", created_by_id: str | None = None, note: str | None = None) -> "ReportRevision":
        next_revision = _increment_parent_revision(report)
        revision = cls()
        revision.report_item_id = report.id
        revision.revision = next_revision
        revision.created_by_id = created_by_id
        revision.note = note
        revision.data = cls.snapshot_report(report)
        db.session.add(revision)
        return revision
