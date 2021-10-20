from managers.db_manager import db
from taranisng.schema.report_item_type import *
from taranisng.schema.attribute import *
from marshmallow import post_load
from sqlalchemy import orm, func, or_, and_
from model.acl_entry import ACLEntry
from taranisng.schema.acl_entry import ItemType
import sqlalchemy
from sqlalchemy.sql.expression import cast
from model.attribute import Attribute


class NewAttributeGroupItemSchema(AttributeGroupItemSchema):
    attribute_id = fields.Integer()

    @post_load
    def make_attribute_group_item(self, data, **kwargs):
        return AttributeGroupItem(**data)


class AttributeGroupItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    index = db.Column(db.Integer)
    min_occurrence = db.Column(db.Integer)
    max_occurrence = db.Column(db.Integer)

    attribute_group_id = db.Column(db.Integer, db.ForeignKey('attribute_group.id'))
    attribute_group = db.relationship("AttributeGroup")

    attribute_id = db.Column(db.Integer, db.ForeignKey('attribute.id'))
    attribute = db.relationship("Attribute")

    def __init__(self, id, title, description, index, min_occurrence, max_occurrence, attribute_id):
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_id = attribute_id

    @classmethod
    def find(cls, id):
        return cls.query.get(id)

    @staticmethod
    def sort(attribute_group_item):
        return attribute_group_item.index


class NewAttributeGroupSchema(AttributeGroupBaseSchema):
    attribute_group_items = fields.Nested('NewAttributeGroupItemSchema', many=True)

    @post_load
    def make_attribute_group(self, data, **kwargs):
        return AttributeGroup(**data)


class AttributeGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    section = db.Column(db.Integer)
    section_title = db.Column(db.String())
    index = db.Column(db.Integer)

    report_item_type_id = db.Column(db.Integer, db.ForeignKey('report_item_type.id'))
    report_item_type = db.relationship("ReportItemType")

    attribute_group_items = db.relationship('AttributeGroupItem', back_populates="attribute_group",
                                            cascade="all, delete-orphan")

    def __init__(self, id, title, description, section, section_title, index, attribute_group_items):
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.attribute_group_items = attribute_group_items

    @orm.reconstructor
    def reconstruct(self):
        self.attribute_group_items.sort(key=AttributeGroupItem.sort)

    @staticmethod
    def sort(attribute_group):
        return attribute_group.index

    def update(self, updated_attribute_group):
        self.title = updated_attribute_group.title
        self.description = updated_attribute_group.description
        self.section = updated_attribute_group.section
        self.section_title = updated_attribute_group.section_title
        self.index = updated_attribute_group.index

        for updated_attribute_group_item in updated_attribute_group.attribute_group_items:
            found = False
            for attribute_group_item in self.attribute_group_items:
                if updated_attribute_group_item.id == attribute_group_item.id:
                    attribute_group_item.title = updated_attribute_group_item.title
                    attribute_group_item.description = updated_attribute_group_item.description
                    attribute_group_item.index = updated_attribute_group_item.index
                    attribute_group_item.min_occurrence = updated_attribute_group_item.min_occurrence
                    attribute_group_item.max_occurrence = updated_attribute_group_item.max_occurrence
                    attribute_group_item.attribute_id = updated_attribute_group_item.attribute_id
                    found = True
                    break

            if found is False:
                updated_attribute_group_item.attribute_group = None
                self.attribute_group_items.append(updated_attribute_group_item)

        for attribute_group_item in self.attribute_group_items[:]:
            found = False
            for updated_attribute_group_item in updated_attribute_group.attribute_group_items:
                if updated_attribute_group_item.id == attribute_group_item.id:
                    found = True
                    break

            if found is False:
                self.attribute_group_items.remove(attribute_group_item)


class NewReportItemTypeSchema(ReportItemTypeBaseSchema):
    attribute_groups = fields.Nested('NewAttributeGroupSchema', many=True)

    @post_load
    def make_report_item_type(self, data, **kwargs):
        return ReportItemType(**data)


class ReportItemType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    attribute_groups = db.relationship('AttributeGroup', back_populates="report_item_type",
                                       cascade="all, delete-orphan")

    def __init__(self, id, title, description, attribute_groups):
        self.id = None
        self.title = title
        self.description = description
        self.attribute_groups = attribute_groups
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.subtitle = self.description
        self.tag = "mdi-file-table-outline"
        self.attribute_groups.sort(key=AttributeGroup.sort)

    @classmethod
    def find(cls, id):
        return cls.query.get(id)

    @classmethod
    def get_all(cls):
        return cls.query.order_by(ReportItemType.title).all()

    @classmethod
    def allowed_with_acl(cls, report_item_type_id, user, see, access, modify):

        query = db.session.query(ReportItemType.id).distinct().group_by(ReportItemType.id).filter(
            ReportItemType.id == report_item_type_id)

        query = query.outerjoin(ACLEntry, and_(cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id,
                                               ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE))

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(ReportItemType.id)

        if acl_check is True:
            query = query.outerjoin(ACLEntry, and_(cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE))
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(ReportItemType.title).like(search_string),
                func.lower(ReportItemType.description).like(search_string)))

        return query.order_by(db.asc(ReportItemType.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        report_item_types, count = cls.get(search, user, acl_check)
        for report_item_type in report_item_types:
            for attribute_group in report_item_type.attribute_groups:
                for attribute_group_item in attribute_group.attribute_group_items:
                    attribute_group_item.attribute.attribute_enums = Attribute.get_enums(
                        attribute_group_item.attribute)

        report_item_type_schema = ReportItemTypePresentationSchema(many=True)
        return {'total_count': count, 'items': report_item_type_schema.dump(report_item_types)}

    @classmethod
    def add_report_item_type(cls, report_item_type_data):
        report_item_type_schema = NewReportItemTypeSchema()
        report_item_type = report_item_type_schema.load(report_item_type_data)
        db.session.add(report_item_type)
        db.session.commit()

    @classmethod
    def update(cls, report_type_id, data):
        schema = NewReportItemTypeSchema()
        updated_report_type = schema.load(data)
        report_type = cls.query.get(report_type_id)
        report_type.title = updated_report_type.title
        report_type.description = updated_report_type.description

        for updated_attribute_group in updated_report_type.attribute_groups:
            found = False
            for attribute_group in report_type.attribute_groups:
                if updated_attribute_group.id is not None and updated_attribute_group.id == attribute_group.id:
                    attribute_group.update(updated_attribute_group)
                    found = True
                    break

            if found is False:
                updated_attribute_group.report_item_type = None
                report_type.attribute_groups.append(updated_attribute_group)

        for attribute_group in report_type.attribute_groups[:]:
            found = False
            for updated_attribute_group in updated_report_type.attribute_groups:
                if updated_attribute_group.id == attribute_group.id:
                    found = True
                    break

            if found is False:
                report_type.attribute_groups.remove(attribute_group)

        db.session.commit()

    @classmethod
    def delete_report_item_type(cls, id):
        report_item_type = cls.query.get(id)
        db.session.delete(report_item_type)
        db.session.commit()
