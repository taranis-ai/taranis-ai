import sys
from pathlib import Path
from typing import get_origin
from unittest.mock import MagicMock

import pytest
import responses


root_path = Path(__file__).resolve().parents[5] / "src" / "models"
root_str = str(root_path)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

from faker import Faker  # noqa: E402
from polyfactory.exceptions import ParameterException  # noqa: E402
from polyfactory.factories.pydantic_factory import ModelFactory  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from pydantic.fields import FieldInfo  # noqa: E402
from uuid_extensions import uuid7str  # noqa: E402

from frontend.config import Config  # noqa: E402
from frontend.log import logger  # noqa: E402
from frontend.views.admin_views import bot_views, scheduler_views, source_views  # noqa: E402
from frontend.views.base_view import BaseView  # noqa: E402

from .utils.formdata import gather_fields_from_model, html_form_to_dict, unwrap_annotation  # noqa: E402


@pytest.fixture
def form_data():
    return html_form_to_dict


@pytest.fixture
def responses_mock():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def source_api_mocks(monkeypatch):
    mock_api = MagicMock()
    monkeypatch.setattr(source_views, "CoreApi", lambda: mock_api)
    return mock_api


@pytest.fixture
def scheduler_api_mocks(monkeypatch):
    mock_api = MagicMock()

    def _api_get(path):
        if path == "/config/workers/dashboard":
            return {
                "scheduled_jobs": [],
                "scheduled_total_count": 0,
                "queues": [],
                "worker_stats": {},
                "active_jobs": [],
                "active_total_count": 0,
                "failed_jobs": [],
                "failed_total_count": 0,
            }
        return None

    mock_api.api_get.side_effect = _api_get
    monkeypatch.setattr(scheduler_views, "CoreApi", lambda: mock_api)

    class _TaskResults:
        extra = {
            "task_stats": {},
            "totals": {"successes": 0, "failures": 0, "overall_success_rate": 0},
        }

        def __len__(self):
            return 0

    class _DataPersistenceLayer:
        def get_objects(self, *_, **__):
            return _TaskResults()

    monkeypatch.setattr(scheduler_views, "DataPersistenceLayer", _DataPersistenceLayer)

    class _Dashboard:
        worker_status = {}

    class _SourcePersistenceLayer:
        def get_first(self, *_args, **_kwargs):
            return _Dashboard()

    monkeypatch.setattr(source_views, "DataPersistenceLayer", _SourcePersistenceLayer)
    monkeypatch.setattr(bot_views, "DataPersistenceLayer", _SourcePersistenceLayer)

    return mock_api


def get_items_from_factory(view_name, model):
    factory = ModelFactory.create_factory(model=model)

    try:
        instance = factory.build(factory_use_construct=True)
        items = [instance.model_dump(mode="json")]
    except ParameterException as e:
        logger.warning(f"PolyFactory couldn’t build {model.__name__} for view {view_name}: {e}\nFalling back to a minimal stub.")
        items = [{"id": 1, "name": f"test_{view_name.lower()}"}]

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

        if view_name in ["Dashboard", "Admin Dashboard"]:
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


@pytest.fixture(scope="class")
def form_formats_from_models():
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

            field_info: FieldInfo = field_info
            field_name: str = field_name

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

        payloads[view_name] = {
            "allowed": allowed_keys,
            "required": required_keys,
        }

    yield payloads


@pytest.fixture
def mock_core_get_endpoints(responses_mock, core_payloads, worker_parameter_data):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/worker-parameters", json=worker_parameter_data)

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

    scheduler_expect_object = str(core_payloads.get("Scheduler", {}).get("_expect_object") or "Scheduler Job")

    # Provide scheduler-specific endpoints so the dashboard renders during tests
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/workers/dashboard",
        json={
            "scheduled_jobs": [
                {
                    "id": "test-scheduler-job",
                    "name": scheduler_expect_object,
                    "queue": "collectors",
                    "type": "cron",
                    "schedule": "*/15 * * * *",
                    "next_run_time": "2025-01-01T12:00:00",
                }
            ],
            "scheduled_total_count": 1,
            "queues": [
                {"name": "collectors", "messages": 0},
                {"name": "bots", "messages": 2},
            ],
            "worker_stats": {
                "total_workers": 3,
                "busy_workers": 1,
                "idle_workers": 2,
            },
            "active_jobs": [],
            "active_total_count": 0,
            "failed_jobs": [],
            "failed_total_count": 0,
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/config/task-results",
        json={
            "items": [
                {
                    "id": "task-1",
                    "task": "collectors.fetch",
                    "status": "SUCCESS",
                    "result": None,
                    "last_run": "2024-01-01T00:00:00Z",
                    "last_success": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "task-2",
                    "task": "bots.process",
                    "status": "FAILURE",
                    "result": {"error": "timeout"},
                    "last_run": "2024-01-02T12:00:00Z",
                    "last_success": "2024-01-02T10:00:00Z",
                },
            ],
            "total_count": 2,
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
                current_item["id"] = uuid7str()
            else:
                logger.warning(f"Unsupported type for ID field in {view_name}: {ann}")
                current_item["id"] = "42"

        payloads[view_name] = {"_url": url, **current_item}
    yield payloads


@pytest.fixture
def mock_core_get_item_endpoints(responses_mock, mock_core_get_item_endpoint_data, worker_parameter_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.get(f"{url}/{data_id}", json=view_data)

    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_delete_endpoints(responses_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.delete(f"{url}/{data_id}", json={"message": "Successfully deleted"})
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_create_endpoints(responses_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.post(f"{url}", json=view_data)
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_update_endpoints(responses_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        responses_mock.put(f"{url}/{data_id}", json=view_data)
    yield mock_core_get_item_endpoint_data


########### LEGACY FIXTURES ###########


@pytest.fixture
def dashboard_get_mock(responses_mock):
    mock_data = {
        "items": [
            {
                "latest_collected": "2025-01-14T21:16:42.699574+01:00",
                "report_items_completed": 5,
                "report_items_in_progress": 1,
                "schedule_length": 2,
                "total_database_items": 308,
                "total_news_items": 306,
                "total_products": 1,
            }
        ]
    }

    responses_mock.get(f"{Config.TARANIS_CORE_URL}/dashboard", json=mock_data)
    yield mock_data


@pytest.fixture
def users_get_mock(responses_mock, organizations_get_mock, roles_get_mock):
    mock_data = {
        "items": [
            {
                "id": 1,
                "name": "Arthur Dent",
                "organization": 1,
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
                "roles": [1],
                "username": "admin",
            },
            {
                "id": 6,
                "name": "ccc",
                "organization": 2,
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
                "roles": [2],
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
                "address": {
                    "city": "Beaconsfield, Buckinghamshire",
                    "country": "United Kingdom",
                    "street": "Cherry Tree Rd",
                    "zip": "HP9 1BH",
                },
                "description": "A network infrastructure of Semaphore Towers, that operate in a similar fashion to telegraph.",
                "id": 2,
                "name": "The Clacks",
            },
            {
                "address": {"city": "Islington, London", "country": "United Kingdom", "street": "29 Arlington Avenue", "zip": "N1 7BE"},
                "description": "Earth is the third planet from the Sun and the only astronomical object known to harbor life.",
                "id": 1,
                "name": "The Earth",
            },
        ],
        "total_count": 2,
    }

    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/organizations", json=mock_data)
    yield mock_data


@pytest.fixture
def roles_get_mock(responses_mock):
    mock_data = {
        "items": [
            {
                "description": "Administrator role",
                "id": 1,
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
                "id": 2,
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
    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/config/users/2", json=response)
    yield response


@pytest.fixture
def users_put_mock(responses_mock):
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/users/1", json={"message": "Success"})


@pytest.fixture
def organizations_delete_mock(responses_mock):
    response = {"message": "Organization deleted successfully"}
    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/config/organizations/2", json=response)
    yield response


@pytest.fixture(autouse=True)
def mock_worker_parameters_get(responses_mock, worker_parameter_data):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/worker-parameters", json=worker_parameter_data)


@pytest.fixture
def organizations_put_mock(responses_mock):
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations", json={"message": "Success"})
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations/1", json={"message": "Success"})


@pytest.fixture
def roles_delete_mock(responses_mock):
    response = {"message": "Role deleted successfully"}
    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/config/roles/2", json=response)
    yield response


@pytest.fixture
def roles_put_mock(responses_mock):
    responses_mock.put(f"{Config.TARANIS_CORE_URL}/config/roles/1", json={"message": "Success"})


@pytest.fixture
def worker_parameter_data():
    return {
        "items": [
            {
                "id": "rss_collector",
                "parameters": [
                    {"label": "BROWSER_MODE", "name": "BROWSER_MODE", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "ADDITIONAL_HEADERS", "name": "ADDITIONAL_HEADERS", "parent": "parameters", "rules": ["json"], "type": "text"},
                    {"label": "FEED_URL", "name": "FEED_URL", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "USER_AGENT", "name": "USER_AGENT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "CONTENT_LOCATION", "name": "CONTENT_LOCATION", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "USE_FEED_CONTENT", "name": "USE_FEED_CONTENT", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "XPATH", "name": "XPATH", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "PROXY_SERVER", "name": "PROXY_SERVER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"},
                    {"label": "DIGEST_SPLITTING", "name": "DIGEST_SPLITTING", "parent": "parameters", "rules": [], "type": "switch"},
                    {
                        "label": "DIGEST_SPLITTING_LIMIT",
                        "name": "DIGEST_SPLITTING_LIMIT",
                        "parent": "parameters",
                        "rules": ["digest_splitting_limit"],
                        "type": "number",
                    },
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "USE_GLOBAL_PROXY", "name": "USE_GLOBAL_PROXY", "parent": "parameters", "rules": [], "type": "switch"},
                ],
            },
            {
                "id": "email_collector",
                "parameters": [
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "EMAIL_SERVER_TYPE", "name": "EMAIL_SERVER_TYPE", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "EMAIL_SERVER_HOSTNAME", "name": "EMAIL_SERVER_HOSTNAME", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "EMAIL_SERVER_PORT", "name": "EMAIL_SERVER_PORT", "parent": "parameters", "rules": [], "type": "number"},
                    {"label": "EMAIL_USERNAME", "name": "EMAIL_USERNAME", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "EMAIL_PASSWORD", "name": "EMAIL_PASSWORD", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "PROXY_SERVER", "name": "PROXY_SERVER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"},
                ],
            },
            {
                "id": "simple_web_collector",
                "parameters": [
                    {"label": "WEB_URL", "name": "WEB_URL", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "USER_AGENT", "name": "USER_AGENT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "PROXY_SERVER", "name": "PROXY_SERVER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "XPATH", "name": "XPATH", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"},
                    {"label": "ADDITIONAL_HEADERS", "name": "ADDITIONAL_HEADERS", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BROWSER_MODE", "name": "BROWSER_MODE", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "DIGEST_SPLITTING", "name": "DIGEST_SPLITTING", "parent": "parameters", "rules": [], "type": "switch"},
                    {
                        "label": "DIGEST_SPLITTING_LIMIT",
                        "name": "DIGEST_SPLITTING_LIMIT",
                        "parent": "parameters",
                        "rules": ["digest_splitting_limit"],
                        "type": "number",
                    },
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "USE_GLOBAL_PROXY", "name": "USE_GLOBAL_PROXY", "parent": "parameters", "rules": [], "type": "switch"},
                ],
            },
            {
                "id": "manual_collector",
                "parameters": [{"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"}],
            },
            {
                "id": "rt_collector",
                "parameters": [
                    {"label": "BASE_URL", "name": "BASE_URL", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "RT_TOKEN", "name": "RT_TOKEN", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"},
                    {"label": "ADDITIONAL_HEADERS", "name": "ADDITIONAL_HEADERS", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "USER_AGENT", "name": "USER_AGENT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "PROXY_SERVER", "name": "PROXY_SERVER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "SEARCH_QUERY", "name": "SEARCH_QUERY", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "FIELDS_TO_INCLUDE", "name": "FIELDS_TO_INCLUDE", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "USE_GLOBAL_PROXY", "name": "USE_GLOBAL_PROXY", "parent": "parameters", "rules": [], "type": "switch"},
                ],
            },
            {
                "id": "analyst_bot",
                "parameters": [
                    {"label": "REGULAR_EXPRESSION", "name": "REGULAR_EXPRESSION", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "ATTRIBUTE_NAME", "name": "ATTRIBUTE_NAME", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "grouping_bot",
                "parameters": [
                    {"label": "REGULAR_EXPRESSION", "name": "REGULAR_EXPRESSION", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "nlp_bot",
                "parameters": [
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "BOT_ENDPOINT", "name": "BOT_ENDPOINT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BOT_API_KEY", "name": "BOT_API_KEY", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "ioc_bot",
                "parameters": [
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "tagging_bot",
                "parameters": [
                    {"label": "KEYWORDS", "name": "KEYWORDS", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "story_bot",
                "parameters": [
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "BOT_ENDPOINT", "name": "BOT_ENDPOINT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BOT_API_KEY", "name": "BOT_API_KEY", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "summary_bot",
                "parameters": [
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "BOT_ENDPOINT", "name": "BOT_ENDPOINT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BOT_API_KEY", "name": "BOT_API_KEY", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "wordlist_bot",
                "parameters": [
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {
                        "disabled": True,
                        "headers": [{"key": "name", "title": "Name"}, {"key": "description", "title": "Description"}],
                        "items": [
                            {"description": "List of Advanced Persistent Threat Groups", "name": "APT Groups"},
                            {"description": "List of products that are known to be affected by a CVE.", "name": "CVE Products"},
                            {"description": "List of vendors that are known to be affected by a CVE.", "name": "CVE Vendors"},
                            {"description": "List of common cyber security terms", "name": "Common Cyber Security Terms"},
                            {"description": "List of Countries", "name": "Countries"},
                            {"description": "Wichtigsten internationalen Organisationen", "name": "Internationale Organisationen"},
                            {"description": "Liste aller L\u00e4nder", "name": "L\u00e4nder"},
                            {"description": "Gr\u00f6\u00dften Unternehmen in \u00d6sterreich", "name": "Unternehmen \u00d6sterreich"},
                        ],
                        "label": "TAGGING_WORDLISTS",
                        "name": "TAGGING_WORDLISTS",
                        "parent": "parameters",
                        "rules": [],
                        "type": "table",
                        "value": [],
                    },
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "pdf_presenter",
                "parameters": [
                    {"label": "TEMPLATE_PATH", "name": "TEMPLATE_PATH", "parent": "parameters", "rules": ["required"], "type": "text"}
                ],
            },
            {
                "id": "html_presenter",
                "parameters": [
                    {"label": "TEMPLATE_PATH", "name": "TEMPLATE_PATH", "parent": "parameters", "rules": ["required"], "type": "text"}
                ],
            },
            {
                "id": "text_presenter",
                "parameters": [
                    {"label": "TEMPLATE_PATH", "name": "TEMPLATE_PATH", "parent": "parameters", "rules": ["required"], "type": "text"}
                ],
            },
            {
                "id": "json_presenter",
                "parameters": [
                    {"label": "TEMPLATE_PATH", "name": "TEMPLATE_PATH", "parent": "parameters", "rules": ["required"], "type": "text"}
                ],
            },
            {
                "id": "ftp_publisher",
                "parameters": [{"label": "FTP_URL", "name": "FTP_URL", "parent": "parameters", "rules": ["required"], "type": "text"}],
            },
            {
                "id": "sftp_publisher",
                "parameters": [
                    {"label": "SFTP_URL", "name": "SFTP_URL", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "PRIVATE_KEY", "name": "PRIVATE_KEY", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "email_publisher",
                "parameters": [
                    {
                        "label": "SMTP_SERVER_ADDRESS",
                        "name": "SMTP_SERVER_ADDRESS",
                        "parent": "parameters",
                        "rules": ["required"],
                        "type": "text",
                    },
                    {"label": "SMTP_SERVER_PORT", "name": "SMTP_SERVER_PORT", "parent": "parameters", "rules": [], "type": "number"},
                    {"label": "SERVER_TLS", "name": "SERVER_TLS", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "EMAIL_USERNAME", "name": "EMAIL_USERNAME", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "EMAIL_PASSWORD", "name": "EMAIL_PASSWORD", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "EMAIL_SENDER", "name": "EMAIL_SENDER", "parent": "parameters", "rules": ["required", "email"], "type": "text"},
                    {
                        "label": "EMAIL_RECIPIENT",
                        "name": "EMAIL_RECIPIENT",
                        "parent": "parameters",
                        "rules": ["required", "email"],
                        "type": "text",
                    },
                    {"label": "EMAIL_SUBJECT", "name": "EMAIL_SUBJECT", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "wordpress_publisher",
                "parameters": [
                    {"label": "WP_URL", "name": "WP_URL", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "WP_USER", "name": "WP_USER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "WP_PYTHON_APP_SECRET", "name": "WP_PYTHON_APP_SECRET", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "misp_publisher",
                "parameters": [
                    {"label": "MISP_URL", "name": "MISP_URL", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "MISP_API_KEY", "name": "MISP_API_KEY", "parent": "parameters", "rules": [], "type": "text"},
                ],
            },
            {
                "id": "sentiment_analysis_bot",
                "parameters": [
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "BOT_ENDPOINT", "name": "BOT_ENDPOINT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BOT_API_KEY", "name": "BOT_API_KEY", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "misp_connector",
                "parameters": [
                    {"label": "URL", "name": "URL", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "ORGANISATION_ID", "name": "ORGANISATION_ID", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "SSL_CHECK", "name": "SSL_CHECK", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REQUEST_TIMEOUT", "name": "REQUEST_TIMEOUT", "parent": "parameters", "rules": [], "type": "number"},
                    {"label": "USER_AGENT", "name": "USER_AGENT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "PROXY_SERVER", "name": "PROXY_SERVER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "ADDITIONAL_HEADERS", "name": "ADDITIONAL_HEADERS", "parent": "parameters", "rules": ["json"], "type": "text"},
                    {"label": "SHARING_GROUP_ID", "name": "SHARING_GROUP_ID", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "DISTRIBUTION", "name": "DISTRIBUTION", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "API_KEY", "name": "API_KEY", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "USE_GLOBAL_PROXY", "name": "USE_GLOBAL_PROXY", "parent": "parameters", "rules": [], "type": "switch"},
                ],
            },
            {
                "id": "cybersec_classifier_bot",
                "parameters": [
                    {"label": "ITEM_FILTER", "name": "ITEM_FILTER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BOT_API_KEY", "name": "BOT_API_KEY", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "BOT_ENDPOINT", "name": "BOT_ENDPOINT", "parent": "parameters", "rules": [], "type": "text"},
                    {
                        "label": "CLASSIFICATION_THRESHOLD",
                        "name": "CLASSIFICATION_THRESHOLD",
                        "parent": "parameters",
                        "rules": [],
                        "type": "text",
                    },
                    {"label": "RUN_AFTER_COLLECTOR", "name": "RUN_AFTER_COLLECTOR", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                ],
            },
            {
                "id": "ppn_collector",
                "parameters": [
                    {"label": "PATH", "name": "PATH", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "DIGEST_SPLITTING", "name": "DIGEST_SPLITTING", "parent": "parameters", "rules": [], "type": "switch"},
                ],
            },
            {
                "id": "pandoc_presenter",
                "parameters": [
                    {"label": "TEMPLATE_PATH", "name": "TEMPLATE_PATH", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "CONVERT_FROM", "name": "CONVERT_FROM", "parent": "parameters", "rules": ["one_of:html|md"], "type": "text"},
                    {"label": "CONVERT_TO", "name": "CONVERT_TO", "parent": "parameters", "rules": ["one_of:docx|odt"], "type": "text"},
                ],
            },
            {
                "id": "misp_collector",
                "parameters": [
                    {"label": "URL", "name": "URL", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "SSL_CHECK", "name": "SSL_CHECK", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "REQUEST_TIMEOUT", "name": "REQUEST_TIMEOUT", "parent": "parameters", "rules": [], "type": "number"},
                    {"label": "USER_AGENT", "name": "USER_AGENT", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "PROXY_SERVER", "name": "PROXY_SERVER", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "ADDITIONAL_HEADERS", "name": "ADDITIONAL_HEADERS", "parent": "parameters", "rules": ["json"], "type": "text"},
                    {"label": "SHARING_GROUP_ID", "name": "SHARING_GROUP_ID", "parent": "parameters", "rules": [], "type": "text"},
                    {"label": "API_KEY", "name": "API_KEY", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "REFRESH_INTERVAL", "name": "REFRESH_INTERVAL", "parent": "parameters", "rules": [], "type": "cron_interval"},
                    {"label": "ORGANISATION_ID", "name": "ORGANISATION_ID", "parent": "parameters", "rules": ["required"], "type": "text"},
                    {"label": "USE_GLOBAL_PROXY", "name": "USE_GLOBAL_PROXY", "parent": "parameters", "rules": [], "type": "switch"},
                    {"label": "TLP_LEVEL", "name": "TLP_LEVEL", "parent": "parameters", "rules": ["tlp"], "type": "text"},
                ],
            },
            {"id": "stix_presenter", "parameters": []},
        ]
    }
