import uuid
from typing import Any, get_origin

import pytest
import responses
from faker import Faker
from models.types import BOT_TYPES
from models.worker_parameters import WORKER_DEFINITIONS
from polyfactory.exceptions import ParameterException
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel

from frontend.config import Config
from frontend.log import logger
from frontend.views.base_view import BaseView

from .utils.formdata import gather_fields_from_model, html_form_to_dict, unwrap_annotation


@pytest.fixture
def form_data():
    return html_form_to_dict


@pytest.fixture
def responses_mock():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


def get_items_from_factory(view_name, model):
    if view_name == "Settings":
        return [model(settings={"default_collector_proxy": "http://proxy.test", "default_timezone": "UTC"}).model_dump(mode="json")]

    factory = ModelFactory.create_factory(model=model)

    try:
        instance = factory.build(factory_use_construct=True)
        items = [instance.model_dump(mode="json")]
    except ParameterException as e:
        logger.warning(f"PolyFactory couldn’t build {model.__name__} for view {view_name}: {e}\nFalling back to a minimal stub.")
        items = [{"id": "test-1", "name": f"test_{view_name.lower()}"}]

    return items


@pytest.fixture(scope="class")
def core_payloads():
    """
    For each registered view:
      - Attempt to build one instance via PolyFactory
      - If that fails (e.g. unsupported nested Role), fall back to a simple dict
      - Mock the endpoint so your list-views always get {"items": [...], "total_count": 1}
    """
    payloads: dict[str, dict] = {}
    url_items: dict[str, list[dict]] = {}

    for view_name, view_cls in BaseView._registry.items():
        model = getattr(view_cls, "model", None)
        endpoint = getattr(model, "_core_endpoint", None)
        if not model or not endpoint:
            continue

        url = f"{Config.TARANIS_CORE_URL}{endpoint}"
        if url not in url_items:
            url_items[url] = get_items_from_factory(view_name, model)
        items = url_items[url]

        expect_object = None

        if view_name == "Notifications":
            expect_object = "client-1"
        elif view_name in ["Dashboard", "Admin Dashboard"]:
            expect_object = str(items[0].get("total_news_items"))
        elif view_name == "Settings":
            expect_object = items[0].get("settings", {}).get("default_collector_proxy")
        elif "name" in items[0]:
            expect_object = str(items[0].get("name"))
        elif "title" in items[0]:
            expect_object = str(items[0].get("title"))
        elif "id" in items[0]:
            expect_object = str(items[0].get("id"))

        payloads[view_name] = {
            "items": items,
            "total_count": len(items),
            "_url": f"{Config.TARANIS_CORE_URL}{endpoint}",
            "_expect_object": expect_object,
        }
    yield payloads


@pytest.fixture
def form_formats_from_models(worker_parameter_data: dict[str, Any]):
    """
    Returns mapping:
       view_name -> {
         "allowed": set of all permissible form keys,
         "required": set of keys that must appear
       }
    """
    payloads: dict[str, dict[str, set[str]]] = {}

    for view_name, view_cls in BaseView._registry.items():
        model = getattr(view_cls, "model", None)
        if not model:
            continue

        allowed_keys = set()
        required_keys = set()

        for field_name, field_info in model.model_fields.items():
            if field_name == "id" and view_name != "Template":
                continue
            if field_name == "status":
                continue

            ann = field_info.annotation
            field_required = True

            if nested_origin := unwrap_annotation(ann):
                ann = nested_origin[0]
                field_required = nested_origin[1]

            origin = get_origin(ann)

            if isinstance(ann, type) and issubclass(ann, BaseModel):
                print(f"Gathering nested fields for {view_name}.{field_name} with {ann}")
                nested_allow_keys, nested_require_keys = gather_fields_from_model(ann)
                for nk in nested_allow_keys:
                    allowed_keys.add(f"{field_name}[{nk}]")
                for nk in nested_require_keys:
                    required_keys.add(f"{field_name}[{nk}]")
                continue

            key = field_name
            if origin in (list, set, dict):
                key = f"{field_name}[]"

            allowed_keys.add(key)
            if field_required:
                required_keys.add(key)

        if view_name == "OSINT Source":
            allowed_keys.add("delete_icon")
            allowed_keys.add("rank")
        if view_name == "Bot":
            allowed_keys.add("id")
            allowed_keys.add("parameters[RUN_AFTER_BOTS][]")
            bot_type_ids = {member.value for member in BOT_TYPES}
            allowed_keys.update(
                f"parameters[{parameter['name']}]"
                for worker in worker_parameter_data["items"]
                if worker["id"] in bot_type_ids
                for parameter in worker["parameters"]
                if parameter.get("parent") == "parameters"
                and parameter.get("type") in {"text", "number", "textarea", "switch", "cron_interval"}
            )
            allowed_keys.discard("enabled")
            required_keys.discard("enabled")
        if view_name == "User":
            allowed_keys.add("profile[onboarding_enabled]")

        payloads[view_name] = {
            "allowed": allowed_keys,
            "required": required_keys,
        }

    yield payloads


@pytest.fixture
def mock_core_get_endpoints(responses_mock, core_payloads):

    for data in core_payloads.values():
        responses_mock.get(
            data["_url"],
            json={
                "items": data["items"],
                "total_count": data["total_count"],
            },
            status=200,
            content_type="application/json",
        )

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/admin-menu-badges",
        json={"osint_source": 2, "bot": 3},
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/realtime/clients",
        json={
            "num_clients": 1,
            "num_users": 1,
            "clients": [{"client_id": "client-1", "user_id": "user-1", "username": "admin"}],
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/tasks",
        json={
            "items": [
                {
                    "id": "task-1",
                    "task": "collector_task",
                    "worker_type": "rss_collector",
                    "worker_id": "source-1",
                    "status": "SUCCESS",
                    "result": {"message": "Collected 5 items", "reason": None, "retryable": False, "data": {"source_id": "source-1"}},
                    "last_run": "2024-01-01T00:00:00Z",
                    "last_success": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "task-2",
                    "task": "bot_task",
                    "worker_type": "WORDLIST_BOT",
                    "worker_id": "bot-1",
                    "status": "FAILURE",
                    "result": {"message": "timeout", "reason": "bot_execution_failed", "retryable": False, "data": {"bot_id": "bot-1"}},
                    "last_run": "2024-01-02T12:00:00Z",
                    "last_success": "2024-01-02T10:00:00Z",
                },
            ],
            "total_count": 2,
            "task_stats": {
                "rss_collector": {
                    "last_run": "2024-01-01T00:00:00Z",
                    "last_success": "2024-01-01T00:00:00Z",
                    "last_run_display": "2024-01-01T00:00:00Z",
                    "last_success_display": "2024-01-01T00:00:00Z",
                    "worker_type": "rss_collector",
                    "worker_id": "source-1",
                    "successes": 1,
                    "failures": 0,
                    "total": 1,
                    "success_pct": 100,
                    "status_badge": {"label": "All Success", "variant": "success"},
                },
                "WORDLIST_BOT": {
                    "last_run": "2024-01-02T12:00:00Z",
                    "last_success": "2024-01-02T10:00:00Z",
                    "last_run_display": "2024-01-02T12:00:00Z",
                    "last_success_display": "2024-01-02T10:00:00Z",
                    "worker_type": "WORDLIST_BOT",
                    "worker_id": "bot-1",
                    "successes": 0,
                    "failures": 1,
                    "total": 1,
                    "success_pct": 0,
                    "status_badge": {"label": "First Failure", "variant": "warning"},
                },
            },
            "totals": {"successes": 1, "failures": 1, "overall_success_rate": 50},
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/workers/tasks",
        json=[
            {"name": "collectors", "messages": 1},
            {"name": "bots", "messages": 0},
        ],
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/workers/stats",
        json={"total_workers": 2, "busy_workers": 1, "idle_workers": 1},
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/workers/active",
        json={
            "items": [
                {
                    "id": "active-1",
                    "name": "Running Bot",
                    "queue": "bots",
                    "started_at": "2025-01-01T11:55:00",
                }
            ],
            "total_count": 1,
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/workers/failed",
        json={
            "items": [
                {
                    "id": "failed-1",
                    "name": "Failed Connector",
                    "queue": "connectors",
                    "failed_at": "2025-01-01T11:50:00",
                    "error": "Boom",
                }
            ],
            "total_count": 1,
        },
        status=200,
        content_type="application/json",
    )
    yield core_payloads


@pytest.fixture(scope="class")
def mock_core_get_item_endpoint_data(core_payloads):
    payloads: dict[str, dict] = {}
    faker = Faker()

    for view_name, view_cls in BaseView._registry.items():
        data = core_payloads.get(view_name)
        if not data:
            logger.warning(f"No core payload data for view {view_name}")
            continue
        url = data.get("_url", None)
        current_item = data["items"][0]
        model = getattr(view_cls, "model", None)
        if not model or not current_item:
            continue

        if field_info := model.model_fields.get("id"):
            ann = field_info.annotation
            if nested_origin := unwrap_annotation(ann):
                ann = nested_origin[0]

            if isinstance(ann, int) or issubclass(ann, int):
                current_item["id"] = faker.pyint()
            elif isinstance(ann, str) or issubclass(ann, str):
                current_item["id"] = str(uuid.uuid7())
            else:
                logger.warning(f"Unsupported type for ID field in {view_name}: {ann}")
                current_item["id"] = "42"

        payloads[view_name] = {"_url": url, **current_item}
    yield payloads


@pytest.fixture
def mock_core_get_item_endpoints(responses_mock, core_payloads, mock_core_get_item_endpoint_data):

    for data in core_payloads.values():
        responses_mock.get(
            data["_url"],
            json={
                "items": data["items"],
                "total_count": data["total_count"],
            },
            status=200,
            content_type="application/json",
        )

    for view_data in mock_core_get_item_endpoint_data.values():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.get(f"{url}/{data_id}", json=view_data)

    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_delete_endpoints(responses_mock, mock_core_get_item_endpoint_data):
    for view_data in mock_core_get_item_endpoint_data.values():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.delete(f"{url}/{data_id}", json={"message": "Successfully deleted"})
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_create_endpoints(responses_mock, mock_core_get_item_endpoint_data):
    for view_data in mock_core_get_item_endpoint_data.values():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.post(f"{url}", json=view_data)
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_update_endpoints(responses_mock, mock_core_get_item_endpoint_data):
    for view_data in mock_core_get_item_endpoint_data.values():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.put(f"{url}/{data_id}", json=view_data)
    yield mock_core_get_item_endpoint_data


########### LEGACY FIXTURES ###########


@pytest.fixture
def settings_get_mock(responses_mock):
    mock_data = {
        "items": [{"settings": {"default_collector_proxy": "", "onboarding_enabled": True}}],
        "total_count": 1,
    }
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/settings/settings", json=mock_data)
    yield mock_data


@pytest.fixture
def users_get_mock(responses_mock, organizations_get_mock, roles_get_mock, settings_get_mock):
    mock_data = {
        "items": [
            {
                "id": "user-1",
                "name": "Arthur Dent",
                "organization": "organization-1",
                "permissions": [
                    "ASSESS_ACCESS",
                    "ANALYZE_ACCESS",
                    "PUBLISH_PRODUCT",
                    "PUBLISH_ACCESS",
                    "PUBLISH_CREATE",
                    "ASSESS_DELETE",
                    "BOT_EXECUTE",
                    "ANALYZE_DELETE",
                    "ANALYZE_UPDATE",
                    "ASSESS_CREATE",
                ],
                "profile": {},
                "roles": ["role-1"],
                "username": "admin",
            },
            {
                "id": "user-2",
                "name": "ccc",
                "organization": "organization-1",
                "permissions": [
                    "PUBLISH_DELETE",
                    "ASSESS_UPDATE",
                    "ANALYZE_CREATE",
                    "PUBLISH_UPDATE",
                    "ASSESS_ACCESS",
                    "ANALYZE_ACCESS",
                    "PUBLISH_PRODUCT",
                    "PUBLISH_ACCESS",
                    "PUBLISH_CREATE",
                    "ASSESS_DELETE",
                    "BOT_EXECUTE",
                    "ANALYZE_DELETE",
                    "ANALYZE_UPDATE",
                    "ASSESS_CREATE",
                ],
                "profile": {},
                "roles": ["role-2"],
                "username": "ccc",
            },
        ],
        "total_count": 2,
    }

    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/users", json=mock_data)
    yield mock_data


@pytest.fixture
def organizations_get_mock(responses_mock):
    mock_data = {
        "items": [
            {
                "address": {},
                "description": "Default organization for initial users.",
                "id": "organization-1",
                "name": "Default Organization",
            },
        ],
        "total_count": 1,
    }

    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/organizations", json=mock_data)
    yield mock_data


@pytest.fixture
def roles_get_mock(responses_mock):
    mock_data = {
        "items": [
            {
                "description": "Administrator role",
                "id": "role-1",
                "name": "Admin",
                "permissions": [
                    "ANALYZE_CREATE",
                    "CONFIG_BOT_CREATE",
                    "CONFIG_OSINT_SOURCE_GROUP_ACCESS",
                    "CONFIG_ACL_DELETE",
                    "CONFIG_ROLE_DELETE",
                ],
                "tlp_level": None,
            },
            {
                "description": "Basic user role",
                "id": "role-2",
                "name": "User",
                "permissions": [
                    "ASSESS_ACCESS",
                    "ASSESS_CREATE",
                    "ASSESS_UPDATE",
                    "ASSESS_DELETE",
                ],
                "tlp_level": None,
            },
        ],
        "total_count": 2,
    }

    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/roles", json=mock_data)
    yield mock_data


@pytest.fixture
def permissions_get_mock(responses_mock):
    mock_data = {
        "items": [
            {
                "description": "Access to the assessment module",
                "id": "ASSESS_ACCESS",
                "name": "ASSESS_ACCESS",
            },
            {
                "description": "Create new assessments",
                "id": "ASSESS_CREATE",
                "name": "ASSESS_CREATE",
            },
        ],
        "total_count": 2,
    }

    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/permissions", json=mock_data)
    yield mock_data


@pytest.fixture
def users_delete_mock(responses_mock):
    response = {"message": "User deleted successfully"}
    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/config/users/user-2", json=response)
    yield response


@pytest.fixture
def users_put_mock(responses_mock):
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/users/user-1", json={"message": "Success"})


@pytest.fixture
def organizations_delete_mock(responses_mock):
    response = {"message": "Organization deleted successfully"}
    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/config/organizations/organization-2", json=response)
    yield response


@pytest.fixture
def organizations_put_mock(responses_mock):
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations", json={"message": "Success"})
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations/organization-1", json={"message": "Success"})


@pytest.fixture
def roles_delete_mock(responses_mock):
    response = {"message": "Role deleted successfully"}
    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/config/roles/role-2", json=response)
    yield response


@pytest.fixture
def roles_put_mock(responses_mock):
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/roles/role-1", json={"message": "Success"})


@pytest.fixture
def worker_parameter_data():
    return {
        "items": [
            {
                "id": worker_type.value,
                "parameters": [{"name": name, "parent": "parameters", "type": "text"} for name in definition.parameter_model.model_fields],
            }
            for worker_type, definition in WORKER_DEFINITIONS.items()
        ]
    }
