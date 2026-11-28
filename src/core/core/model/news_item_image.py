import base64
import hashlib
from datetime import datetime
from io import BytesIO

from models.news_image import MAX_IMAGE_BYTES, MAX_IMAGE_COUNT, MAX_IMAGE_PIXELS, CapturedImage
from PIL import Image
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, deferred, relationship

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.image_match import close_colors, color_signature, same_picture, source_key
from core.model.news_image_blob import NewsImageBlob, NewsItemImageFingerprint


class NewsItemImage(BaseModel):
    __tablename__ = "news_item_image"
    __table_args__ = (db.UniqueConstraint("news_item_id", "digest"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    news_item_id: Mapped[str] = db.Column(db.ForeignKey("news_item.id", ondelete="CASCADE"), nullable=False)
    source_url: Mapped[str] = db.Column(db.Text, nullable=False)
    captured: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    mime_type: Mapped[str] = db.Column(db.String, nullable=False)
    digest: Mapped[str] = db.Column(db.String(64), nullable=False)
    description: Mapped[str | None] = db.Column(db.Text)
    inline_data: Mapped[bytes] = deferred(db.Column("data", db.LargeBinary, nullable=False))
    fingerprint: Mapped[NewsItemImageFingerprint | None] = relationship(cascade="all, delete-orphan", single_parent=True)

    @classmethod
    def from_capture(cls, capture: CapturedImage):
        data = base64.b64decode(capture.data, validate=True)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("Image too large")
        digest = hashlib.sha256(data).hexdigest()
        blob = db.session.get(NewsImageBlob, digest)
        if blob is None:
            with Image.open(BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS or getattr(image, "is_animated", False):
                    raise ValueError("Unsupported image dimensions or animation")
                assert image.format is not None
                mime = Image.MIME[image.format]
                image.load()
                colors = color_signature(image)
        else:
            mime, colors = blob.mime_type, blob.colors
        record = cls()
        record.description = capture.alt_text
        record.source_url = str(capture.source_url)
        record.mime_type = mime
        record.digest = digest
        record.inline_data = data
        fingerprint = NewsItemImageFingerprint(colors)
        if blob is not None:
            fingerprint.blob_digest = digest
        record.fingerprint = fingerprint
        return record

    def matches(self, candidate: "NewsItemImage") -> bool:
        if self.digest == candidate.digest:
            return True
        fingerprint = self.fingerprint
        if fingerprint is None:
            # Only fingerprint a pre-existing capture when its item receives another candidate.
            try:
                with Image.open(BytesIO(self.inline_data), formats=("JPEG", "PNG", "WEBP")) as image:
                    fingerprint = self.fingerprint = NewsItemImageFingerprint(color_signature(image))
            except (ValueError, OSError, EOFError, SyntaxError, IndexError, Image.DecompressionBombError):
                return False
        assert candidate.fingerprint is not None
        if not close_colors(fingerprint.colors, candidate.fingerprint.colors):
            return False
        return same_picture(candidate.inline_data, self.data, fingerprint.colors, same_article=True)

    @property
    def data(self) -> bytes:
        if self.id and self.fingerprint and self.fingerprint.blob_digest:
            return db.session.scalars(db.select(NewsImageBlob.data).where(NewsImageBlob.digest == self.fingerprint.blob_digest)).one()
        return self.inline_data

    @staticmethod
    def share_blobs(images: list["NewsItemImage"], source_id: str) -> None:
        """Resolve exact and source-local matches, then pin the chosen blobs until the attachments commit."""
        selected = []
        for image in images:
            fingerprint = image.fingerprint
            assert fingerprint is not None
            digest = image.digest
            colors = fingerprint.colors
            data = image.inline_data
            key = source_key(colors)
            if fingerprint.blob_digest is None and (blob := NewsImageBlob.source_match(source_id, key, colors, data)):
                digest, data, colors = blob.digest, blob.data, blob.colors
                image.mime_type = blob.mime_type
                key = source_key(colors)
            fingerprint.colors = colors
            fingerprint.source_id = source_id
            fingerprint.visual_key = key
            fingerprint.blob_digest = digest
            selected.append((digest, image, data))
        for digest, image, data in sorted(selected, key=lambda entry: entry[0]):
            locked = db.select(NewsImageBlob.digest).where(NewsImageBlob.digest == digest).with_for_update(read=True, key_share=True)
            if db.session.scalar(locked) is None:
                insert = pg_insert if db.engine.dialect.name == "postgresql" else sqlite_insert
                assert image.fingerprint is not None
                stmt = insert(NewsImageBlob).values(digest=digest, colors=image.fingerprint.colors, mime_type=image.mime_type, data=data)
                # A concurrent insert can win after the miss. Keep its row locked until our FK is present.
                db.session.execute(stmt.on_conflict_do_update(index_elements=["digest"], set_={"digest": digest}))
            image.inline_data = b""

    def remember_urls(self, duplicate: "NewsItemImage") -> None:
        assert duplicate.fingerprint is not None
        fingerprint = self.fingerprint
        if fingerprint is None:
            fingerprint = self.fingerprint = NewsItemImageFingerprint(duplicate.fingerprint.colors)
        url = duplicate.source_url
        if url != self.source_url and url not in fingerprint.aliases:
            fingerprint.aliases = [*fingerprint.aliases, url][-MAX_IMAGE_COUNT:]

    def to_image_metadata(self):
        return {"id": self.id, "mime_type": self.mime_type, "description": self.description}
