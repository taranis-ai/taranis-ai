from datetime import datetime

from sqlalchemy import CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.user import User


class Comment(BaseModel):
    __tablename__ = "comment"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN story_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN report_item_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN product_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_comment_one_parent",
        ),
        Index("ix_comment_story_time", "story_id", "created_at", "id"),
        Index("ix_comment_report_time", "report_item_id", "created_at", "id"),
        Index("ix_comment_product_time", "product_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    body: Mapped[str] = mapped_column(Text)
    # Legacy story comments have no reliable original timestamp.
    created_at: Mapped[datetime | None] = mapped_column()
    edited_at: Mapped[datetime | None] = mapped_column()
    author_id: Mapped[str | None] = mapped_column(String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    author: Mapped[User | None] = relationship()
    story_id: Mapped[str | None] = mapped_column(String(UUID_STR_LENGTH), db.ForeignKey("story.id", ondelete="CASCADE"))
    report_item_id: Mapped[str | None] = mapped_column(String(UUID_STR_LENGTH), db.ForeignKey("report_item.id", ondelete="CASCADE"))
    product_id: Mapped[str | None] = mapped_column(String(UUID_STR_LENGTH), db.ForeignKey("product.id", ondelete="CASCADE"))
