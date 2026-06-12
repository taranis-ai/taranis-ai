import copy
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
        self.settings = settings or {
            "default_collector_proxy": "",
            "default_collector_interval": "0 */8 * * *",
            "default_tlp_level": TLPLevel.CLEAR.value,
            "default_story_conflict_retention": "200",
            "default_news_item_conflict_retention": "200",
            "default_timezone": None,
        }

    @classmethod
    def update(cls, data) -> tuple[dict, int]:
        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return {"error": "Error updating settings"}, 404

        if update_data := data.get("settings"):
            try:
                update_data = cls._normalize_update_data(update_data)
            except ValueError as exc:
                return {"error": str(exc)}, 400
            logger.debug(f"Settings update data: {update_data}")
            logger.debug(f"Settings before update: {settings.settings}")
            settings.settings = {**settings.settings, **update_data}
        db.session.commit()
        logger.debug(f"Settings after update: {settings.settings}")
        return {"message": "Successfully updated settings", "settings": settings.settings}, 200

    @classmethod
    def initialize(cls):
        if settings := cls.get_settings_entry():
            current_settings = copy.deepcopy(settings.settings)
            if "default_collector_proxy" not in current_settings:
                current_settings["default_collector_proxy"] = ""
            if "default_collector_interval" not in current_settings:
                current_settings["default_collector_interval"] = "0 */8 * * *"
            if "default_tlp_level" not in current_settings:
                current_settings["default_tlp_level"] = TLPLevel.CLEAR.value
            if "default_story_conflict_retention" not in current_settings:
                current_settings["default_story_conflict_retention"] = "200"
            if "default_news_item_conflict_retention" not in current_settings:
                current_settings["default_news_item_conflict_retention"] = "200"
            if "default_timezone" not in current_settings:
                current_settings["default_timezone"] = None
            settings.settings = current_settings
        else:
            db.session.add(Settings())

        db.session.commit()

    @classmethod
    def get_settings(cls) -> dict:
        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return {}
        return settings.settings

    @classmethod
    def _normalize_update_data(cls, data: dict) -> dict:
        normalized = dict(data)
        if "default_timezone" in normalized:
            normalized["default_timezone"] = cls._validate_timezone(normalized.get("default_timezone"))
        return normalized

    @staticmethod
    def _validate_timezone(value: str | None) -> str | None:
        timezone_name = (value or "").strip()
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
