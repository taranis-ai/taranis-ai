import uuid
from typing import Any
from enum import StrEnum, auto
from sqlalchemy.sql import Select
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.parameter_value import ParameterValue
from core.model.base_model import BaseModel


class COLLECTOR_TYPES(StrEnum):
    RSS_COLLECTOR = auto()
    EMAIL_COLLECTOR = auto()
    TWITTER_COLLECTOR = auto()
    SIMPLE_WEB_COLLECTOR = auto()
    RT_COLLECTOR = auto()
    MISP_COLLECTOR = auto()
    MANUAL_COLLECTOR = auto()


class BOT_TYPES(StrEnum):
    ANALYST_BOT = auto()
    GROUPING_BOT = auto()
    NLP_BOT = auto()
    IOC_BOT = auto()
    TAGGING_BOT = auto()
    STORY_BOT = auto()
    SUMMARY_BOT = auto()
    WORDLIST_BOT = auto()
    SENTIMENT_ANALYSIS_BOT = auto()
    CYBERSEC_CLASSIFIER_BOT = auto()


class PRESENTER_TYPES(StrEnum):
    PDF_PRESENTER = auto()
    HTML_PRESENTER = auto()
    TEXT_PRESENTER = auto()
    JSON_PRESENTER = auto()


class PUBLISHER_TYPES(StrEnum):
    FTP_PUBLISHER = auto()
    SFTP_PUBLISHER = auto()
    EMAIL_PUBLISHER = auto()
    WORDPRESS_PUBLISHER = auto()
    MISP_PUBLISHER = auto()


class WORKER_TYPES(StrEnum):
    RSS_COLLECTOR = auto()
    EMAIL_COLLECTOR = auto()
    TWITTER_COLLECTOR = auto()
    SIMPLE_WEB_COLLECTOR = auto()
    MANUAL_COLLECTOR = auto()
    RT_COLLECTOR = auto()
    MISP_COLLECTOR = auto()
    ANALYST_BOT = auto()
    GROUPING_BOT = auto()
    NLP_BOT = auto()
    IOC_BOT = auto()
    TAGGING_BOT = auto()
    STORY_BOT = auto()
    SUMMARY_BOT = auto()
    SENTIMENT_ANALYSIS_BOT = auto()
    CYBERSEC_CLASSIFIER_BOT = auto()
    WORDLIST_BOT = auto()
    PDF_PRESENTER = auto()
    HTML_PRESENTER = auto()
    TEXT_PRESENTER = auto()
    JSON_PRESENTER = auto()
    FTP_PUBLISHER = auto()
    SFTP_PUBLISHER = auto()
    EMAIL_PUBLISHER = auto()
    WORDPRESS_PUBLISHER = auto()
    MISP_PUBLISHER = auto()
    MISP_CONNECTOR = auto()


class CONNECTOR_TYPES(StrEnum):
    MISP_CONNECTOR = auto()


class WORKER_CATEGORY(StrEnum):
    COLLECTOR = auto()
    BOT = auto()
    PRESENTER = auto()
    PUBLISHER = auto()
    CONNECTOR = auto()


class Worker(BaseModel):
    __tablename__ = "worker"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[WORKER_TYPES] = db.Column(db.Enum(WORKER_TYPES), nullable=False, unique=True)
    category: Mapped[WORKER_CATEGORY] = db.Column(db.Enum(WORKER_CATEGORY), nullable=False)
    parameters: Mapped[list["ParameterValue"]] = relationship("ParameterValue", secondary="worker_parameter_value", cascade="all")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.category = type.split("_")[-1]
        self.parameters = ParameterValue.get_or_create_from_list(parameters)

    @classmethod
    def add(cls, data) -> tuple[dict[str, str], int]:
        if cls.filter_by_type(data["type"]):
            return {"error": f"Worker with type {data['type']} already exists"}, 409
        worker = cls.from_dict(data)
        db.session.add(worker)
        db.session.commit()
        return {"message": f"Worker {worker.name} added", "id": worker.id}, 201

    @classmethod
    def get_type(cls, id) -> "WORKER_TYPES":
        if worker := cls.get(id):
            return worker.type
        raise ValueError(f"Worker {id} not found")

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                db.or_(
                    Worker.name.ilike(f"%{search}%"),
                    Worker.description.ilike(f"%{search}%"),
                )
            )

        if category := filter_args.get("category"):
            if bool(WORKER_CATEGORY(category)):
                query = query.where(Worker.category == category)

        if type := filter_args.get("type"):
            if bool(WORKER_TYPES(type)):
                query = query.where(Worker.type == type)

        return query.order_by(db.asc(Worker.name))

    @classmethod
    def filter_by_type(cls, worker_type) -> "Worker | None":
        return db.session.execute(db.select(cls).filter(cls.type == worker_type)).scalar_one_or_none()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "parameters": {parameter.parameter: parameter.value for parameter in self.parameters},
        }

    @classmethod
    def get_parameters(cls, worker_type: str) -> list[ParameterValue]:
        if worker := cls.filter_by_type(worker_type):
            return [parameter.get_copy() for parameter in worker.parameters]
        return []

    @classmethod
    def parse_parameters(cls, worker_type: str, parameters) -> list[ParameterValue]:
        default_parameters = Worker.get_parameters(worker_type)

        if not parameters:
            return default_parameters

        parsed_parameters = cls._get_or_create_parameters(parameters)
        missing_parameters = cls._get_missing_parameters(default_parameters, parsed_parameters)

        return parsed_parameters + missing_parameters

    @classmethod
    def _get_or_create_parameters(cls, parameters) -> list[ParameterValue]:
        return ParameterValue.get_or_create_from_list(parameters=parameters)

    @classmethod
    def _get_missing_parameters(cls, default_parameters, parsed_parameters) -> list[ParameterValue]:
        parsed_parameter_names = {pp.parameter for pp in parsed_parameters}
        return [wp for wp in default_parameters if wp.parameter not in parsed_parameter_names]

    @classmethod
    def get_parameter_map(cls):
        if workers := cls.get_all_for_collector():
            return {worker.type: cls._generate_parameters_data(worker) for worker in workers}
        return {}

    @classmethod
    def _generate_parameters_data(cls, worker):
        return [cls._construct_parameter_data(parameter) for parameter in worker.parameters]

    @classmethod
    def _construct_parameter_data(cls, parameter):
        from core.model.word_list import WordList

        data = {
            "name": parameter.parameter,
            "label": parameter.parameter,
            "parent": "parameters",
            "type": parameter.type,
            "rules": parameter.rules.split(",") if parameter.rules else [],
        }

        if parameter.parameter in ["TAGGING_WORDLISTS"]:
            word_lists = WordList.get_by_filter({"usage": 4})
            data["items"] = [{"name": wordlist.name, "description": wordlist.description} for wordlist in word_lists] if word_lists else []
            data["headers"] = [{"title": "Name", "key": "name"}, {"title": "Description", "key": "description"}]
            data["value"] = []
            data["disabled"] = True

        return data

    def update(self, item: dict[str, Any]) -> tuple[dict, int]:
        if name := item.get("name"):
            self.name = name
        if description := item.get("description"):
            self.description = description

        if update_parameters := item.get("parameters"):
            self._update_parameters(update_parameters)

        db.session.commit()
        return self.to_dict(), 200

    def _update_parameters(self, update_parameters: list):
        updated_params = {param.parameter: param for param in ParameterValue.get_or_create_from_list(update_parameters)}
        existing_parameters = {param.parameter: param for param in self.parameters}

        for param_name, update_parameter in updated_params.items():
            if param_name in existing_parameters:
                parameter = existing_parameters[param_name]
                parameter.value = update_parameter.value
                parameter.type = update_parameter.type
                parameter.rules = update_parameter.rules
            else:
                self.parameters.append(update_parameter)
        self.parameters = [p for p in self.parameters if p.parameter in updated_params]
        return self.parameters


class WorkerParameterValue(BaseModel):
    worker_id = db.Column(db.String, db.ForeignKey("worker.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
