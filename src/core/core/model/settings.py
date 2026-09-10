from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Mapped

from core.config import Config
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
        values = dict(settings) if settings is not None else {}
        self._validate_chat_settings(values)
        self.settings = self.with_defaults(values)

    @classmethod
    def with_defaults(cls, settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(settings) if isinstance(settings, Mapping) else {}
        merged.setdefault("default_collector_proxy", "")
        merged.setdefault("default_collector_interval", "0 */8 * * *")
        merged.setdefault("rss_collector_max_entries", 42)
        merged.setdefault("default_bot_lookback_days", 7)
        merged.setdefault("default_tlp_level", TLPLevel.CLEAR.value)
        merged.setdefault("default_story_conflict_retention", "200")
        merged.setdefault("default_news_item_conflict_retention", "200")
        merged.setdefault("default_timezone", None)
        merged.setdefault("onboarding_enabled", True)
        merged.setdefault("chat_llm_base_url", "")
        merged.setdefault("chat_llm_api_key", "")
        merged.setdefault("chat_llm_model", "")
        merged.setdefault("chat_llm_timeout", 120)
        merged.setdefault("chat_max_stories", 5)
        return merged

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        public_settings = self.with_defaults(self.settings)
        public_settings["chat_llm_api_key_configured"] = bool(public_settings.pop("chat_llm_api_key", ""))
        data["settings"] = public_settings
        return data

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
        except (TypeError, ValueError):
            return {"error": "Invalid timezone"}, 400
        if "default_bot_lookback_days" in update_data:
            try:
                update_data["default_bot_lookback_days"] = cls._validate_non_negative_int(update_data["default_bot_lookback_days"])
            except (TypeError, ValueError):
                return {"error": "Invalid bot lookback setting"}, 400
        if "rss_collector_max_entries" in update_data:
            try:
                update_data["rss_collector_max_entries"] = cls._validate_non_negative_int(update_data["rss_collector_max_entries"])
                if update_data["rss_collector_max_entries"] == 0:
                    raise ValueError
            except (TypeError, ValueError):
                return {"error": "Invalid RSS collector entry limit"}, 400
        if "onboarding_enabled" in update_data:
            try:
                update_data["onboarding_enabled"] = cls._validate_bool(update_data["onboarding_enabled"])
            except ValueError:
                return {"error": "Invalid onboarding setting"}, 400

        try:
            cls._validate_chat_settings(update_data)
        except (TypeError, ValueError):
            return {"error": "Invalid chat settings"}, 400

        if update_data:
            current_settings = cls.with_defaults(settings.settings)
            onboarding_changed = (
                "onboarding_enabled" in update_data and update_data["onboarding_enabled"] != current_settings["onboarding_enabled"]
            )
            current_settings.update(update_data)
            settings.settings = current_settings
            if onboarding_changed:
                from core.model.user import User

                User.set_onboarding_enabled_for_all(current_settings["onboarding_enabled"])
        db.session.commit()
        return {"message": "Successfully updated settings", "settings": settings.to_dict()["settings"]}, 200

    @classmethod
    def _validate_chat_settings(cls, update_data: dict[str, Any]) -> None:
        update_data.pop("chat_llm_api_key_configured", None)
        for key in ("chat_llm_timeout", "chat_max_stories"):
            if key in update_data:
                value = cls._validate_non_negative_int(update_data[key])
                if value == 0 or (key == "chat_max_stories" and value > 20):
                    raise ValueError
                update_data[key] = value
        for key in ("chat_llm_base_url", "chat_llm_model", "chat_llm_api_key"):
            if key in update_data:
                if not isinstance(update_data[key], str):
                    raise TypeError
                update_data[key] = update_data[key].strip()
        if base_url := update_data.get("chat_llm_base_url"):
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError
            if parsed.port == 0 or parsed.query or parsed.fragment:
                raise ValueError
        clear_key = cls._validate_bool(update_data.pop("chat_llm_api_key_clear", False))
        if clear_key:
            update_data["chat_llm_api_key"] = ""
        elif not update_data.get("chat_llm_api_key"):
            update_data.pop("chat_llm_api_key", None)

    @classmethod
    def initialize(cls):
        if settings := cls.get_settings_entry():
            onboarding_missing = "onboarding_enabled" not in (settings.settings or {})
            settings.settings = cls.with_defaults(settings.settings)
        else:
            seed = cls._normalize_update_data(Config.PRE_SEED_SETTINGS)
            for key in ("default_bot_lookback_days", "rss_collector_max_entries"):
                if key in seed:
                    seed[key] = cls._validate_non_negative_int(seed[key])
            if seed.get("rss_collector_max_entries") == 0:
                raise ValueError("Invalid RSS collector entry limit")
            if "onboarding_enabled" in seed:
                seed["onboarding_enabled"] = cls._validate_bool(seed["onboarding_enabled"])
            settings = cls(seed)
            onboarding_missing = True
            db.session.add(settings)

        if onboarding_missing:
            from core.model.user import User

            User.set_onboarding_enabled_for_all(settings.settings["onboarding_enabled"])

        db.session.commit()

    @classmethod
    def get_settings(cls) -> dict:
        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return cls.with_defaults()
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
            raise TypeError("Invalid timezone: must be a string")
        timezone_name = value.strip()
        if not timezone_name:
            return None
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Invalid timezone: {timezone_name}") from None
        return timezone_name

    @staticmethod
    def _validate_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            return value.strip().lower() == "true"
        raise ValueError("Invalid boolean")

    @staticmethod
    def _validate_non_negative_int(value: Any) -> int:
        if isinstance(value, bool):
            raise TypeError("Invalid non-negative integer")
        if isinstance(value, int):
            normalized = value
        elif isinstance(value, str) and value.strip().isdecimal():
            normalized = int(value.strip())
        else:
            raise ValueError("Invalid non-negative integer")
        if normalized < 0:
            raise ValueError("Invalid non-negative integer")
        return normalized

    @classmethod
    def get_settings_entry(cls) -> "Settings | None":
        return cls.get_first(db.select(cls).filter_by(singleton_key=cls.SINGLETON_KEY))

    @classmethod
    def get(cls, item_id):
        if item_id in (1, "1", cls.SINGLETON_KEY):
            return cls.get_settings_entry()
        return super().get(item_id)
