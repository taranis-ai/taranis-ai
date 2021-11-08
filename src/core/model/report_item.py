from marshmallow import post_load
from datetime import datetime
import uuid as uuid_generator
from sqlalchemy import orm, or_, func, text, and_
from sqlalchemy.sql.expression import cast
import sqlalchemy
from marshmallow import fields, post_load

from managers.db_manager import db
from model.news_item import NewsItemAggregate
from model.report_item_type import AttributeGroupItem
from model.report_item_type import ReportItemType
from model.acl_entry import ACLEntry
from schema.acl_entry import ItemType
from schema.attribute import AttributeType
from schema.news_item import NewsItemAggregateIdSchema, NewsItemAggregateSchema
from schema.report_item import ReportItemAttributeBaseSchema, ReportItemBaseSchema, ReportItemIdSchema, RemoteReportItemSchema, ReportItemRemoteSchema, ReportItemSchema, ReportItemPresentationSchema


class NewReportItemAttributeSchema(ReportItemAttributeBaseSchema):

    @post_load
    def make_report_item_attribute(self, data, **kwargs):
        return ReportItemAttribute(**data)


class ReportItemAttribute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    binary_size = db.Column(db.Integer)
    binary_description = db.Column(db.String())
    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)

    version = db.Column(db.Integer, default=1)
    current = db.Column(db.Boolean, default=True)

    attribute_group_item_id = db.Column(db.Integer, db.ForeignKey('attribute_group_item.id'))
    attribute_group_item = db.relationship("AttributeGroupItem")
    attribute_group_item_title = db.Column(db.String)

    report_item_id = db.Column(db.Integer, db.ForeignKey('report_item.id'), nullable=True)
    report_item = db.relationship("ReportItem")

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship("User")

    def __init__(self, id, value, binary_mime_type, binary_size, binary_description, attribute_group_item_id,
                 attribute_group_item_title):
        self.id = None
        self.value = value
        self.binary_mime_type = binary_mime_type
        self.binary_size = binary_size
        self.binary_description = binary_description
        self.attribute_group_item_id = attribute_group_item_id
        self.attribute_group_item_title = attribute_group_item_title

    @classmethod
    def find(cls, attribute_id):
        report_item_attribute = cls.query.get(attribute_id)
        return report_item_attribute

    @staticmethod
    def sort(report_item_attribute):
        return report_item_attribute.last_updated


class NewReportItemSchema(ReportItemBaseSchema):
    news_item_aggregates = fields.Nested(NewsItemAggregateIdSchema, many=True, missing=[])
    remote_report_items = fields.Nested(ReportItemIdSchema, many=True, missing=[])
    attributes = fields.Nested(NewReportItemAttributeSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return ReportItem(**data)


class ReportItemRemoteReportItem(db.Model):
    report_item_id = db.Column(db.Integer, db.ForeignKey('report_item.id'), primary_key=True)
    remote_report_item_id = db.Column(db.Integer, db.ForeignKey('report_item.id'), primary_key=True)


class ReportItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64))

    title = db.Column(db.String())
    title_prefix = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship("User")
    remote_user = db.Column(db.String())

    report_item_type_id = db.Column(db.Integer, db.ForeignKey('report_item_type.id'), nullable=True)
    report_item_type = db.relationship("ReportItemType")

    news_item_aggregates = db.relationship("NewsItemAggregate", secondary='report_item_news_item_aggregate')

    remote_report_items = db.relationship("ReportItem", secondary='report_item_remote_report_item',
                                          primaryjoin=ReportItemRemoteReportItem.report_item_id == id,
                                          secondaryjoin=ReportItemRemoteReportItem.remote_report_item_id == id)

    attributes = db.relationship('ReportItemAttribute', back_populates="report_item", cascade="all, delete-orphan")

    report_item_cpes = db.relationship("ReportItemCpe", cascade="all, delete-orphan")

    def __init__(self, id, uuid, title, title_prefix, report_item_type_id, news_item_aggregates, remote_report_items,
                 attributes, completed):

        self.id = id

        if uuid is None:
            self.uuid = str(uuid_generator.uuid4())
        else:
            self.uuid = uuid

        self.title = title
        self.title_prefix = title_prefix
        self.report_item_type_id = report_item_type_id
        self.attributes = attributes
        self.completed = completed
        self.report_item_cpes = []
        self.subtitle = ""
        self.tag = ""

        self.news_item_aggregates = []
        for news_item_aggregate in news_item_aggregates:
            self.news_item_aggregates.append(NewsItemAggregate.find(news_item_aggregate.id))

        self.remote_report_items = []
        for remote_report_item in remote_report_items:
            self.remote_report_items.append(ReportItem.find(remote_report_item.id))

    @orm.reconstructor
    def reconstruct(self):
        self.subtitle = ""
        self.tag = "mdi-file-table-outline"
        self.attributes.sort(key=ReportItemAttribute.sort)

    @classmethod
    def count_all(cls, is_completed):
        return cls.query.filter_by(completed=is_completed).count()

    @classmethod
    def find(cls, report_item_id):
        report_item = cls.query.get(report_item_id)
        return report_item

    @classmethod
    def find_by_uuid(cls, report_item_uuid):
        report_item = cls.query.filter_by(uuid=report_item_uuid)
        return report_item

    @classmethod
    def allowed_with_acl(cls, report_item_id, user, see, access, modify):

        query = db.session.query(ReportItem.id).distinct().group_by(ReportItem.id).filter(
            ReportItem.id == report_item_id)

        query = query.outerjoin(ACLEntry, or_(and_(ReportItem.uuid == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.REPORT_ITEM),
                                              and_(cast(ReportItem.report_item_type_id,
                                                        sqlalchemy.String) == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE)))

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_for_sync(cls, last_synced, report_item_types):
        report_item_type_ids = set()
        for report_item_type in report_item_types:
            report_item_type_ids.add(report_item_type.id)

        last_sync_time = datetime.now()

        query = cls.query.filter(ReportItem.last_updated >= last_synced, ReportItem.last_updated <= last_sync_time,
                                 ReportItem.report_item_type_id.in_(report_item_type_ids))

        report_items = query.all()

        for report_item in report_items:
            for attribute in report_item.attributes:
                attribute.attribute_group_item_title = attribute.attribute_group_item.title

        report_item_remote_schema = ReportItemRemoteSchema(many=True)
        items = report_item_remote_schema.dump(report_items)

        return items, last_sync_time

    @classmethod
    def get(cls, group, filter, offset, limit, user):

        if group:
            query = cls.query.filter(ReportItem.remote_user == group)
        else:
            query = db.session.query(ReportItem, func.count().filter(ACLEntry.id > 0).label("acls"),
                                     func.count().filter(ACLEntry.access == True).label("access"),
                                     func.count().filter(ACLEntry.modify == True).label("modify")).distinct().group_by(
                ReportItem.id)

            query = query.filter(ReportItem.remote_user == None)

            query = query.outerjoin(ACLEntry, or_(and_(ReportItem.uuid == ACLEntry.item_id,
                                                       ACLEntry.item_type == ItemType.REPORT_ITEM),
                                                  and_(cast(ReportItem.report_item_type_id,
                                                            sqlalchemy.String) == ACLEntry.item_id,
                                                       ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE)))
            query = ACLEntry.apply_query(query, user, True, False, False)

        if 'search' in filter and filter['search'] != '':
            search_string = '%' + filter['search'].lower() + '%'
            query = query.join(ReportItemAttribute, ReportItem.id == ReportItemAttribute.report_item_id).filter(or_(
                func.lower(ReportItemAttribute.value).like(search_string),
                func.lower(ReportItem.title).like(search_string),
                func.lower(ReportItem.title_prefix).like(search_string)))

        if 'completed' in filter and filter['completed'].lower() == "true":
            query = query.filter(ReportItem.completed == True)

        if 'incompleted' in filter and filter['incompleted'].lower() == "true":
            query = query.filter(ReportItem.completed == False)

        if 'range' in filter and filter['range'] != 'ALL':
            date_limit = datetime.now()
            if filter['range'] == 'TODAY':
                date_limit = date_limit.replace(hour=0, minute=0, second=0, microsecond=0)

            if filter['range'] == 'WEEK':
                date_limit = date_limit.replace(day=date_limit.day - date_limit.weekday(), hour=0, minute=0, second=0,
                                                microsecond=0)

            if filter['range'] == 'MONTH':
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            query = query.filter(ReportItem.created >= date_limit)

        if 'sort' in filter:
            if filter['sort'] == 'DATE_DESC':
                query = query.order_by(db.desc(ReportItem.created))

            elif filter['sort'] == 'DATE_ASC':
                query = query.order_by(db.asc(ReportItem.created))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def identical(cls, uuid):
        return db.session.query(db.exists().where(ReportItem.uuid == uuid)).scalar()

    @classmethod
    def get_by_cpe(cls, cpes):

        if len(cpes) > 0:
            query_string = "SELECT DISTINCT report_item_id FROM report_item_cpe WHERE value LIKE ANY(:cpes) OR {}"
            params = {'cpes': cpes}

            inner_query = ""
            for i in range(len(cpes)):
                if i > 0:
                    inner_query += " OR "
                param = "cpe" + str(i)
                inner_query += ":" + param + " LIKE value"
                params[param] = cpes[i]

            result = db.engine.execute(text(query_string.format(inner_query)), params)

            return [row[0] for row in result]
        else:
            return []

    @classmethod
    def get_json(cls, group, filter, offset, limit, user):
        results, count = cls.get(group, filter, offset, limit, user)
        report_items = []
        if group:
            for result in results:
                report_item = result
                report_item.see = True
                report_item.access = True
                report_item.modify = False
                report_items.append(report_item)
        else:
            for result in results:
                report_item = result.ReportItem
                report_item.see = True
                report_item.access = result.access > 0 or result.acls == 0
                report_item.modify = result.modify > 0 or result.acls == 0
                report_items.append(report_item)

        report_items_schema = ReportItemPresentationSchema(many=True)
        return {'total_count': count, 'items': report_items_schema.dump(report_items)}

    @classmethod
    def get_detail_json(cls, id):
        report_item = cls.query.get(id)
        report_item_schema = ReportItemSchema()
        return report_item_schema.dump(report_item)

    @classmethod
    def get_groups(cls):
        result = db.session.query(ReportItem.remote_user).distinct().group_by(ReportItem.remote_user).filter(
            ReportItem.remote_user != None).all()
        groups = set()
        for row in result:
            groups.add(row[0])

        return list(groups)

    @classmethod
    def add_report_item(cls, report_item_data, user):
        report_item_schema = NewReportItemSchema()
        report_item = report_item_schema.load(report_item_data)

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return 'Unauthorized access to report item type', 401

        report_item.user_id = user.id
        for attribute in report_item.attributes:
            attribute.user_id = user.id

        report_item.update_cpes()

        db.session.add(report_item)
        db.session.commit()

        return report_item, 200

    @classmethod
    def add_remote_report_items(cls, report_item_data, remote_node_name):
        report_item_schema = NewReportItemSchema(many=True)
        report_items = report_item_schema.load(report_item_data)

        for report_item in report_items:
            original_report_item = cls.find_by_uuid(report_item.uuid)
            if original_report_item is None:
                report_item.remote_user = remote_node_name
                db.session.add(report_item)
            else:
                original_report_item.title = report_item.title
                original_report_item.title_prefix = report_item.title_prefix
                original_report_item.completed = report_item.completed
                original_report_item.last_updated = datetime.now()
                original_report_item.attributes = report_item.attributes

        db.session.commit()

    @classmethod
    def update_report_item(cls, id, data, user):
        modified = False
        new_attribute = None
        report_item = cls.query.get(id)
        if report_item is not None:
            if 'update' in data:
                if 'title' in data:
                    if report_item.title != data['title']:
                        modified = True
                        report_item.title = data['title']
                        data['title'] = ''

                if 'title_prefix' in data:
                    if report_item.title_prefix != data['title_prefix']:
                        modified = True
                        report_item.title_prefix = data['title_prefix']
                        data['title_prefix'] = ''

                if 'completed' in data:
                    if report_item.completed != data['completed']:
                        modified = True
                        report_item.completed = data['completed']
                        data['completed'] = ''

                if 'attribute_id' in data:
                    for attribute in report_item.attributes:
                        if attribute.id == data['attribute_id']:
                            if attribute.value != data['attribute_value']:
                                modified = True
                                attribute.value = data['attribute_value']
                                data['attribute_value'] = ''
                                attribute.user = user
                                attribute.last_updated = datetime.now()
                                break

            if 'add' in data:
                if 'attribute_id' in data:
                    modified = True
                    new_attribute = ReportItemAttribute(None, "", None, 0, None, data['attribute_group_item_id'], None)
                    new_attribute.user = user
                    report_item.attributes.append(new_attribute)

                if 'aggregate_ids' in data:
                    modified = True
                    for aggregate_id in data['aggregate_ids']:
                        aggregate = NewsItemAggregate.find(aggregate_id)
                        report_item.news_item_aggregates.append(aggregate)

                if 'remote_report_item_ids' in data:
                    modified = True
                    for remote_report_item_id in data['remote_report_item_ids']:
                        remote_report_item = ReportItem.find(remote_report_item_id)
                        report_item.remote_report_items.append(remote_report_item)

            if 'delete' in data:
                if 'attribute_id' in data:
                    attribute_to_delete = None
                    for attribute in report_item.attributes:
                        if attribute.id == data['attribute_id']:
                            attribute_to_delete = attribute
                            break

                    if attribute_to_delete is not None:
                        modified = True
                        report_item.attributes.remove(attribute_to_delete)

                if 'aggregate_id' in data:
                    aggregate_to_delete = None
                    for aggregate in report_item.news_item_aggregates:
                        if aggregate.id == data['aggregate_id']:
                            aggregate_to_delete = aggregate
                            break

                    if aggregate_to_delete is not None:
                        modified = True
                        report_item.news_item_aggregates.remove(aggregate_to_delete)

                if 'remote_report_item_id' in data:
                    remote_report_item_to_delete = None
                    for remote_report_item in report_item.remote_report_items:
                        if remote_report_item.id == data['remote_report_item_id']:
                            remote_report_item_to_delete = remote_report_item
                            break

                    if remote_report_item_to_delete is not None:
                        modified = True
                        report_item.remote_report_items.remove(remote_report_item_to_delete)

            if modified:
                report_item.last_updated = datetime.now()
                data['user_id'] = user.id
                data['report_item_id'] = int(id)
                report_item.update_cpes()

            db.session.commit()

            if new_attribute is not None:
                data['attribute_id'] = new_attribute.id

        return modified, data

    @classmethod
    def get_updated_data(cls, id, data):
        report_item = cls.query.get(id)
        if report_item is not None:
            if 'update' in data:
                if 'title' in data:
                    data['title'] = report_item.title

                if 'title_prefix' in data:
                    data['title_prefix'] = report_item.title_prefix

                if 'completed' in data:
                    data['completed'] = report_item.completed

                if 'attribute_id' in data:
                    for attribute in report_item.attributes:
                        if attribute.id == data['attribute_id']:
                            data['attribute_value'] = attribute.value
                            data['attribute_last_updated'] = attribute.last_updated.strftime('%d.%m.%Y - %H:%M')
                            data['attribute_user'] = attribute.user.name
                            break

            if 'add' in data:
                if 'aggregate_ids' in data:
                    schema = NewsItemAggregateSchema()
                    data['news_item_aggregates'] = []
                    for aggregate_id in data['aggregate_ids']:
                        aggregate = NewsItemAggregate.find(aggregate_id)
                        data['news_item_aggregates'].append(schema.dump(aggregate))

                if 'remote_report_item_ids' in data:
                    schema = RemoteReportItemSchema()
                    data['remote_report_items'] = []
                    for remote_report_item_id in data['remote_report_item_ids']:
                        remote_report_item = ReportItem.find(remote_report_item_id)
                        data['remote_report_items'].append(schema.dump(remote_report_item))

                if 'attribute_id' in data:
                    for attribute in report_item.attributes:
                        if attribute.id == data['attribute_id']:
                            data['attribute_value'] = attribute.value
                            data['binary_mime_type'] = attribute.binary_mime_type
                            data['binary_size'] = attribute.binary_size
                            data['binary_description'] = attribute.binary_description
                            data['attribute_last_updated'] = attribute.last_updated.strftime('%d.%m.%Y - %H:%M')
                            data['attribute_user'] = attribute.user.name
                            break

        return data

    @classmethod
    def add_attachment(cls, id, attribute_group_item_id, user, file, description):
        report_item = cls.query.get(id)
        file_data = file.read()
        new_attribute = ReportItemAttribute(None, file.filename, file.mimetype, len(file_data), description,
                                            attribute_group_item_id, None)
        new_attribute.user = user
        new_attribute.binary_data = file_data
        report_item.attributes.append(new_attribute)

        report_item.last_updated = datetime.now()

        data = dict()
        data['add'] = True
        data['user_id'] = user.id
        data['report_item_id'] = int(id)
        data['attribute_id'] = new_attribute.id

        db.session.commit()

        return data

    @classmethod
    def remove_attachment(cls, id, attribute_id, user):
        report_item = cls.query.get(id)
        attribute_to_delete = None
        for attribute in report_item.attributes:
            if attribute.id == attribute_id:
                attribute_to_delete = attribute
                break

        if attribute_to_delete is not None:
            report_item.attributes.remove(attribute_to_delete)

        report_item.last_updated = datetime.now()

        data = dict()
        data['delete'] = True
        data['user_id'] = user.id
        data['report_item_id'] = int(id)
        data['attribute_id'] = attribute_id

        db.session.commit()

        return data

    @classmethod
    def delete_report_item(cls, id):
        report_item = cls.query.get(id)
        if report_item is not None:
            db.session.delete(report_item)
            db.session.commit()
            return 'success', 200

    def update_cpes(self):
        self.report_item_cpes = []
        if self.completed is True:
            for attribute in self.attributes:
                attribute_group = AttributeGroupItem.find(attribute.attribute_group_item_id)
                if attribute_group.attribute.type == AttributeType.CPE:
                    self.report_item_cpes.append(ReportItemCpe(attribute.value))


class ReportItemCpe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())

    report_item_id = db.Column(db.Integer, db.ForeignKey('report_item.id'))
    report_item = db.relationship("ReportItem")

    def __init__(self, value):
        self.id = None
        self.value = value
