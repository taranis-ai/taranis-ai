import uuid
from datetime import datetime

from marshmallow import post_load, fields
from sqlalchemy import orm, func, or_, and_
from sqlalchemy.types import JSON

from managers.db_manager import db
from model.acl_entry import ACLEntry
from model.collector import Collector
from model.parameter_value import NewParameterValueSchema, ParameterValue
from model.word_list import WordList
from schema.acl_entry import ItemType
from schema.osint_source import OSINTSourceSchema, OSINTSourceGroupSchema, OSINTSourceIdSchema, \
    OSINTSourcePresentationSchema, OSINTSourceGroupPresentationSchema, OSINTSourceGroupIdSchema
from schema.word_list import WordListIdSchema


class NewOSINTSourceSchema(OSINTSourceSchema):
    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))
    word_lists = fields.List(fields.Nested(WordListIdSchema))
    osint_source_groups = fields.List(fields.Nested(OSINTSourceGroupIdSchema))

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
    last_data = db.Column(JSON, default=None)

    def __init__(self, id, name, description, collector_id, parameter_values, word_lists, osint_source_groups):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.collector_id = collector_id
        self.parameter_values = parameter_values
        self.tag = ""

        self.word_lists = []
        for word_list in word_lists:
            self.word_lists.append(WordList.find(word_list.id))

        self.osint_source_groups = []
        for osint_source_group in osint_source_groups:
            group = OSINTSourceGroup.find(osint_source_group.id)
            if not group.default:
                self.osint_source_groups.append(group)

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-animation-outline"

    @classmethod
    def find(cls, source_id):
        source = cls.query.get(source_id)
        return source

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(OSINTSource.name)).all()

    @classmethod
    def get_all_manual(cls, user):
        query = cls.query.join(Collector, OSINTSource.collector_id == Collector.id).filter(
            Collector.type == 'MANUAL_COLLECTOR')

        query = query.outerjoin(ACLEntry, or_(and_(OSINTSource.id == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.OSINT_SOURCE),
                                              and_(OSINTSource.collector_id == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.COLLECTOR)))

        query = ACLEntry.apply_query(query, user, False, True, False)

        return query.order_by(db.asc(OSINTSource.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.join(Collector, OSINTSource.collector_id == Collector.id).filter(or_(
                func.lower(OSINTSource.name).like(search_string),
                func.lower(OSINTSource.description).like(search_string),
                func.lower(Collector.type).like(search_string)))

        return query.order_by(db.asc(OSINTSource.name)).all(), query.count()

    @classmethod
    def get_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def get_all_json(cls, search):
        sources, count = cls.get(search)
        for source in sources:
            source.osint_source_groups = OSINTSourceGroup.get_for_osint_source(source.id)
        sources_schema = OSINTSourcePresentationSchema(many=True)
        return {'total_count': count, 'items': sources_schema.dump(sources)}

    @classmethod
    def get_all_manual_json(cls, user):
        sources = cls.get_all_manual(user)
        for source in sources:
            source.osint_source_groups = OSINTSourceGroup.get_for_osint_source(source.id)
        sources_schema = OSINTSourcePresentationSchema(many=True)
        return sources_schema.dump(sources)

    @classmethod
    def get_all_for_collector_json(cls, collector_node, collector_type):
        for collector in collector_node.collectors:
            if collector.type == collector_type:
                sources_schema = OSINTSourceSchema(many=True)
                return sources_schema.dump(collector.sources)

    @classmethod
    def add_new(cls, data):
        new_osint_source_schema = NewOSINTSourceSchema()
        osint_source = new_osint_source_schema.load(data)
        db.session.add(osint_source)

        if len(osint_source.osint_source_groups) > 0:
            for osint_source_group in osint_source.osint_source_groups:
                osint_source_group.osint_sources.append(osint_source)
        else:
            default_group = OSINTSourceGroup.get_default()
            default_group.osint_sources.append(osint_source)

        db.session.commit()

        return osint_source

    @classmethod
    def import_new(cls, osint_source, collector):
        parameter_values = []
        for parameter_value in osint_source.parameter_values:
            for parameter in collector.parameters:
                if parameter.key == parameter_value.parameter.key:
                    new_parameter_value = ParameterValue(parameter_value.value, parameter)
                    parameter_values.append(new_parameter_value)
                    break

        news_osint_source = OSINTSource('', osint_source.name, osint_source.description, collector.id, parameter_values,
                                        [], [])

        db.session.add(news_osint_source)
        default_group = OSINTSourceGroup.get_default()
        default_group.osint_sources.append(news_osint_source)
        db.session.commit()

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

        current_groups = OSINTSourceGroup.get_for_osint_source(osint_source_id)
        default_group = None
        for group in current_groups:
            if group.default:
                default_group = group

            for source in group.osint_sources:
                if source.id == osint_source_id:
                    group.osint_sources.remove(source)
                    break

        if len(updated_osint_source.osint_source_groups) > 0:
            for osint_source_group in updated_osint_source.osint_source_groups:
                osint_source_group.osint_sources.append(osint_source)
        else:
            default_group = OSINTSourceGroup.get_default()
            default_group.osint_sources.append(osint_source)

        db.session.commit()

        return osint_source, default_group

    def update_status(self, status_schema):
        # if not collected, do not change last collected timestamp
        if status_schema.last_collected:
            self.last_collected = status_schema.last_collected

        # if not attempted, do not change last collected timestamp
        if status_schema.last_attempted:
            self.last_attempted = status_schema.last_attempted

        self.last_error_message = status_schema.last_error_message
        self.last_data = status_schema.last_data


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
    default = db.Column(db.Boolean(), default=False)

    osint_sources = db.relationship('OSINTSource', secondary='osint_source_group_osint_source')

    def __init__(self, id, name, description, default, osint_sources):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.default = False
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
    def get_for_osint_source(cls, osint_source_id):
        return cls.query.join(OSINTSourceGroupOSINTSource,
                              and_(OSINTSourceGroupOSINTSource.osint_source_id == osint_source_id,
                                   OSINTSourceGroup.id == OSINTSourceGroupOSINTSource.osint_source_group_id)).all()

    @classmethod
    def get_default(cls):
        return cls.query.filter(OSINTSourceGroup.default == True).first()

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

        return query.order_by(db.asc(OSINTSourceGroup.default), db.asc(OSINTSourceGroup.name)).all(), query.count()

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
        if osint_source_group.default is False:
            db.session.delete(osint_source_group)
            db.session.commit()
            return "", 200
        else:
            return {'message': 'could_not_delete_default_group'}, 400

    @classmethod
    def update(cls, osint_source_group_id, data):
        new_osint_source_group_schema = NewOSINTSourceGroupSchema()
        updated_osint_source_group = new_osint_source_group_schema.load(data)
        osint_source_group = cls.query.get(osint_source_group_id)
        if osint_source_group.default is False:
            osint_source_group.name = updated_osint_source_group.name
            osint_source_group.description = updated_osint_source_group.description
            osint_source_group.osint_sources = updated_osint_source_group.osint_sources

            sources_in_default_group = set()
            for source in osint_source_group.osint_sources:
                current_groups = OSINTSourceGroup.get_for_osint_source(source.id)
                for current_group in current_groups:
                    if current_group.default:
                        current_group.osint_sources.remove(source)
                        sources_in_default_group.add(source)
                        break

            db.session.commit()

            return sources_in_default_group, "", 200
        else:
            return None, {'message': 'could_not_modify_default_group'}, 400


class OSINTSourceGroupOSINTSource(db.Model):
    osint_source_group_id = db.Column(db.String, db.ForeignKey('osint_source_group.id'), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey('osint_source.id'), primary_key=True)
