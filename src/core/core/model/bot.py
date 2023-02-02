from marshmallow import fields, post_load
from sqlalchemy import or_, func
import uuid

from core.managers.db_manager import db
from core.model.parameter_value import ParameterValueImportSchema
from core.managers.log_manager import logger
from shared.schema.bot import BotSchema


class NewBotSchema(BotSchema):
    parameter_values = fields.List(fields.Nested(ParameterValueImportSchema), load_default=[])

    @post_load
    def make(self, data, **kwargs):
        return Bot(**data)


class Bot(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.String(64), nullable=False)
    parameter_values = db.relationship("ParameterValue", secondary="bot_parameter_value", cascade="all")

    def __init__(self, name, description, type, parameter_values):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameter_values = parameter_values

    @classmethod
    def create_all(cls, bots_data):
        new_bot_schema = NewBotSchema(many=True)
        return new_bot_schema.load(bots_data)

    @classmethod
    def update_bot_parameters(cls, bot_id, data):
        try:
            bot = cls.find_by_id(bot_id)
            if not bot:
                return None
            # parameter_values = [NewParameterValueSchema().load(pv) for pv in data["parameter_values"]]
            for pv in bot.parameter_values:
                for updated_value in data["parameter_values"]:
                    if pv.parameter.key == updated_value["parameter"]:
                        pv.value = updated_value["value"]

            # bot_params = [{"id": pv.id, "key": pv.parameter.key, "value": pv.value} for pv in bot.parameter_values]
            # print(f"bot_params = {bot_params}")
            # bot.parameter_values = parameter_values
            db.session.commit()
        except Exception:
            logger.log_debug_trace("Update Bot Parameters Failed")

    @classmethod
    def add(cls, data):
        if cls.find_by_type(data["type"]):
            return None
        schema = NewBotSchema()
        bot = schema.load(data)
        db.session.add(bot)
        db.session.commit()

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def find_by_type(cls, type):
        return cls.query.filter_by(type=type).first()

    @classmethod
    def get_all_by_type(cls, type):
        return cls.query.filter_by(type=type).all()

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


class BotParameterValue(db.Model):
    bot_id = db.Column(db.String, db.ForeignKey("bot.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
