import pytest
import lxml.html
from lxml.html import CheckboxValues, MultipleSelectOptions, InputElement

from frontend.config import Config


class FormData(dict):
    def __init__(self, form_element):
        super().__init__()
        self._frozen = False
        self.form = form_element

        for key, element in form_element.inputs.items():
            skip, value = self._get_value_from_element(element)
            if not skip:
                self[key] = value

        self._frozen = True

    def _get_value_from_element(self, element):
        if isinstance(element, InputElement) and element.attrib.get("type") == "submit":
            return True, None

        value = element.value

        if value is None:
            return False, ""
        if isinstance(value, str):
            value = value.lstrip("\n")
        elif isinstance(value, CheckboxValues):
            value = [el.value for el in value.group if el.value is not None]
        elif isinstance(value, MultipleSelectOptions):
            value = list(value)

        return False, value

    def __setitem__(self, key, value):
        if self._frozen and key not in self:
            available_keys = ", ".join(self.keys())
            raise ValueError(f"Key '{key}' is not in the dict. Available: {available_keys}")
        super().__setitem__(key, value)

    def update(self, other=None, **kwargs):
        if other:
            for key, value in other.items():
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def submit(self, client):
        for method in ["get", "post", "delete"]:
            url = self.form.get(f"hx-{method}")
            if url:
                break
        else:
            url = self.form.get("action")
            if not url:
                raise ValueError("Could not find an URL to send data to. Tried hx-get, hx-post, hx-delete and action.")
            method = self.form.get("method", "get").lower()

        return getattr(client, method)(url, self)

    def get_cleaned_keys(self):
        keys = set(dict(self).keys())
        keys.discard(None)
        return keys


def html_form_to_dict(html: str, index: int = 0, name: str | None = None, id: str | None = None) -> FormData:
    """
    Return data of a form in the given `html`.

    - index: Return the data of the n'th form in the html. Defaults to the first one.
    - name: Return the data of the form with the given name.
    - id: Return the data of the form with the given id.
    """
    tree = lxml.html.fromstring(html)

    for attr_name, attr_value in (("name", name), ("id", id)):
        if attr_value is not None:
            found_values = []
            for form in tree.iterfind(".//form"):
                val = form.get(attr_name)
                found_values.append(val)
                if val == attr_value:
                    return FormData(form)
            raise ValueError(f'No form with {attr_name}="{attr_value}" found. Found forms with these {attr_name}s: {found_values}')

    try:
        return FormData(tree.forms[index])
    except IndexError as e:
        raise ValueError(f"No form at index {index}. Found {len(tree.forms)} forms.") from e


@pytest.fixture
def form_data():
    return html_form_to_dict


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
    requests_mock.delete(f"{Config.TARANIS_CORE_URL}/config/users/2", json={"message": "Success"})


@pytest.fixture
def users_put_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/users/1", json={"message": "Success"})


@pytest.fixture
def organizations_delete_mock(requests_mock):
    requests_mock.delete(f"{Config.TARANIS_CORE_URL}/config/organizations/2", json={"message": "Success"})


@pytest.fixture
def organizations_put_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/organizations/1", json={"message": "Success"})


@pytest.fixture
def roles_delete_mock(requests_mock):
    requests_mock.delete(f"{Config.TARANIS_CORE_URL}/config/roles/2", json={"message": "Success"})


@pytest.fixture
def roles_put_mock(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/config/roles/1", json={"message": "Success"})
