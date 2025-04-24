import uuid
import base64
import contextlib
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Mapped, deferred

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role import TLPLevel


class NewsItemAttribute(BaseModel):
    __tablename__ = "news_item_attribute"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    key: Mapped[str] = db.Column(db.String(), nullable=False, index=True)
    value: Mapped[str] = db.Column(db.String(), nullable=False)
    binary_mime_type: Mapped[str] = db.Column(db.String())
    binary_data: Mapped = deferred(db.Column(db.LargeBinary))
    created: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, key, value, binary_mime_type=None, binary_value=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.key = key
        self.value = value
        if binary_mime_type:
            self.binary_mime_type = binary_mime_type

        with contextlib.suppress(Exception):
            if binary_value:
                self.binary_data = base64.b64decode(binary_value)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("binary_mime_type", None)
        data.pop("binary_data", None)
        return data

    def to_small_dict(self) -> dict[str, Any]:
        return {"key": self.key, "value": self.value}

    @classmethod
    def get_by_key(cls, attributes: list["NewsItemAttribute"], key: str) -> "NewsItemAttribute | None":
        return next((attribute for attribute in attributes if attribute.key == key), None)  # type: ignore

    @property
    def tlp_level(self) -> TLPLevel:
        return TLPLevel(self.value) if self.key == "TLP" else TLPLevel.CLEAR

    @classmethod
    def get_tlp_level(cls, attributes: list["NewsItemAttribute"]) -> TLPLevel | None:
        return TLPLevel(cls.get_by_key(attributes, "TLP"))
