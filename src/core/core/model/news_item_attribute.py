import uuid
import base64
import contextlib
from datetime import datetime
from typing import Any
from sqlalchemy import orm

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role import TLPLevel


class NewsItemAttribute(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    key: Any = db.Column(db.String(), nullable=False)
    value: Any = db.Column(db.String(), nullable=False)
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, key, value, binary_mime_type=None, binary_value=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type

        with contextlib.suppress(Exception):
            if binary_value:
                self.binary_data = base64.b64decode(binary_value)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("binary_mime_type", None)
        data.pop("binary_data", None)
        return data

    @classmethod
    def get_by_key(cls, attributes: list["NewsItemAttribute"], key: str) -> "NewsItemAttribute | None":
        return next((attribute for attribute in attributes if attribute.key == key), None)

    @classmethod
    def set_or_update(cls, attributes: list["NewsItemAttribute"], key: str, value: str) -> list["NewsItemAttribute"]:
        if not (attribute := cls.get_by_key(attributes, key)):
            attributes.append(cls(key=key, value=value))
        else:
            attribute.value = value
        return attributes

    @classmethod
    def get_tlp_level(cls, attributes: list["NewsItemAttribute"]) -> TLPLevel | None:
        return TLPLevel(cls.get_by_key(attributes, "TLP"))
