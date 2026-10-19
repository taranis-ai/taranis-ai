from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from models.llm import LLM_FEATURES, LLMEndpoint
from sqlalchemy import event
from sqlalchemy.orm import Mapped, Session

from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.role import TLPLevel


_SETTINGS_CACHE_KEY = "core.settings"


@event.listens_for(Session, "after_flush")
@event.listens_for(Session, "after_transaction_end")
def _clear_settings_cache(session, _context):
    session.info.pop(_SETTINGS_CACHE_KEY, None)


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
        self._validate_llm_settings(self.settings)

    @classmethod
    def with_defaults(cls, settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(settings) if isinstance(settings, Mapping) else {}
        merged.setdefault("default_collector_proxy", "")
        merged.setdefault("default_collector_interval", "0 */8 * * *")
        merged.setdefault("rss_collector_max_entries", 42)
        merged.setdefault("collection_group_threshold", 85)
        merged.setdefault("collection_lookback_days", 30)
        merged.setdefault("default_bot_lookback_days", 7)
        merged.setdefault("default_tlp_level", TLPLevel.CLEAR.value)
        merged.setdefault("default_story_conflict_retention", "200")
        merged.setdefault("default_news_item_conflict_retention", "200")
        merged.setdefault("default_timezone", None)
        merged.setdefault("onboarding_enabled", True)
        # Convert the old Chat configuration once, without opting worker jobs into it.
        if "llm_endpoints" not in merged:
            merged["llm_endpoints"] = {}
            if merged.get("chat_llm_base_url"):
                merged["llm_endpoints"]["existing-chat"] = LLMEndpoint(
                    name="Existing Chat provider",
                    base_url=merged["chat_llm_base_url"],
                    api_key=merged.get("chat_llm_api_key", ""),
                    model=merged.get("chat_llm_model", ""),
                    api_format=merged.get("chat_llm_api_format", "responses"),
                    timeout=merged.get("chat_llm_timeout", 120),
                    enabled=not Config.DEBUG,
                ).model_dump()
                merged["llm_chat_endpoint"] = "existing-chat"
        for key in list(merged):
            if key.startswith("chat_llm_"):
                merged.pop(key)
        merged["llm_endpoints"] = {key: {"enabled": not Config.DEBUG, **endpoint} for key, endpoint in merged["llm_endpoints"].items()}
        merged.setdefault("llm_default_endpoint", "")
        for feature in LLM_FEATURES:
            merged.setdefault(f"llm_{feature}_endpoint", "")
        merged.setdefault("chat_max_stories", 5)
        return merged

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        public_settings = deepcopy(self.with_defaults(self.settings))
        from core.service.endpoint_health import get_status

        for endpoint_id, endpoint in public_settings["llm_endpoints"].items():
            endpoint["health"] = get_status("llm", endpoint_id, dict(endpoint))
            endpoint["api_key_configured"] = bool(endpoint.pop("api_key", ""))
        data["settings"] = public_settings
        return data

    @classmethod
    def update(cls, data) -> tuple[dict, int]:
        if not isinstance(data, dict):
            return {"error": "Invalid settings payload"}, 400

        settings = cls.get_first(
            db.select(cls).filter_by(singleton_key=cls.SINGLETON_KEY).with_for_update().execution_options(populate_existing=True)
        )
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
        try:
            cls._normalize_collection_settings(update_data)
        except (TypeError, ValueError):
            return {"error": "Collection threshold must be 1–100 and lookback days must be 1–36500"}, 400
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

        current_settings = cls.with_defaults(settings.settings)
        if "llm_endpoints" in update_data or any(key.startswith("chat_llm_") for key in update_data):
            return {"error": "Manage providers in LLM Endpoints"}, 400
        for key in ("llm_default_endpoint", *(f"llm_{feature}_endpoint" for feature in LLM_FEATURES)):
            if key in update_data and (
                not isinstance(update_data[key], str) or (update_data[key] and update_data[key] not in current_settings["llm_endpoints"])
            ):
                return {"error": "Select an existing LLM endpoint"}, 400
        if cls._chat_uses_batch({**current_settings, **update_data}):
            return {"error": "Chat requires a realtime LLM endpoint. Assign Chat explicitly before using a batch default."}, 400
        if "chat_max_stories" in update_data:
            try:
                value = cls._validate_non_negative_int(update_data["chat_max_stories"])
                if not 1 <= value <= 20:
                    raise ValueError
                update_data["chat_max_stories"] = value
            except (TypeError, ValueError):
                return {"error": "Maximum stories must be between 1 and 20"}, 400

        if update_data:
            onboarding_changed = (
                "onboarding_enabled" in update_data and update_data["onboarding_enabled"] != current_settings["onboarding_enabled"]
            )
            current_settings.update(update_data)
            settings.settings = current_settings
            if onboarding_changed:
                from core.model.user import User

                User.set_onboarding_enabled_for_all(current_settings["onboarding_enabled"])
        db.session.commit()
        if any(key == "llm_default_endpoint" or key.startswith("llm_") and key.endswith("_endpoint") for key in update_data):
            from core.model.bot import Bot

            Bot.schedule_all_bots()
        return {"message": "Successfully updated settings", "settings": settings.to_dict()["settings"]}, 200

    @classmethod
    def _validate_llm_settings(cls, values: dict) -> None:
        endpoints = {key: LLMEndpoint.model_validate(value).model_dump() for key, value in values["llm_endpoints"].items()}
        names = [endpoint["name"].casefold() for endpoint in endpoints.values()]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate LLM endpoint names")
        for key in ("llm_default_endpoint", *(f"llm_{feature}_endpoint" for feature in LLM_FEATURES)):
            if values[key] and values[key] not in endpoints:
                raise ValueError("Unknown LLM endpoint assignment")
        values["llm_endpoints"] = endpoints
        if cls._chat_uses_batch(values):
            raise ValueError("Chat requires a realtime LLM endpoint")
        values["chat_max_stories"] = cls._validate_non_negative_int(values["chat_max_stories"])
        if not 1 <= values["chat_max_stories"] <= 20:
            raise ValueError("Maximum stories must be between 1 and 20")

    @classmethod
    def _chat_uses_batch(cls, values: dict) -> bool:
        endpoint_id = values.get("llm_chat_endpoint") or values.get("llm_default_endpoint")
        endpoint = values.get("llm_endpoints", {}).get(endpoint_id)
        return bool(endpoint and endpoint.get("processing_mode") == "openrouter_batch")

    @classmethod
    def get_llm_endpoint(cls, feature: str, settings: dict | None = None) -> dict | None:
        if feature not in LLM_FEATURES:
            return None
        values = settings if settings is not None else cls.get_settings()
        endpoint_id = values.get(f"llm_{feature}_endpoint") or values.get("llm_default_endpoint")
        endpoint = values.get("llm_endpoints", {}).get(endpoint_id)
        return deepcopy(endpoint) if endpoint and endpoint.get("enabled", True) else None

    @classmethod
    def save_llm_endpoint(cls, data: dict | None, endpoint_id: str | None = None, *, delete: bool = False) -> tuple[dict, int]:
        entry = cls.get_first(
            db.select(cls).filter_by(singleton_key=cls.SINGLETON_KEY).with_for_update().execution_options(populate_existing=True)
        )
        if entry is None:
            return {"error": "Settings not found"}, 404
        values = cls.with_defaults(entry.settings)
        endpoints = dict(values["llm_endpoints"])
        if delete:
            from core.model.bot import Bot

            if endpoint_id not in endpoints:
                return {"error": "LLM endpoint not found"}, 404
            if endpoint_id in [values.get("llm_default_endpoint"), *(values.get(f"llm_{feature}_endpoint") for feature in LLM_FEATURES)]:
                return {"error": "Reassign this endpoint before deleting it"}, 409
            if any(bot.parameters.get("LLM_ENDPOINT") == endpoint_id for bot in db.session.execute(db.select(Bot)).scalars()):
                return {"error": "Reassign this endpoint before deleting it"}, 409
            endpoints.pop(endpoint_id)
        else:
            if endpoint_id is not None and endpoint_id not in endpoints:
                return {"error": "LLM endpoint not found"}, 404
            if not isinstance(data, dict):
                return {"error": "Invalid LLM endpoint"}, 400
            submitted = dict(data)
            try:
                clear_key = cls._validate_bool(submitted.pop("api_key_clear", False))
                existing = endpoints.get(endpoint_id, {})
                if "enabled" in submitted:
                    submitted["enabled"] = cls._validate_bool(submitted["enabled"])
                elif endpoint_id is None:
                    submitted["enabled"] = not Config.DEBUG
                if clear_key:
                    submitted["api_key"] = ""
                elif "api_key" not in submitted or (isinstance(submitted["api_key"], str) and not submitted["api_key"].strip()):
                    submitted["api_key"] = existing.get("api_key", "")
                endpoint = LLMEndpoint.model_validate({**existing, **submitted}).model_dump()
            except (TypeError, ValueError):
                return {
                    "error": "Invalid LLM endpoint. Check the name, base URL, model, API format, processing mode, and positive timeout."
                }, 400
            if any(item["name"].casefold() == endpoint["name"].casefold() for key, item in endpoints.items() if key != endpoint_id):
                return {"error": "An LLM endpoint with this name already exists"}, 400
            endpoint_id = endpoint_id or cls.uuid7_str()
            endpoints[endpoint_id] = endpoint
        values["llm_endpoints"] = endpoints
        if cls._chat_uses_batch(values):
            return {"error": "Chat requires a realtime LLM endpoint. Reassign Chat before changing this endpoint to batch."}, 400
        entry.settings = values
        db.session.commit()
        from core.model.bot import Bot
        from core.service.endpoint_health import schedule_check

        Bot.schedule_all_bots()
        schedule_check("llm", endpoint_id)
        return {"message": "LLM endpoint deleted" if delete else "LLM endpoint saved", "id": endpoint_id}, 200

    @classmethod
    def initialize(cls):
        if settings := cls.get_settings_entry():
            onboarding_missing = "onboarding_enabled" not in (settings.settings or {})
            settings.settings = cls.with_defaults(settings.settings)
            cls._validate_llm_settings(settings.settings)
        else:
            seed = cls._normalize_update_data(Config.PRE_SEED_SETTINGS)
            cls._normalize_collection_settings(seed)
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
        session = db.session()
        # Keep normal query autoflush semantics when there are pending writes.
        if _SETTINGS_CACHE_KEY in session.info and not (session.new or session.dirty or session.deleted):
            return deepcopy(session.info[_SETTINGS_CACHE_KEY])
        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return {}
        snapshot = deepcopy(cls.with_defaults(settings.settings))
        session.info[_SETTINGS_CACHE_KEY] = snapshot
        return deepcopy(snapshot)

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
    def _normalize_collection_settings(cls, data: dict) -> None:
        for key, maximum in (("collection_group_threshold", 100), ("collection_lookback_days", 36500)):
            if key in data:
                value = cls._validate_non_negative_int(data[key])
                if not 1 <= value <= maximum:
                    raise ValueError("Invalid collection setting")
                data[key] = value

    @classmethod
    def get_settings_entry(cls) -> "Settings | None":
        return cls.get_first(db.select(cls).filter_by(singleton_key=cls.SINGLETON_KEY))

    @classmethod
    def get(cls, item_id):
        if item_id in (1, "1", cls.SINGLETON_KEY):
            return cls.get_settings_entry()
        return super().get(item_id)
