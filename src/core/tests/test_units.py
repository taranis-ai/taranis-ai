from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.types import PRESENTER_TYPES

from core.model.product import Product
from core.model.product_type import ProductType
from core.model.report_item import ReportItem
from core.model.report_item_type import ReportItemType
from core.managers import queue_manager
from core.service.product import ProductService


@pytest.fixture
def product_type_id(app):
    with app.app_context():
        text_presenter = ProductType.get_by_type(PRESENTER_TYPES.TEXT_PRESENTER)
        if not text_presenter:
            raise AssertionError("Text presenter product type is required for tests")
        return text_presenter.id


@pytest.fixture
def report_item(app, session):
    with app.app_context():
        report_types = ReportItemType.get_all_for_collector()
        if not report_types:
            raise AssertionError("At least one report item type must exist")

        report, status = ReportItem.add({"title": "Auto Publish Report", "report_item_type_id": report_types[0].id}, None)
        if status != 200:
            raise AssertionError(f"Report item creation failed with status {status}")
        return report


@pytest.fixture(autouse=True)
def suppress_generate_product(app, monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(queue_manager.queue_manager, "generate_product", mock)
    yield mock


def _create_product(app, product_type_id: int, report_item: ReportItem, *, title: str, auto_publish: bool, default_publisher: str | None):
    payload = {
        "title": title,
        "description": "unit-test product",
        "product_type_id": product_type_id,
        "auto_publish": auto_publish,
        "default_publisher": default_publisher,
        "report_items": [report_item.id],
    }
    with app.app_context():
        return Product.add(payload)


def test_get_products_for_auto_render_filters_products(app, product_type_id, report_item):
    with app.app_context():
        other_report, status = ReportItem.add(
            {"title": "Other Report", "report_item_type_id": report_item.report_item_type_id},
            None,
        )
        if status != 200:
            raise AssertionError(f"Report item creation failed with status {status}")

    included = _create_product(
        app,
        product_type_id,
        report_item,
        title="Auto Product",
        auto_publish=True,
        default_publisher="publisher-1",
    )
    _create_product(
        app,
        product_type_id,
        report_item,
        title="Manual Product",
        auto_publish=False,
        default_publisher="publisher-2",
    )
    _create_product(
        app,
        product_type_id,
        other_report,
        title="Other Report Product",
        auto_publish=True,
        default_publisher="publisher-3",
    )

    with app.app_context():
        products = ProductService.get_products_for_auto_render(report_item.id)

    assert [product.id for product in products] == [included.id]


def test_autopublish_product_enqueues_only_products_with_publishers(app, product_type_id, report_item, monkeypatch):
    _create_product(
        app,
        product_type_id,
        report_item,
        title="Auto - No Publisher",
        auto_publish=True,
        default_publisher=None,
    )
    publishable = _create_product(
        app,
        product_type_id,
        report_item,
        title="Auto - Default Publisher",
        auto_publish=True,
        default_publisher="publisher-default",
    )

    mock_queue_manager = MagicMock()
    monkeypatch.setattr(queue_manager, "queue_manager", mock_queue_manager)

    with app.app_context():
        ProductService.autopublish_product(report_item.id)

    mock_queue_manager.autopublish_product.assert_called_once_with(publishable.id, publishable.default_publisher)
