from marshmallow import post_load, fields
import uuid
from sqlalchemy import func, or_, orm

from managers.db_manager import db
from model.bots_node import BotsNode
from model.parameter_value import NewParameterValueSchema
from schema.bot_preset import BotPresetSchema, BotPresetPresentationSchema


class NewBotPresetSchema(BotPresetSchema):
    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        return BotPreset(**data)


class BotPreset(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    bot_id = db.Column(db.String, db.ForeignKey('bot.id'))
    bot = db.relationship("Bot", back_populates="presets")

    parameter_values = db.relationship('ParameterValue', secondary='bot_preset_parameter_value', cascade="all")

    def __init__(self, id, name, description, bot_id, parameter_values):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.bot_id = bot_id
        self.parameter_values = parameter_values
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-robot"

    @classmethod
    def find(cls, preset_id):
        preset = cls.query.get(preset_id)
        return preset

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(BotPreset.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(BotPreset.name).like(search_string),
                func.lower(BotPreset.description).like(search_string)))

        return query.order_by(db.asc(BotPreset.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        bots, count = cls.get(search)
        bot_schema = BotPresetPresentationSchema(many=True)
        return {'total_count': count, 'items': bot_schema.dump(bots)}

    @classmethod
    def get_all_for_bot_json(cls, parameters):
        node = BotsNode.get_by_api_key(parameters.api_key)
        if node is not None:
            for bot in node.bots:
                if bot.type == parameters.bot_type:
                    presets_schema = BotPresetSchema(many=True)
                    return presets_schema.dump(bot.presets)

    @classmethod
    def add_new(cls, data):
        new_preset_schema = NewBotPresetSchema()
        preset = new_preset_schema.load(data)
        db.session.add(preset)
        db.session.commit()

    @classmethod
    def delete(cls, preset_id):
        preset = cls.query.get(preset_id)
        db.session.delete(preset)
        db.session.commit()

    @classmethod
    def update(cls, preset_id, data):
        new_preset_schema = NewBotPresetSchema()
        updated_preset = new_preset_schema.load(data)
        preset = cls.query.get(preset_id)
        preset.name = updated_preset.name
        preset.description = updated_preset.description

        for value in preset.parameter_values:
            for updated_value in updated_preset.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value

        db.session.commit()


class BotPresetParameterValue(db.Model):
    bot_preset_id = db.Column(db.String, db.ForeignKey('bot_preset.id'), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey('parameter_value.id'), primary_key=True)
