import base64
import hashlib
from datetime import datetime
from io import BytesIO

from models.news_image import MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS, CapturedImage
from PIL import Image
from sqlalchemy.orm import Mapped, deferred

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


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
    data: Mapped[bytes] = deferred(db.Column(db.LargeBinary, nullable=False))

    @classmethod
    def from_capture(cls, capture: CapturedImage):
        data = base64.b64decode(capture.data, validate=True)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("Image too large")
        with Image.open(BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS or getattr(image, "is_animated", False):
                raise ValueError("Unsupported image dimensions or animation")
            assert image.format is not None
            mime = Image.MIME[image.format]
            image.load()
        record = cls()
        record.source_url = str(capture.source_url)
        record.mime_type = mime
        record.digest = hashlib.sha256(data).hexdigest()
        record.data = data
        return record

    def to_image_metadata(self):
        return {"id": self.id, "mime_type": self.mime_type, "description": self.description}
