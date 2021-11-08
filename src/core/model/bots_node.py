from marshmallow import post_load
from sqlalchemy import func, or_, orm
import uuid

from managers.db_manager import db
from schema.bots_node import BotsNodeSchema, BotsNodePresentationSchema


class NewBotsNodeSchema(BotsNodeSchema):

    @post_load
    def make(self, data, **kwargs):
        return BotsNode(**data)


class BotsNode(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    bots = db.relationship('Bot', back_populates="node", cascade="all")

    def __init__(self, id, name, description, api_url, api_key):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-server-network"

    @classmethod
    def exists_by_api_key(cls, api_key):
        return db.session.query(db.exists().where(BotsNode.api_key == api_key)).scalar()

    @classmethod
    def get_by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(BotsNode.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(BotsNode.name).like(search_string),
                func.lower(BotsNode.description).like(search_string)))

        return query.order_by(db.asc(BotsNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        nodes, count = cls.get(search)
        node_schema = BotsNodePresentationSchema(many=True)
        return {'total_count': count, 'items': node_schema.dump(nodes)}

    @classmethod
    def add_new(cls, node_data, bots):
        new_node_schema = NewBotsNodeSchema()
        node = new_node_schema.load(node_data)
        node.bots = bots
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id, node_data, bots):
        new_node_schema = NewBotsNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = cls.query.get(node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for bot in bots:
            found = False
            for existing_bot in node.bots:
                if bot.type == existing_bot.type:
                    found = True
                    break

            if found is False:
                node.bots.append(bot)

        db.session.commit()

    @classmethod
    def delete(cls, node_id):
        node = cls.query.get(node_id)
        for bot in node.bots:
            if len(bot.presets) > 0:
                raise Exception("Bots has mapped presets")

        db.session.delete(node)
        db.session.commit()
