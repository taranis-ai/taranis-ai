from sqlalchemy.orm import Mapped
from sqlalchemy.schema import CheckConstraint

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role import TLPLevel
from core.log import logger


class Settings(BaseModel):
    __tablename__ = "settings"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True, default=1)
    __table_args__ = (CheckConstraint("id = 1", name="check_only_one_row"),)

    settings: Mapped["dict"] = db.Column(db.JSON)

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {
            "default_collector_proxy": "",
            "default_collector_interval": "0 */8 * * *",
            "default_tlp_level": TLPLevel.CLEAR.value,
        }

    @classmethod
    def update(cls, data) -> tuple[dict, int]:
        settings = cls.get(1)
        if settings is None:
            logger.debug("No Settings entry found")
            return {"error": "Error updating settings"}, 404

        if update_data := data.get("settings"):
            logger.debug(f"Settings update data: {update_data}")
            logger.debug(f"Settings before update: {settings.settings}")
            settings.settings = {**settings.settings, **update_data}
        db.session.commit()
        logger.debug(f"Settings after update: {settings.settings}")
        return {"message": "Successfully updated settings", "settings": settings.settings}, 200

    @classmethod
    def initialize(cls):
        if settings := cls.get(1):
            current_settings = settings.settings
            if "default_collector_proxy" not in current_settings:
                current_settings["default_collector_proxy"] = ""
            if "default_collector_interval" not in current_settings:
                current_settings["default_collector_interval"] = "0 */8 * * *"
            if "default_tlp_level" not in current_settings:
                current_settings["default_tlp_level"] = TLPLevel.CLEAR.value
        else:
            db.session.add(Settings())

        db.session.commit()

    @classmethod
    def get_settings(cls) -> dict:
        settings = cls.get(1)
        if settings is None:
            logger.debug("No Settings entry found")
            return {}
        return settings.settings
