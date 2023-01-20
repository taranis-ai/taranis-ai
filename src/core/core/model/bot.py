from marshmallow import fields, post_load
from sqlalchemy import or_, func
import uuid

from managers.db_manager import db
from model.parameter import NewParameterSchema
from shared.schema.bot import BotSchema


class NewBotSchema(BotSchema):
    parameters = fields.List(fields.Nested(NewParameterSchema))

    @post_load
    def make(self, data, **kwargs):
        return Bot(**data)


class Bot(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(64), nullable=False)

    parameters = db.relationship("Parameter", secondary="bot_parameter")

    node_id = db.Column(db.String, db.ForeignKey("bots_node.id"))
    node = db.relationship("BotsNode", back_populates="bots")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def create_all(cls, bots_data):
        new_bot_schema = NewBotSchema(many=True)
        return new_bot_schema.load(bots_data)

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Bot.name).like(search_string),
                    func.lower(Bot.description).like(search_string),
                )
            )

        return query.order_by(db.asc(Bot.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        bots, count = cls.get(search)
        node_schema = BotSchema(many=True)
        items = node_schema.dump(bots)

        return {"total_count": count, "items": items}


class BotParameter(db.Model):
    bot_id = db.Column(db.String, db.ForeignKey("bot.id"), primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey("parameter.id"), primary_key=True)
