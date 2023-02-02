import os
from xml.etree.ElementTree import iterparse
from marshmallow import fields, post_load
from sqlalchemy import orm, func, or_

from core.managers.log_manager import logger
from core.managers.db_manager import db
from shared.schema.attribute import (
    AttributeBaseSchema,
    AttributeEnumSchema,
    AttributeType,
    AttributeValidator,
    AttributePresentationSchema,
)


class NewAttributeEnumSchema(AttributeEnumSchema):
    @post_load
    def make_attribute_enum(self, data, **kwargs):
        return AttributeEnum(**data)


class AttributeEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)
    value = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    imported = db.Column(db.Boolean, default=False)

    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute = db.relationship("Attribute")

    def __init__(self, id, index, value, description):
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.index = index
        self.value = value
        self.description = description

    @classmethod
    def count_for_attribute(cls, attribute_id):
        return cls.query.filter_by(attribute_id=attribute_id).count()

    @classmethod
    def get_all_for_attribute(cls, attribute_id):
        return cls.query.filter_by(attribute_id=attribute_id).order_by(db.asc(AttributeEnum.index)).all()

    @classmethod
    def get_for_attribute(cls, attribute_id, search, offset, limit):
        query = cls.query.filter_by(attribute_id=attribute_id)
        if search:
            search_string = "%" + search + "%"
            query = query.filter(
                or_(
                    AttributeEnum.value.like(search_string),
                    AttributeEnum.description.like(search_string),
                )
            )

        query = query.order_by(db.asc(AttributeEnum.index))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def find_by_value(cls, attribute_id, value):
        return cls.query.filter_by(attribute_id=attribute_id).filter(func.lower(AttributeEnum.value) == value.lower()).first()

    @classmethod
    def get_for_attribute_json(cls, attribute_id, search, offset, limit):
        attribute_enums, total_count = cls.get_for_attribute(attribute_id, search, offset, limit)
        attribute_enums_schema = AttributeEnumSchema(many=True)
        return {
            "total_count": total_count,
            "items": attribute_enums_schema.dump(attribute_enums),
        }

    @classmethod
    def delete_for_attribute(cls, attribute_id):
        cls.query.filter_by(attribute_id=attribute_id).delete()
        db.session.commit()

    @classmethod
    def delete_imported_for_attribute(cls, attribute_id):
        cls.query.filter_by(attribute_id=attribute_id, imported=True).delete()
        db.session.commit()

    @classmethod
    def add(cls, attribute_id, data):

        count = 0
        if data["delete_existing"] is True:
            cls.delete_for_attribute(attribute_id)
        else:
            count = cls.count_for_attribute(attribute_id)

        attribute_enums_schema = NewAttributeEnumSchema(many=True)
        attribute_enums = attribute_enums_schema.load(data["items"])

        for attribute_enum in attribute_enums:
            original_attribute_enum = cls.find_by_value(attribute_id, attribute_enum.value)
            if original_attribute_enum is None:
                attribute_enum.attribute_id = attribute_id
                attribute_enum.index = count
                count += 1
                db.session.add(attribute_enum)
            else:
                original_attribute_enum.value = attribute_enum.value
                original_attribute_enum.description = attribute_enum.description

        db.session.commit()

    @classmethod
    def update(cls, enum_id, data):
        attribute_enums_schema = NewAttributeEnumSchema(many=True)
        attribute_enums = attribute_enums_schema.load(data)
        for attribute_enum in attribute_enums:
            original_attribute_enum = cls.query.get(enum_id)
            original_attribute_enum.value = attribute_enum.value
            original_attribute_enum.description = attribute_enum.description
            original_attribute_enum.imported = False

        db.session.commit()

    @classmethod
    def delete(cls, attribute_enum_id):
        db.session.delete(cls.query.get(attribute_enum_id))
        db.session.commit()


class NewAttributeSchema(AttributeBaseSchema):
    attribute_enums = fields.Nested(NewAttributeEnumSchema, many=True)

    @post_load
    def make_attribute(self, data, **kwargs):
        return Attribute(**data)


class Attribute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(AttributeType))
    default_value = db.Column(db.String())

    validator = db.Column(db.Enum(AttributeValidator))
    validator_parameter = db.Column(db.String())

    def __init__(
        self,
        id,
        name,
        description,
        type,
        default_value,
        validator,
        validator_parameter,
        attribute_enums,
    ):
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter
        self.attribute_enums = attribute_enums
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description

        switcher = {
            AttributeType.STRING: "mdi-form-textbox",
            AttributeType.NUMBER: "mdi-numeric",
            AttributeType.BOOLEAN: "mdi-checkbox-marked-outline",
            AttributeType.RADIO: "mdi-radiobox-marked",
            AttributeType.ENUM: "mdi-format-list-bulleted-type",
            AttributeType.TEXT: "mdi-form-textarea",
            AttributeType.RICH_TEXT: "mdi-format-font",
            AttributeType.DATE: "mdi-calendar-blank-outline",
            AttributeType.TIME: "clock-outline",
            AttributeType.DATE_TIME: "calendar-clock",
            AttributeType.LINK: "mdi-link",
            AttributeType.ATTACHMENT: "mdi-paperclip",
            AttributeType.TLP: "mdi-traffic-light",
            AttributeType.CPE: "mdi-laptop",
            AttributeType.CVE: "mdi-hazard-lights",
            AttributeType.CVSS: "mdi-counter",
        }
        self.tag = switcher.get(self.type, "mdi-textbox")

    @classmethod
    def get_all(cls):
        return cls.query.order_by(Attribute.name).all()

    @classmethod
    def find_by_type(cls, attribute_type):
        return cls.query.filter_by(type=attribute_type).first()

    @classmethod
    def find_by_id(cls, attribute_id):
        return cls.query.get(attribute_id)

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    Attribute.name.ilike(search_string),
                    Attribute.description.ilike(search_string),
                )
            )

        return query.order_by(db.asc(Attribute.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        attributes, total_count = cls.get(search)
        for attribute in attributes:
            if attribute.type == AttributeType.CPE or attribute.type == AttributeType.CVE:
                attribute.attribute_enums = []
            else:
                attribute.attribute_enums = AttributeEnum.get_all_for_attribute(attribute.id)

        attribute_schema = AttributePresentationSchema(many=True)
        return {"total_count": total_count, "items": attribute_schema.dump(attributes)}

    @classmethod
    def get_enums(cls, attribute):
        if attribute.type == AttributeType.RADIO or attribute.type == AttributeType.ENUM:
            return AttributeEnum.get_all_for_attribute(attribute.id)
        else:
            return []

    @classmethod
    def create_attribute(cls, attribute):
        db.session.add(attribute)
        db.session.commit()

        for attribute_enum in attribute.attribute_enums:
            attribute_enum.attribute_id = attribute.id
            db.session.add(attribute_enum)

        attribute.attribute_enums = []

        db.session.commit()

    @classmethod
    def add_attribute(cls, attribute_data):
        attribute_schema = NewAttributeSchema()
        attribute = attribute_schema.load(attribute_data)
        db.session.add(attribute)
        db.session.commit()

        count = 0
        for attribute_enum in attribute.attribute_enums:
            attribute_enum.attribute_id = attribute.id
            attribute_enum.index = count
            count += 1
            db.session.add(attribute_enum)

        attribute.attribute_enums = []

        db.session.commit()

    @classmethod
    def update(cls, attribute_id, data):
        schema = NewAttributeSchema()
        updated_attribute = schema.load(data)
        attribute = cls.query.get(attribute_id)
        attribute.name = updated_attribute.name
        attribute.description = updated_attribute.description
        attribute.type = updated_attribute.type
        attribute.default_value = updated_attribute.default_value
        attribute.validator = updated_attribute.validator
        attribute.validator_parameter = updated_attribute.validator_parameter
        db.session.commit()

    @classmethod
    def delete_attribute(cls, id):
        attribute = cls.query.get(id)
        AttributeEnum.delete_for_attribute(id)
        db.session.delete(attribute)
        db.session.commit()

    @classmethod
    def load_cve_from_file(cls, file_path):

        attribute = cls.query.filter_by(type=AttributeType.CVE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)

        item_count = 0
        block_item_count = 0
        desc = ""
        for event, element in iterparse(file_path, events=("start", "end")):
            if event == "end":
                if element.tag == "{http://cve.mitre.org/cve/downloads/1.0}desc":
                    desc = element.text
                elif element.tag == "{http://cve.mitre.org/cve/downloads/1.0}item":
                    attribute_enum = AttributeEnum(None, item_count, element.attrib["name"], desc)
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    desc = ""
                    if block_item_count == 1000:
                        logger.log_debug("Processed CVE items: " + str(item_count))
                        block_item_count = 0
                        db.session.commit()

        logger.log_debug("Processed CVE items: " + str(item_count))
        db.session.commit()

    @classmethod
    def load_cpe_from_file(cls, file_path):

        attribute = cls.query.filter_by(type=AttributeType.CPE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)

        item_count = 0
        block_item_count = 0
        desc = ""
        for event, element in iterparse(file_path, events=("start", "end")):
            if event == "end":
                logger.log_debug("Element: {}".format(element))
                if element.tag == "{http://cpe.mitre.org/dictionary/2.0}title":
                    desc = element.text
                elif element.tag == "{http://cpe.mitre.org/dictionary/2.0}cpe-item":
                    attribute_enum = AttributeEnum(None, item_count, element.attrib["name"], desc)
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    desc = ""
                    if block_item_count == 1000:
                        logger.log_debug("Processed CPE items: " + str(item_count))
                        block_item_count = 0
                        db.session.commit()

        logger.log_debug("Processed CPE items: " + str(item_count))
        db.session.commit()

    @classmethod
    def load_dictionaries(cls, dict_type):
        if dict_type == "cve":
            cve_update_file = os.getenv("CVE_UPDATE_FILE")
            if cve_update_file is not None and os.path.exists(cve_update_file):
                Attribute.load_cve_from_file(cve_update_file)

        if dict_type == "cpe":
            cpe_update_file = os.getenv("CPE_UPDATE_FILE")
            if cpe_update_file is not None and os.path.exists(cpe_update_file):
                Attribute.load_cpe_from_file(cpe_update_file)
