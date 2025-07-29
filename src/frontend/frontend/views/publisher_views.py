from typing import Any
from flask import request, render_template

from frontend.utils.form_data_parser import parse_formdata
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from models.admin import PublisherPreset, ProductType, ReportItemType, WorkerParameter, WorkerParameterValue, ProductTypeParameter
from models.types import PRESENTER_TYPES, PUBLISHER_TYPES

from frontend.filters import render_item_type
from frontend.log import logger


class PublisherView(BaseView):
    model = PublisherPreset
    icon = "envelope-open"
    _index = 140

    publisher_types = {
        member.name.lower(): {"id": member.name.upper(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in PUBLISHER_TYPES
    }

    @classmethod
    def get_worker_parameters(cls, publisher_type: str) -> list[WorkerParameterValue]:
        dpl = DataPersistenceLayer()
        all_parameters = dpl.get_objects(WorkerParameter)
        match = next((wp for wp in all_parameters if wp.id == publisher_type), None)
        return match.parameters if match else []

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        parameters = {}
        parameter_values = {}
        publisher = base_context.get(cls.model_name())
        if publisher and (hasattr(publisher, "type") and (publisher_type := publisher.type)):
            parameter_values = publisher.parameters
            parameters = cls.get_worker_parameters(publisher_type=publisher_type.name.lower())

        base_context |= {
            "publisher_types": cls.publisher_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
        }
        return base_context

    @classmethod
    def get_publisher_parameters_view(cls, publisher_id: str, publisher_type: str):
        publisher_type = publisher_type.lower()
        if not publisher_id and not publisher_type:
            logger.warning("No Publisher ID or Publisher Type provided.")

        parameters = cls.get_worker_parameters(publisher_type)

        return render_template("partials/worker_parameters.html", parameters=parameters)


class ProductTypeView(BaseView):
    model = ProductType
    icon = "envelope"
    _index = 150

    presenter_types = {
        member.name.lower(): {"id": member.name.upper(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in PRESENTER_TYPES
    }

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        parameters = {}
        presenter = base_context.get(cls.model_name())
        if presenter and (hasattr(presenter, "type") and (presenter_type := presenter.type)):
            parameters = cls.get_product_type_parameters(presenter_type=presenter_type.name.lower())
        base_context |= {
            "presenter_types": cls.presenter_types.values(),
            "report_types": [rt.model_dump() for rt in dpl.get_objects(ReportItemType)],
            "parameters": parameters,
        }
        return base_context

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            obj = cls.model(**form_data)
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def get_columns(cls):
        return [
            {"title": "ID", "field": "id", "sortable": False, "renderer": None},
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {"title": "Type", "field": "type", "sortable": False, "renderer": render_item_type},
        ]

    @classmethod
    def get_product_type_parameters(cls, presenter_type: str) -> list[WorkerParameterValue]:
        dpl = DataPersistenceLayer()
        endpoint = dpl.get_endpoint(ProductTypeParameter)
        if result := dpl.api.api_get(endpoint):
            all_parameters = [ProductTypeParameter(**object) for object in result.get("items", [])]
            match = next((wp for wp in all_parameters if wp.id == presenter_type), None)
            return match.parameters if match else []
        return []

    @classmethod
    def get_product_type_parameters_view(cls, presenter_type: str):
        presenter_type = presenter_type.lower()
        if not presenter_type:
            logger.warning("No Product Type ID or Presenter Type provided.")
        parameters = cls.get_product_type_parameters(presenter_type)
        return render_template("partials/worker_parameters.html", parameters=parameters, preserve=False)
