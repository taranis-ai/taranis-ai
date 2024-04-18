from datetime import datetime
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class TokenBlacklist(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    token: Any = db.Column(db.String(), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, token):
        self.id = None
        self.token = token

    @classmethod
    def add(cls, token):
        db.session.add(TokenBlacklist(token))
        db.session.commit()

    @classmethod
    def invalid(cls, token):
        return db.session.query(db.exists().where(TokenBlacklist.token == token)).scalar()

    @classmethod
    def delete_older(cls, check_time):
        db.select(TokenBlacklist).filter(TokenBlacklist.created < check_time).delete()
        db.session.commit()
