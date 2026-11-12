import re

import pytest
from pydantic import TypeAdapter, ValidationError

from models.api import partial_model
from models.api_operations import _OPERATIONS, OPERATIONS
from models.assessment_api import WebParameters
from models.config_api import UserInput
from models.content_api import ContentImport, ContentQuery
from models.imports import SourceImport
from models.realtime_api import Broadcast
from models.workspace_api import unchanged_proxy_url


def test_contract_inventory_has_unique_keys_and_usable_schemas():
    assert len(OPERATIONS) == len(_OPERATIONS)
    for (method, path), operation in OPERATIONS.items():
        assert (method, path) == (operation.method, operation.path)
        assert set(operation.parameters.model_fields) == set(re.findall(r"\{(\w+)\}", path))
        shapes = (
            operation.body,
            operation.query,
            operation.parameters,
            operation.headers,
            operation.uploads,
            *operation.alternate_bodies.values(),
            *(response.body for response in operation.responses.values()),
            *(response.json_body for response in operation.responses.values()),
        )
        for shape in shapes:
            if shape is not None:
                TypeAdapter(shape).json_schema()


def test_partial_updates_preserve_omission_nullability_and_validation():
    update = partial_model(UserInput)
    assert update.model_validate({}).model_dump(exclude_unset=True) == {}
    assert update.model_validate({"organization": None}).model_dump(exclude_unset=True, exclude_none=False) == {"organization": None}
    with pytest.raises(ValidationError):
        update.model_validate({"name": None})

    profile_update = OPERATIONS["PUT", "/users/profile"].body
    assert profile_update.model_validate({}).model_dump(exclude_unset=True) == {}
    with pytest.raises(ValidationError):
        profile_update.model_validate({"timezone": "Invalid/Timezone"})


def test_empty_optional_filters_and_repeated_query_values():
    query = ContentQuery.model_validate({"completed": "", "timefrom": "", "group": ["one", "two"]})
    assert query.completed is None and query.timefrom is None
    assert query.group == ["one", "two"]
    filters = OPERATIONS["GET", "/tasks/runs"].query.model_validate({"job_ids": ["one", "two"], "limit": "1"})
    assert filters.job_ids == ["one", "two"] and filters.limit == 1


def test_url_validation_retains_original_spelling():
    url = "https://EXAMPLE.com"
    assert WebParameters.model_validate({"WEB_URL": url}).WEB_URL == url
    assert unchanged_proxy_url(url) == url
    assert unchanged_proxy_url("") == ""
    with pytest.raises(ValidationError):
        WebParameters.model_validate({"WEB_URL": "file:///etc/passwd"})
    with pytest.raises(ValidationError):
        unchanged_proxy_url("invalid proxy")


def test_broadcast_rejects_whitespace_without_trimming_valid_messages():
    assert Broadcast.model_validate({"message": " hello "}).message == " hello "
    with pytest.raises(ValidationError):
        Broadcast.model_validate({"message": " \n "})


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "News", "content": "Body"},
        [{"title": "News", "content": "Body"}],
        {"news_items": [{"title": "News", "content": "Body"}]},
        {"total_count": 1, "items": [{"news_items": [{"title": "News", "content": "Body"}]}]},
    ],
)
def test_content_import_preserves_supported_formats(payload):
    assert ContentImport.model_validate(payload).payload == payload


@pytest.mark.parametrize("payload", [[], {"items": []}, [1], [{"news_items": []}, {"title": "News"}]])
def test_content_import_rejects_empty_malformed_or_mixed_rows(payload):
    with pytest.raises(ValidationError):
        ContentImport.model_validate(payload)


def test_source_import_selects_version_specific_shape():
    adapter = TypeAdapter(SourceImport)
    source = {"name": "Feed", "type": "rss_collector"}
    assert adapter.validate_python({"version": 2, "data": [source]}).data[0].name == "Feed"
    assert adapter.validate_python({"version": 3, "sources": [source]}).sources[0].name == "Feed"
    with pytest.raises(ValidationError):
        adapter.validate_python({"version": 5, "sources": [source]})
