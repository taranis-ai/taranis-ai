from marshmallow import post_load, fields
from sqlalchemy import func, or_, orm
import uuid

from managers.db_manager import db
from model.parameter_value import NewParameterValueSchema
from model.publishers_node import PublishersNode
from schema.publisher_preset import PublisherPresetSchema, PublisherPresetPresentationSchema


class NewPublisherPresetSchema(PublisherPresetSchema):
    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        return PublisherPreset(**data)


class PublisherPreset(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    publisher_id = db.Column(db.String, db.ForeignKey('publisher.id'))
    publisher = db.relationship("Publisher", back_populates="presets")

    use_for_notifications = db.Column(db.Boolean)

    parameter_values = db.relationship('ParameterValue', secondary='publisher_preset_parameter_value', cascade="all")

    def __init__(self, id, name, description, publisher_id, use_for_notifications, parameter_values):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.publisher_id = publisher_id
        self.parameter_values = parameter_values
        self.use_for_notifications = use_for_notifications
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-file-star-outline"

    @classmethod
    def find(cls, preset_id):
        preset = cls.query.get(preset_id)
        return preset

    @classmethod
    def find_for_notifications(cls):
        return cls.query.filter_by(use_for_notifications=True).first()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(PublisherPreset.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(PublisherPreset.name).like(search_string),
                func.lower(PublisherPreset.description).like(search_string)))

        return query.order_by(db.asc(PublisherPreset.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        publishers, count = cls.get(search)
        publisher_schema = PublisherPresetPresentationSchema(many=True)
        return {'total_count': count, 'items': publisher_schema.dump(publishers)}

    @classmethod
    def get_all_for_publisher_json(cls, parameters):
        node = PublishersNode.get_by_api_key(parameters.api_key)
        for publisher in node.publishers:
            if publisher.type == parameters.publisher_type:
                presets_schema = PublisherPresetSchema(many=True)
                return presets_schema.dump(publisher.sources)

    @classmethod
    def add_new(cls, data):
        new_preset_schema = NewPublisherPresetSchema()
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
        new_preset_schema = NewPublisherPresetSchema()
        updated_preset = new_preset_schema.load(data)
        preset = cls.query.get(preset_id)
        preset.name = updated_preset.name
        preset.description = updated_preset.description

        for value in preset.parameter_values:
            for updated_value in updated_preset.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value

        db.session.commit()


class PublisherPresetParameterValue(db.Model):
    publisher_preset_id = db.Column(db.String, db.ForeignKey('publisher_preset.id'), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey('parameter_value.id'), primary_key=True)
