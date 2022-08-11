from datetime import datetime

from core.managers.db_manager import db


class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(), nullable=False)
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
        db.session.query(TokenBlacklist).filter(TokenBlacklist.created < check_time).delete()
        db.session.commit()
