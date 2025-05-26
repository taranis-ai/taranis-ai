import pytest

from frontend.log import logger
from frontend.config import Config
from frontend.views.base_view import BaseView
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.exceptions import ParameterException


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
        if not (model and endpoint):
            continue

        # Make a factory for this model
        factory = ModelFactory.create_factory(model=model)

        try:
            instance = factory.build(factory_use_construct=True)
            items = [instance.model_dump(mode="json")]
        except ParameterException as e:
            logger.warning(f"PolyFactory couldn’t build {model.__name__} for view {view_name}: {e}\nFalling back to a minimal stub.")
            items = [{"id": 1, "name": f"test_{view_name.lower()}"}]

        payloads[view_name] = {
            "items": items,
            "total_count": len(items),
            "_url": f"{Config.TARANIS_CORE_URL}{endpoint}",
        }
    yield payloads


@pytest.fixture
def mock_core_endpoints(requests_mock, core_payloads):
    """
    Function‐scoped: before each test, register all URLs
    from our pre‐built core_payloads, then yield that payloads dict.
    """
    for data in core_payloads.values():
        requests_mock.get(
            data["_url"],
            json={
                "items": data["items"],
                "total_count": data["total_count"],
            },
        )
    yield core_payloads
