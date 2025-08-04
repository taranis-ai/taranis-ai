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

    @classmethod
    def parse_attributes(cls, tags: list | dict) -> dict[str, "NewsItemAttribute"]:
        if isinstance(tags, dict):
            return cls._parse_dict_attributes(tags)

        return cls._parse_list_attributes(tags)

    @classmethod
    def _parse_dict_attributes(cls, attributes: dict) -> dict[str, "NewsItemAttribute"]:
        """Parse tags from dict format - handles both old and new formats:
        - Old: {"APT75": "UNKNOWN"}
        - New: {"APT75": {"key": "APT75", "value": "UNKNOWN"}}
        """
        parsed_tags = {}

        for attr_key, attr_value in attributes.items():
            if isinstance(attr_value, dict):
                key = attr_value.get("key", attr_key)
                value = attr_value.get("value", "")
            elif isinstance(attr_value, str):
                key = attr_key
                value = attr_value
            else:
                key = attr_key
                value = ""

            parsed_tags[key] = NewsItemAttribute(key=key, value=value)

        return parsed_tags

    @classmethod
    def _parse_list_attributes(cls, attributes: list) -> dict[str, "NewsItemAttribute"]:
        dict_attributes = {attr["key"]: attr for attr in attributes if isinstance(attr, dict) and "key" in attr}
        return cls._parse_dict_attributes(dict_attributes)

    @classmethod
    def unify_attributes_to_old_format(cls, attributes: list | dict) -> list[dict[str, str]]:
        """Unify attributes to a list of dicts with 'key' and 'value' keys.
        This serves for the __init__ function of NewsItemAttribute
        """
        if isinstance(attributes, dict):
            attributes = cls._parse_dict_attributes(attributes)
        elif isinstance(attributes, list):
            attributes = cls._parse_list_attributes(attributes)

        return [{"key": attr.key, "value": attr.value} for attr in attributes.values()]
