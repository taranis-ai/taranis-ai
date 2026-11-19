from datetime import datetime

from sqlalchemy.orm import Mapped, deferred, relationship

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.news_item import NewsItem
from core.model.osint_source import OSINTSource


class SocialPost(BaseModel):
    __tablename__ = "social_post"
    __table_args__ = (db.UniqueConstraint("source_id", "key"), db.Index("ix_social_thread", "source_id", "thread", "activity"))
    id: Mapped[str] = db.Column(db.String(36), primary_key=True, default=BaseModel.uuid7_str)
    source_id: Mapped[str] = db.Column(db.ForeignKey("osint_source.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[OSINTSource] = relationship()
    key: Mapped[str] = db.Column(db.String(500), nullable=False)
    thread: Mapped[str] = db.Column(db.String(500), nullable=False)
    parent: Mapped[str] = db.Column(db.String(500), nullable=False)
    platform: Mapped[str] = db.Column(db.String(16), nullable=False)
    title: Mapped[str] = db.Column(db.Text, nullable=False)
    body: Mapped[str] = db.Column(db.Text, nullable=False)
    author: Mapped[str] = db.Column(db.Text, nullable=False)
    boosted_by: Mapped[str] = db.Column(db.Text, nullable=False)
    warning: Mapped[str] = db.Column(db.Text, nullable=False)
    url: Mapped[str] = db.Column(db.Text, nullable=False)
    published: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    activity: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    checked: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    item_id: Mapped[str | None] = db.Column(db.ForeignKey("news_item.id", ondelete="SET NULL"), unique=True)
    item: Mapped[NewsItem | None] = relationship()
    images: Mapped[list["SocialImage"]] = relationship(cascade="all, delete-orphan", order_by="SocialImage.position", back_populates="post")

    def __init__(self, source: OSINTSource, key: str, platform: str):
        self.source = source
        self.key = key
        self.platform = platform


class SocialImage(BaseModel):
    __tablename__ = "social_image"
    id: Mapped[str] = db.Column(db.String(36), primary_key=True, default=BaseModel.uuid7_str)
    post_id: Mapped[str] = db.Column(db.ForeignKey("social_post.id", ondelete="CASCADE"), index=True, nullable=False)
    post: Mapped[SocialPost] = relationship(back_populates="images")
    key: Mapped[str] = db.Column(db.Text, nullable=False)
    position: Mapped[int] = db.Column(db.Integer, nullable=False)
    alt: Mapped[str] = db.Column(db.Text, nullable=False)
    mime: Mapped[str | None] = db.Column(db.String(30))
    original: Mapped[bytes | None] = deferred(db.Column(db.LargeBinary))
    thumbnail: Mapped[bytes | None] = deferred(db.Column(db.LargeBinary))

    def __init__(self, key: str, position: int, alt: str):
        self.key = key
        self.position = position
        self.alt = alt


class SocialBeat(BaseModel):
    __tablename__ = "social_beat"
    __table_args__ = (db.UniqueConstraint("user_id", "name"),)
    id: Mapped[str] = db.Column(db.String(36), primary_key=True, default=BaseModel.uuid7_str)
    user_id: Mapped[str] = db.Column(db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = db.Column(db.String(100), nullable=False)
    filters: Mapped[dict] = db.Column(db.JSON, nullable=False)

    def __init__(self, user_id: str, name: str):
        self.user_id = user_id
        self.name = name


class SocialFigure(BaseModel):
    __tablename__ = "social_figure"
    report_id: Mapped[str] = db.Column(db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    image_id: Mapped[str] = db.Column(db.ForeignKey("social_image.id", ondelete="CASCADE"), primary_key=True)
    image: Mapped[SocialImage] = relationship()
    position: Mapped[int] = db.Column(db.Integer, nullable=False)
    caption: Mapped[str] = db.Column(db.Text, nullable=False)
    alt: Mapped[str] = db.Column(db.Text, nullable=False)

    def __init__(self, report_id: str, image_id: str, position: int, caption: str, alt: str):
        self.report_id = report_id
        self.image_id = image_id
        self.position = position
        self.caption = caption
        self.alt = alt


class SocialRenderImage(BaseModel):
    """Dependencies of generated output, including older still-published copies."""

    __tablename__ = "social_render_image"
    product_id: Mapped[str] = db.Column(db.ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    image_id: Mapped[str] = db.Column(db.ForeignKey("social_image.id", ondelete="CASCADE"), primary_key=True)

    def __init__(self, product_id: str, image_id: str):
        self.product_id = product_id
        self.image_id = image_id
