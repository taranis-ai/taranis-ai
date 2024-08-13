import os
from enum import Enum, auto
from typing import Any
from xml.etree.ElementTree import iterparse

from sqlalchemy import func, or_
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel


class AttributeType(Enum):
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    RADIO = auto()
    ENUM = auto()
    TEXT = auto()
    RICH_TEXT = auto()
    DATE = auto()
    TIME = auto()
    DATE_TIME = auto()
    LINK = auto()
    ATTACHMENT = auto()
    TLP = auto()
    CPE = auto()
    CVE = auto()
    CVSS = auto()
    STORY = auto()


class AttributeEnum(BaseModel):
    __tablename__ = "attribute_enum"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    index: Mapped[int] = db.Column(db.Integer)
    value: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    imported: Mapped[bool] = db.Column(db.Boolean, default=False)

    attribute_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("attribute.id", ondelete="CASCADE"))
    attribute: Mapped["Attribute"] = relationship("Attribute", cascade="all, delete")

    def __init__(self, index: int, value: str, description: str, attribute_id: int | None = None, imported: bool = False, id=None):
        if id:
            self.id = id
        self.index = index
        self.value = value
        self.description = description
        self.imported = imported
        if attribute_id:
            self.attribute_id = attribute_id

    @classmethod
    def get_all_for_attribute(cls, attribute_id):
        return cls.get_filtered(db.select(cls).filter_by(attribute_id=attribute_id).order_by(db.asc(cls.index))) or []

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.filter(
                or_(
                    AttributeEnum.value.ilike(f"%{search}%"),
                    AttributeEnum.description.ilike(f"%{search}%"),
                )
            )
        return query.order_by(db.asc(AttributeEnum.index))

    @classmethod
    def find_by_value(cls, attribute_id, value):
        return cls.get_first(db.select(cls).filter_by(attribute_id=attribute_id).filter(func.lower(AttributeEnum.value) == value.lower()))

    @classmethod
    def delete_for_attribute(cls, attribute_id):
        db.session.execute(db.delete(cls).where(cls.attribute_id == attribute_id))
        db.session.commit()

    @classmethod
    def delete_unused(cls, attribute_id, used_enums):
        db.session.execute(db.delete(cls).where(cls.attribute_id == attribute_id).where(cls.id.notin_(used_enums)))
        db.session.commit()

    @classmethod
    def delete_imported_for_attribute(cls, attribute_id):
        db.session.execute(db.delete(cls).where(cls.attribute_id == attribute_id, imported=True))
        db.session.commit()

    @classmethod
    def add_or_update(cls, data):
        if "id" not in data:
            return cls.add(data), 201
        if entry := cls.get(data["id"]):
            entry.update(data)
            db.session.commit()
            return entry, 200
        return cls.add(data), 201

    def to_dict(self):
        data = super().to_dict()
        data["attribute"] = self.attribute.to_dict()
        return data

    def to_small_dict(self):
        return super().to_dict()


class Attribute(BaseModel):
    __tablename__ = "attribute"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[AttributeType] = db.Column(db.Enum(AttributeType))
    default_value: Mapped[str] = db.Column(db.String(), default="")

    def __init__(self, name: str, description: str, attribute_type, default_value: str = "", id=None):
        if id:
            self.id = id
        self.name = name
        self.description = description
        self.type = attribute_type
        self.default_value = default_value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attribute":
        if attribute_type := data.pop("type", None):
            data["attribute_type"] = AttributeType[attribute_type]
        return cls(**data)

    @classmethod
    def filter_by_type(cls, attribute_type) -> "Attribute|None":
        return cls.get_first(db.select(cls).filter_by(type=attribute_type))

    @classmethod
    def filter_by_name(cls, name):
        return cls.get_first(db.select(cls).filter_by(name=name))

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(cls.name))

    @classmethod
    def add(cls, data):
        attribute_enums = data.pop("attribute_enums", None)
        item = cls.from_dict(data)
        db.session.add(item)
        db.session.commit()

        if attribute_enums:
            for enum in attribute_enums:
                enum["attribute_id"] = item.id
                AttributeEnum.add_or_update(enum)

            db.session.commit()

        return item

    @classmethod
    def update(cls, attribute_id, data) -> tuple[dict, int]:
        attribute = cls.get(attribute_id)
        if not attribute:
            return {"error": "Attribute not found"}, 404

        if attribute_enums := data.pop("attribute_enums", None):
            used_enums = [enum["id"] for enum in attribute_enums if "id" in enum]
            AttributeEnum.delete_unused(attribute_id, used_enums)
            for enum in attribute_enums:
                enum["attribute_id"] = attribute_id
                AttributeEnum.add_or_update(enum)

        for key, value in data.items():
            if hasattr(attribute, key) and key != "id":
                setattr(attribute, key, value)

        db.session.commit()
        return {"message": f"Attribute {attribute.name} updated", "id": attribute_id}, 200

    @classmethod
    def load_cve_from_file(cls, file_path):
        attribute = cls.get_first(db.select(cls).filter_by(type=AttributeType.CVE))
        if not attribute:
            attribute = Attribute("CVE", "Common Vulnerabilities and Exposures", AttributeType.CVE)
            db.session.add(attribute)
            db.session.commit()
        AttributeEnum.delete_imported_for_attribute(attribute.id)

        logger.error("Loading CVEs from file is not implemented yet")
        # TODO: Implement parser for https://github.com/CVEProject/cvelistV5
        db.session.commit()

    @classmethod
    def load_cpe_from_file(cls, file_path):
        attribute = cls.get_first(db.select(cls).filter_by(type=AttributeType.CPE))
        if not attribute:
            attribute = Attribute("CPE", "Common Platform Enumeration", AttributeType.CPE)
            db.session.add(attribute)
            db.session.commit()

        AttributeEnum.delete_imported_for_attribute(attribute.id)

        item_count = 0
        block_item_count = 0
        desc = ""
        for event, element in iterparse(file_path, events=("start", "end")):
            if event == "end":
                if element.tag == "{http://cpe.mitre.org/dictionary/2.0}title":
                    desc = element.text
                elif element.tag == "{http://cpe.mitre.org/dictionary/2.0}cpe-item":
                    attribute_enum = AttributeEnum(item_count, element.attrib["name"], desc)
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    desc = ""
                    if block_item_count == 1000:
                        logger.debug(f"Processed CPE items: {item_count}")
                        block_item_count = 0
                        db.session.commit()

        logger.debug(f"Processed CPE items: {str(item_count)}")
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

    def get_tag(self):
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
            AttributeType.STORY: "mdi-book-open-outline",
        }
        return switcher.get(self.type, "mdi-textbox")

    def to_dict(self):
        data = super().to_dict()
        attribute_enums = AttributeEnum.get_all_for_attribute(self.id)
        data["attribute_enums"] = [attribute_enum.to_small_dict() for attribute_enum in attribute_enums]
        data["type"] = self.type.name
        data["tag"] = self.get_tag()
        return data

    def to_report_item_dict(self):
        data = super().to_dict()
        attribute_enums = AttributeEnum.get_all_for_attribute(self.id)
        data["attribute_enums"] = [attribute_enum.to_small_dict() for attribute_enum in attribute_enums]
        data["type"] = self.type.name
        return data
