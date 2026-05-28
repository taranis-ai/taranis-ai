from typing import Any

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
    def with_defaults(cls, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = dict(settings) if isinstance(settings, dict) else {}
        merged.setdefault("default_collector_proxy", "")
        merged.setdefault("default_collector_interval", "0 */8 * * *")
        merged.setdefault("default_tlp_level", TLPLevel.CLEAR.value)
        merged.setdefault("default_story_conflict_retention", "200")
        merged.setdefault("default_news_item_conflict_retention", "200")
        onboarding_tours = merged.setdefault("onboarding_tours", {})
        if isinstance(onboarding_tours, dict):
            merged["onboarding_tours"] = dict(onboarding_tours)
        else:
            merged["onboarding_tours"] = {}
        return merged

    @classmethod
    def update(cls, data) -> tuple[dict, int]:
        settings = cls.get_settings_entry()
        if settings is None:
            logger.debug("No Settings entry found")
            return {"error": "Error updating settings"}, 404

        update_data = data.get("settings") or {}
        reset_onboarding_tours = data.get("reset_onboarding_tours") in {True, "true", "1", "on"}
        if update_data or reset_onboarding_tours:
            logger.debug(f"Settings update data: {update_data}")
            logger.debug(f"Settings before update: {settings.settings}")
            update_data = dict(update_data)
            current_settings = cls.with_defaults(settings.settings)
            onboarding_tours = update_data.pop("onboarding_tours", None)
            current_settings.update(update_data)
            if reset_onboarding_tours:
                current_settings["onboarding_tours"] = {}
            elif isinstance(onboarding_tours, dict) and onboarding_tours:
                current_settings["onboarding_tours"] = {
                    **current_settings["onboarding_tours"],
                    **onboarding_tours,
                }
            settings.settings = cls.with_defaults(current_settings)
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
    def get_settings_entry(cls) -> "Settings | None":
        return cls.get_first(db.select(cls).filter_by(singleton_key=cls.SINGLETON_KEY))

    @classmethod
    def get(cls, item_id):
        if item_id in (1, "1", cls.SINGLETON_KEY):
            return cls.get_settings_entry()
        return super().get(item_id)
