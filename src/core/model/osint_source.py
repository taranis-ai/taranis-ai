import uuid

from marshmallow import post_load, fields
from sqlalchemy import orm, func, or_, and_

from managers.db_manager import db
from model.acl_entry import ACLEntry
from model.collector import Collector
from model.collectors_node import CollectorsNode
from model.parameter_value import NewParameterValueSchema
from model.word_list import WordList
from taranisng.schema.acl_entry import ItemType
from taranisng.schema.osint_source import OSINTSourceSchema, OSINTSourceGroupSchema, OSINTSourceIdSchema, \
    OSINTSourcePresentationSchema, OSINTSourceGroupPresentationSchema
from taranisng.schema.word_list import WordListIdSchema
from datetime import datetime


class NewOSINTSourceSchema(OSINTSourceSchema):
    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))
    word_lists = fields.List(fields.Nested(WordListIdSchema))

    @post_load
    def make_osint_source(self, data, **kwargs):
        return OSINTSource(**data)


class OSINTSource(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    collector_id = db.Column(db.String, db.ForeignKey('collector.id'))
    collector = db.relationship("Collector", back_populates="sources")

    parameter_values = db.relationship('ParameterValue', secondary='osint_source_parameter_value',
                                       cascade="all")

    word_lists = db.relationship('WordList', secondary='osint_source_word_list')

    modified = db.Column(db.DateTime, default=datetime.now)
    last_collected = db.Column(db.DateTime, default=None)
    last_attempted = db.Column(db.DateTime, default=None)
    state = db.Column(db.SmallInteger, default=0)
    last_error_message = db.Column(db.String, default=None)
    screenshot = db.Column(db.LargeBinary, default=None)

    def __init__(self, id, name, description, collector_id, parameter_values, word_lists):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.collector_id = collector_id
        self.parameter_values = parameter_values
        self.tag = ""

        self.word_lists = []
        for word_list in word_lists:
            self.word_lists.append(WordList.find(word_list.id))

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-animation-outline"

    @classmethod
    def find(cls, source_id):
        source = cls.query.get(source_id)
        return source

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.desc(OSINTSource.name)).all()

    @classmethod
    def get_all_manual(cls, user):
        query = cls.query.join(Collector, OSINTSource.collector_id == Collector.id).filter(
            Collector.type == 'MANUAL_COLLECTOR')

        query = query.outerjoin(ACLEntry, or_(and_(OSINTSource.id == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.OSINT_SOURCE),
                                              and_(OSINTSource.collector_id == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.COLLECTOR)))

        query = ACLEntry.apply_query(query, user, False, True, False)

        return query.order_by(db.desc(OSINTSource.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.join(Collector, OSINTSource.collector_id == Collector.id).filter(or_(
                func.lower(OSINTSource.name).like(search_string),
                func.lower(OSINTSource.description).like(search_string),
                func.lower(Collector.type).like(search_string)))

        return query.order_by(db.desc(OSINTSource.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        sources, count = cls.get(search)
        sources_schema = OSINTSourcePresentationSchema(many=True)
        return {'total_count': count, 'items': sources_schema.dump(sources)}

    @classmethod
    def get_all_manual_json(cls, user):
        sources = cls.get_all_manual(user)
        sources_schema = OSINTSourcePresentationSchema(many=True)
        return sources_schema.dump(sources)

    @classmethod
    def get_all_for_collector_json(cls, parameters):
        node = CollectorsNode.get_by_api_key(parameters.api_key)
        if node is not None:
            for collector in node.collectors:
                if collector.type == parameters.collector_type:
                    sources_schema = OSINTSourceSchema(many=True)
                    return sources_schema.dump(collector.sources)

    @classmethod
    def add_new(cls, data):
        new_osint_source_schema = NewOSINTSourceSchema()
        osint_source = new_osint_source_schema.load(data)
        db.session.add(osint_source)
        db.session.commit()
        return osint_source

    @classmethod
    def delete(cls, osint_source_id):
        osint_source = cls.query.get(osint_source_id)
        db.session.delete(osint_source)
        db.session.commit()

    @classmethod
    def update(cls, osint_source_id, data):
        new_osint_source_schema = NewOSINTSourceSchema()
        updated_osint_source = new_osint_source_schema.load(data)
        osint_source = cls.query.get(osint_source_id)
        osint_source.name = updated_osint_source.name
        osint_source.description = updated_osint_source.description

        for value in osint_source.parameter_values:
            for updated_value in updated_osint_source.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value

        osint_source.word_lists = updated_osint_source.word_lists
        db.session.commit()
        return osint_source


class OSINTSourceParameterValue(db.Model):
    osint_source_id = db.Column(db.String, db.ForeignKey('osint_source.id'), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey('parameter_value.id'), primary_key=True)


class OSINTSourceWordList(db.Model):
    osint_source_id = db.Column(db.String, db.ForeignKey('osint_source.id'), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey('word_list.id'), primary_key=True)


class NewOSINTSourceGroupSchema(OSINTSourceGroupSchema):
    osint_sources = fields.Nested(OSINTSourceIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return OSINTSourceGroup(**data)


class OSINTSourceGroup(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    osint_sources = db.relationship('OSINTSource', secondary='osint_source_group_osint_source')

    def __init__(self, id, name, description, osint_sources):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.osint_sources = []
        self.tag = ""
        for osint_source in osint_sources:
            self.osint_sources.append(OSINTSource.find(osint_source.id))

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-folder-multiple"

    @classmethod
    def find(cls, group_id):
        group = cls.query.get(group_id)
        return group

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(OSINTSourceGroup.name)).all()

    @classmethod
    def allowed_with_acl(cls, group_id, user, see, access, modify):

        query = db.session.query(OSINTSourceGroup.id).distinct().group_by(OSINTSourceGroup.id).filter(
            OSINTSourceGroup.id == group_id)

        query = query.outerjoin(ACLEntry, and_(OSINTSourceGroup.id == ACLEntry.item_id,
                                               ACLEntry.item_type == ItemType.OSINT_SOURCE_GROUP))

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(OSINTSourceGroup.id)

        if acl_check is True:
            query = query.outerjoin(ACLEntry, and_(OSINTSourceGroup.id == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.OSINT_SOURCE_GROUP))
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(OSINTSourceGroup.name).like(search_string),
                func.lower(OSINTSourceGroup.description).like(search_string)))

        return query.order_by(db.asc(OSINTSourceGroup.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        groups, count = cls.get(search, user, acl_check)
        group_schema = OSINTSourceGroupPresentationSchema(many=True)
        return {'total_count': count, 'items': group_schema.dump(groups)}

    @classmethod
    def get_all_with_source(cls, osint_source_id):
        all_groups = cls.get_all()
        groups = []
        for group in all_groups:
            for source in group.osint_sources:
                if source.id == osint_source_id:
                    groups.append(group)
                    break

        return groups

    @classmethod
    def add(cls, data):
        new_osint_source_group_schema = NewOSINTSourceGroupSchema()
        osint_source_group = new_osint_source_group_schema.load(data)
        db.session.add(osint_source_group)
        db.session.commit()

    @classmethod
    def delete(cls, osint_source_group_id):
        osint_source_group = cls.query.get(osint_source_group_id)
        db.session.delete(osint_source_group)
        db.session.commit()

    @classmethod
    def update(cls, osint_source_group_id, data):
        new_osint_source_group_schema = NewOSINTSourceGroupSchema()
        updated_osint_source_group = new_osint_source_group_schema.load(data)
        osint_source_group = cls.query.get(osint_source_group_id)
        osint_source_group.name = updated_osint_source_group.name
        osint_source_group.description = updated_osint_source_group.description
        osint_source_group.osint_sources = updated_osint_source_group.osint_sources
        db.session.commit()


class OSINTSourceGroupOSINTSource(db.Model):
    osint_source_group_id = db.Column(db.String, db.ForeignKey('osint_source_group.id'), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey('osint_source.id'), primary_key=True)
