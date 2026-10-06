"""Component rules, article evidence, and resumable historical matching runs."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.asset_sbom import AssetSbomComponent
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.news_item import NewsItem


class AssetTrigger(BaseModel):
    __tablename__ = "asset_trigger"
    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    component_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_component.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component: Mapped[AssetSbomComponent] = relationship()
    phrase: Mapped[str] = db.Column(db.String(200), nullable=False)
    context: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    sources: Mapped[list[str]] = db.Column(db.JSON, nullable=False)
    suggestion: Mapped[str | None] = db.Column(db.String(200))
    enabled: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, index=True)
    analyst_edited: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("component_id", "suggestion"),)

    def __init__(self, component_id: str, phrase: str, context: list[str], sources: list[str], suggestion: str | None = None, enabled=False):
        self.component_id = component_id
        self.phrase = phrase
        self.context = context
        self.sources = sources
        self.suggestion = suggestion
        self.enabled = enabled


class AssetArticleMatch(BaseModel):
    __tablename__ = "asset_article_match"
    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    trigger_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_trigger.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger: Mapped[AssetTrigger] = relationship()
    news_item_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    news_item: Mapped[NewsItem] = relationship()
    evidence: Mapped[list[dict[str, Any]]] = db.Column(db.JSON, nullable=False)
    __table_args__ = (db.UniqueConstraint("trigger_id", "news_item_id"),)

    def __init__(self, trigger_id: str, news_item_id: str, evidence: list[dict[str, Any]]):
        self.trigger_id = trigger_id
        self.news_item_id = news_item_id
        self.evidence = evidence


class AssetMatchRun(BaseModel):
    __tablename__ = "asset_match_run"
    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    asset_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)
    days: Mapped[int] = db.Column(db.Integer, nullable=False)
    cursor: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), nullable=False, default="")
    status: Mapped[str] = db.Column(db.String(20), nullable=False, default="QUEUED")
    processed: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    error: Mapped[str] = db.Column(db.String(255), nullable=False, default="")

    def __init__(self, asset_id: str, user_id: str, days: int):
        self.asset_id = asset_id
        self.user_id = user_id
        self.days = days
