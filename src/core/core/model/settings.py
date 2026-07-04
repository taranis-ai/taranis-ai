from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Mapped

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.role import TLPLevel


class Settings(BaseModel):
    __tablename__ = "settings"

    SINGLETON_KEY = "settings"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    singleton_key: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False, default=SINGLETON_KEY)

    settings: Mapped["dict"] = db.Column(db.JSON)

    def __init__(self, settings: dict | None = None):
        self.id = self.uuid7_str()
        self.singleton_key = self.SINGLETON_KEY
        self.settings = self.with_defaults(settings)

    @classmethod
    def with_defaults(cls, settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
        merged = dict(settings) if isinstance(settings, Mapping) else {}
        merged.setdefault("default_collector_proxy", "")
        merged.setdefault("default_collector_interval", "0 */8 * * *")
        merged.setdefault("default_tlp_level", TLPLevel.CLEAR.value)
        merged.setdefault("default_story_conflict_retention", "200")
        merged.setdefault("default_news_item_conflict_retention", "200")
        merged.setdefault("default_timezone", None)
        return merged

    @classmethod
    def update(cls, data) -> tuple[dict, int]:
        if not isinstance(data, dict):
            return {"error": "Invalid settings payload"}, 400

        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return {"error": "Error updating settings"}, 404

        raw_update_data = data.get("settings", {})
        if not isinstance(raw_update_data, Mapping):
            return {"error": "settings must be a JSON object"}, 400
        try:
            update_data = cls._normalize_update_data(dict(raw_update_data))
        except ValueError:
            return {"error": "Invalid timezone"}, 400

        if update_data:
            logger.debug(f"Settings update data: {update_data}")
            logger.debug(f"Settings before update: {settings.settings}")
            current_settings = cls.with_defaults(settings.settings)
            current_settings.update(update_data)
            settings.settings = current_settings
        db.session.commit()
        logger.debug(f"Settings after update: {settings.settings}")
        return {"message": "Successfully updated settings", "settings": settings.settings}, 200

    @classmethod
    def initialize(cls):
        if settings := cls.get_settings_entry():
            settings.settings = cls.with_defaults(settings.settings)
        else:
            db.session.add(Settings())

        db.session.commit()

    @classmethod
    def get_settings(cls) -> dict:
        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return {}
        return cls.with_defaults(settings.settings)

    @classmethod
    def _normalize_update_data(cls, data: dict) -> dict:
        normalized = dict(data)
        if "default_timezone" in normalized:
            normalized["default_timezone"] = cls._validate_timezone(normalized.get("default_timezone"))
        return normalized

    @staticmethod
    def _validate_timezone(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Invalid timezone: must be a string")
        timezone_name = value.strip()
        if not timezone_name:
            return None
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Invalid timezone: {timezone_name}") from None
        return timezone_name

    @classmethod
    def get_settings_entry(cls) -> "Settings | None":
        return cls.get_first(db.select(cls).filter_by(singleton_key=cls.SINGLETON_KEY))

    @classmethod
    def get(cls, item_id):
        if item_id in (1, "1", cls.SINGLETON_KEY):
            return cls.get_settings_entry()
        return super().get(item_id)
