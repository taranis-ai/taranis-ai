"""Shared collector image bytes. The private attachment remains the authorization boundary."""

from models.news_image import MAX_IMAGE_COUNT
from sqlalchemy import DDL, event
from sqlalchemy.orm import Mapped, deferred

from core.managers.db_manager import db
from core.model.image_match import close_colors, same_picture


class NewsImageBlob(db.Model):
    __tablename__ = "news_image_blob"

    digest: Mapped[str] = db.Column(db.String(64), primary_key=True)
    mime_type: Mapped[str] = db.Column(db.String, nullable=False)
    colors: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    data: Mapped[bytes] = deferred(db.Column(db.LargeBinary, nullable=False))

    @classmethod
    def source_match(cls, source_id: str, key: int, colors: bytes, data: bytes) -> "NewsImageBlob | None":
        # One flipped gradient bit is allowed. The covering index starts with the source and hash.
        keys = [key, *(key ^ (1 << bit) for bit in range(49))]
        candidates = (
            db.select(NewsItemImageFingerprint.blob_digest)
            .where(NewsItemImageFingerprint.source_id == source_id, NewsItemImageFingerprint.visual_key.in_(keys))
            .limit(4 * MAX_IMAGE_COUNT)
        )
        for blob in db.session.scalars(db.select(cls).where(cls.digest.in_(candidates)).order_by(cls.digest).limit(MAX_IMAGE_COUNT)):
            if close_colors(colors, blob.colors) and same_picture(data, blob.data, colors, same_article=False):
                return blob
        return None


class NewsItemImageFingerprint(db.Model):
    __tablename__ = "news_item_image_fingerprint"
    __table_args__ = (db.Index("ix_image_source_key_blob", "source_id", "visual_key", "blob_digest"),)

    image_id: Mapped[str] = db.Column(db.ForeignKey("news_item_image.id", ondelete="CASCADE"), primary_key=True)
    blob_digest: Mapped[str | None] = db.Column(db.ForeignKey("news_image_blob.digest"), index=True)
    source_id: Mapped[str | None] = db.Column(db.String(36))
    visual_key: Mapped[int | None] = db.Column(db.BigInteger)
    colors: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    aliases: Mapped[list[str]] = db.Column(db.JSON, nullable=False)

    def __init__(self, colors: bytes):
        self.colors = colors
        self.aliases = []


# Cascades from item/source deletion can bypass the ORM. Serialize last-reference checks with collector inserts.
_delete_orphan = """
    DELETE FROM news_image_blob WHERE digest = OLD.blob_digest
    AND NOT EXISTS (SELECT 1 FROM news_item_image_fingerprint WHERE blob_digest = OLD.blob_digest);
"""
event.listen(
    db.metadata.tables["news_item_image_fingerprint"],
    "after_create",
    DDL(f"""CREATE TRIGGER release_image_blob AFTER DELETE ON news_item_image_fingerprint
        BEGIN {_delete_orphan} END""").execute_if(dialect="sqlite"),
)
event.listen(
    db.metadata.tables["news_item_image_fingerprint"],
    "after_create",
    DDL(f"""CREATE OR REPLACE FUNCTION release_image_blob() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM digest FROM news_image_blob WHERE digest = OLD.blob_digest FOR UPDATE;
            {_delete_orphan}
            RETURN NULL;
        END; $$""").execute_if(dialect="postgresql"),
)
event.listen(
    db.metadata.tables["news_item_image_fingerprint"],
    "after_create",
    DDL("""CREATE TRIGGER release_image_blob AFTER DELETE ON news_item_image_fingerprint
        FOR EACH ROW EXECUTE FUNCTION release_image_blob()""").execute_if(dialect="postgresql"),
)
