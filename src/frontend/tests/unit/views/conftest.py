import pytest
from typing import get_origin

from frontend.log import logger
from frontend.config import Config
from frontend.views.base_view import BaseView
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.exceptions import ParameterException
from .utils.formdata import html_form_to_dict, gather_fields_from_model, unwrap_annotation
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from uuid_extensions import uuid7str
from faker import Faker


@pytest.fixture
def form_data():
    return html_form_to_dict


@pytest.fixture(scope="class")
def core_payloads():
    """
    For each registered view:
      - Attempt to build one instance via PolyFactory
      - If that fails (e.g. unsupported nested Role), fall back to a simple dict
      - Mock the endpoint so your list-views always get {"items": [...], "total_count": 1}
    """
    payloads: dict[str, dict] = {}

    for view_name, view_cls in BaseView._registry.items():
        model = getattr(view_cls, "model", None)
        endpoint = getattr(model, "_core_endpoint", None)
        if not model or not endpoint:
            continue

        # Make a factory for this model
        factory = ModelFactory.create_factory(model=model)

        try:
            instance = factory.build(factory_use_construct=True)
            items = [instance.model_dump(mode="json")]
        except ParameterException as e:
            logger.warning(f"PolyFactory couldn’t build {model.__name__} for view {view_name}: {e}\nFalling back to a minimal stub.")
            items = [{"id": 1, "name": f"test_{view_name.lower()}"}]

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
def mock_core_get_endpoints(requests_mock, core_payloads):
    for data in core_payloads.values():
        requests_mock.get(
            data["_url"],
            json={
                "items": data["items"],
                "total_count": data["total_count"],
            },
        )
    yield core_payloads


@pytest.fixture(scope="class")
def mock_core_get_item_endpoint_data(core_payloads):
    payloads: dict[str, dict] = {}
    faker = Faker()

    for view_name, view_cls in BaseView._registry.items():
        data = core_payloads.get(view_name)
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
def mock_core_get_item_endpoints(requests_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        requests_mock.get(f"{url}/{data_id}", json=view_data)
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_delete_endpoints(requests_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        requests_mock.delete(f"{url}/{data_id}", json={"message": "Successfully deleted"})
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_create_endpoints(requests_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        requests_mock.post(f"{url}", json=view_data)
    yield mock_core_get_item_endpoint_data


@pytest.fixture
def mock_core_update_endpoints(requests_mock, mock_core_get_item_endpoint_data):
    for view_name, view_data in mock_core_get_item_endpoint_data.items():
        url = view_data.pop("_url", None)
        data_id = view_data.get("id", None)
        if not url or not data_id:
            continue
        requests_mock.put(f"{url}/{data_id}", json=view_data)
    yield mock_core_get_item_endpoint_data


########### LEGACY FIXTURES ###########


@pytest.fixture
def dashboard_get_mock(requests_mock):
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

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/dashboard", json=mock_data)
    yield mock_data


@pytest.fixture
def users_get_mock(requests_mock, organizations_get_mock, roles_get_mock):
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

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/config/users", json=mock_data)
    yield mock_data


@pytest.fixture
def organizations_get_mock(requests_mock):
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

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/config/organizations", json=mock_data)
    yield mock_data


@pytest.fixture
def roles_get_mock(requests_mock):
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

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/config/roles", json=mock_data)
    yield mock_data


@pytest.fixture
def permissions_get_mock(requests_mock):
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

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/config/permissions", json=mock_data)
    yield mock_data


@pytest.fixture
def users_delete_mock(requests_mock):
    response = {"message": "User deleted successfully"}
    requests_mock.delete(f"{Config.TARANIS_CORE_URL}/config/users/2", json=response)
    yield response


@pytest.fixture
def users_put_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/users/1", json={"message": "Success"})


@pytest.fixture
def organizations_delete_mock(requests_mock):
    response = {"message": "Organization deleted successfully"}
    requests_mock.delete(f"{Config.TARANIS_CORE_URL}/config/organizations/2", json=response)
    yield response


@pytest.fixture
def organizations_put_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations", json={"message": "Success"})
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations/1", json={"message": "Success"})


@pytest.fixture
def roles_delete_mock(requests_mock):
    response = {"message": "Role deleted successfully"}
    requests_mock.delete(f"{Config.TARANIS_CORE_URL}/config/roles/2", json=response)
    yield response


@pytest.fixture
def roles_put_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/roles/1", json={"message": "Success"})
