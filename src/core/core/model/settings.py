from sqlalchemy.orm import Mapped
from sqlalchemy.schema import CheckConstraint

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Settings(BaseModel):
    __tablename__ = "settings"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True, default=1)
    __table_args__ = (CheckConstraint("id = 1", name="check_only_one_row"),)

    settings: Mapped["dict"] = db.Column(db.JSON)

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {"global_proxy": "", "default_collector_interval": "* */8 * * *"}

    @classmethod
    def update(cls, data) -> tuple[dict, int]:
        settings = cls.get(1)
        if settings is None:
            return {"error": "Error updating settings"}, 404

        settings.settings = data
        db.session.commit()
        return {"message": "Successfully updated settings"}, 200
