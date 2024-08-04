from datetime import datetime
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class TokenBlacklist(BaseModel):
    __tablename__ = "token_blacklist"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    token: Mapped[str] = db.Column(db.String(), nullable=False)
    created: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, token):
        self.token = token

    @classmethod
    def add(cls, token: str):
        db.session.add(TokenBlacklist(token))
        db.session.commit()

    @classmethod
    def invalid(cls, token: str) -> bool:
        query = db.select(db.exists().where(cls.token == token))
        return db.session.execute(query).scalar_one()

    @classmethod
    def delete_older(cls, check_time: datetime):
        db.session.execute(db.delete(cls).where(cls.created < check_time))
        db.session.commit()
