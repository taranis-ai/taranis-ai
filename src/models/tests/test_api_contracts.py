from dataclasses import replace

import pytest
from pydantic import TypeAdapter, ValidationError

from models.api import OperationContract
from models.api_operations import OPERATIONS, find_operation, validate_outgoing_request
from models.base import TaranisBaseModel


def test_operation_resolution_and_task_payload():
    assert len({(operation.method, operation.path) for operation in OPERATIONS}) == len(OPERATIONS)
    operation = find_operation("GET", "/tasks/runs?limit=1")
    assert operation is not None and operation.path == "/tasks/runs"
    filters = operation.query.model_validate({"job_ids": ["one", "two"], "limit": "1"})
    assert filters.job_ids == ["one", "two"]
    assert filters.limit == 1
    assert validate_outgoing_request("GET", "/tasks/runs?job_ids=one&job_ids=two", params={"limit": "1"}) is operation
    assert validate_outgoing_request("GET", "/tasks/runs", params={"job_ids": ("one", "two"), "search": None, "limit": ()}) is operation

    operation = find_operation("POST", "/tasks")
    assert operation is not None
    submission = operation.validate_body({"task_id": "one", "status": "SUCCESS", "result": {"message": "Done", "data": None}})
    assert submission.id == "one"
    assert submission.result.data is None
    assert submission.model_fields_set == {"id", "status", "result"}
    with pytest.raises(ValidationError):
        operation.validate_body({"id": "one", "status": "SUCCESS", "result": {}})
    with pytest.raises(ValidationError):
        operation.response(200).validate({"message": "Done"}, content_type="application/json")


def test_bodyless_health_response_and_content_type():
    operation = find_operation("GET", "/health")
    assert operation is not None
    assert operation.validate_body(None) is None
    assert operation.validate_body({}) is None
    with pytest.raises(ValueError):
        operation.validate_body({"unexpected": "value"})
    with pytest.raises(ValidationError):
        operation.response(503).validate({"healthy": False}, content_type="application/json")
    with pytest.raises(ValueError):
        operation.response(200).validate({}, content_type="text/html")


def test_validation_error_messages_preserve_precedence():
    operation = OperationContract(
        "POST",
        "/example",
        {},
        field_error_messages={"0:int_parsing": "Specific error", "0": "Field error", "*": "Item error"},
        validation_error_message="Invalid payload",
        validation_error_model=TaranisBaseModel,
    )
    with pytest.raises(ValidationError) as error:
        TypeAdapter(list[int]).validate_python(["invalid"])

    assert operation.validation_error_response(error.value) == {"error": "Specific error"}
    operation = replace(operation, field_error_messages={"0": "Field error", "*": "Item error"})
    assert operation.validation_error_response(error.value) == {"error": "Field error"}
    operation = replace(operation, field_error_messages={"*": "Item error"})
    assert operation.validation_error_response(error.value) == {"error": "Item error"}
    operation = replace(operation, field_error_messages={})
    assert operation.validation_error_response(error.value) == {"error": "Invalid payload"}
    operation = replace(operation, validation_error_message=None)
    assert operation.validation_error_response(error.value)["error"].startswith("Validation failed for model 'TaranisBaseModel':")
    operation = replace(operation, validation_error_model=None)
    assert operation.validation_error_response(error.value)["error"].startswith("Invalid request: 0:")


def test_partial_updates_csv_and_required_client_contracts():
    from models.api import partial_model
    from models.config_api import UserInput
    from models.imports import CSV_WORD_LIST

    update = partial_model(UserInput)
    assert update.model_validate({}).model_dump(exclude_unset=True) == {}
    assert update.model_validate({"organization": None}).model_dump(exclude_unset=True, exclude_none=False) == {"organization": None}
    with pytest.raises(ValidationError):
        update.model_validate({"username": None})
    imported = CSV_WORD_LIST.validate_python("value,category\nexample,domain\n", context={"filename": "words.csv"})
    assert imported.data[0].name == "words.csv"
    assert imported.data[0].entries[0].value == "example"
    for invalid_csv in ("", "value,category\n" + "x" * 140000 + ",misc\n"):
        with pytest.raises(ValidationError):
            CSV_WORD_LIST.validate_python(invalid_csv)
    with pytest.raises(ValueError, match="Missing API operation contract"):
        validate_outgoing_request("GET", "/unregistered")


def test_nested_configuration_and_runtime_ranges():
    from models.config_api import DagRequest, ReportTypeInput
    from models.workspace_api import ClusterQuery

    validate_outgoing_request("GET", "/analyze/report-items", params={"completed": "", "timefrom": ""})
    preview = DagRequest.model_validate({"index": "1", "parameters": {"RUN_AFTER_COLLECTOR": "false"}})
    assert preview.type is None
    report = ReportTypeInput.model_validate(
        {
            "title": "Report",
            "attribute_groups": [
                {"title": "Group", "index": 0, "attribute_group_items": [{"title": "Story", "index": 0, "attribute": "Story"}]}
            ],
        }
    )
    assert report.attribute_groups[0].attribute_group_items[0].attribute == "Story"
    validate_outgoing_request("PUT", "/worker/word-list/words", b"value,category\nexample,domain\n", content_type="text/csv")
    with pytest.raises(ValidationError):
        ClusterQuery.model_validate({"days": 10**12})
    with pytest.raises(ValidationError):
        ClusterQuery.model_validate({"page": 1024, "limit": -9016003946094601})


def test_worker_resources_require_identity_and_product_attributes_keep_groups():
    from models.worker_api import WorkerProduct

    operation = find_operation("GET", "/worker/bots/bot")
    assert operation is not None
    with pytest.raises(ValidationError):
        operation.response(200).validate({"name": "Bot", "type": "nlp_bot"}, content_type="application/json")
    product = WorkerProduct.model_validate(
        {
            "id": "product",
            "title": "Product",
            "type": "html_presenter",
            "type_id": "type",
            "mime_type": "text/html",
            "render_revision": "revision",
            "parameters": {},
            "report_items": [{"id": "report", "attributes": {"Overview": {"Text": "Content", "Empty": None}}, "stories": []}],
        }
    )
    assert product.report_items[0].attributes["Overview"]["Text"] == "Content"
