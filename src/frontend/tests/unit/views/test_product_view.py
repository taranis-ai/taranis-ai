from unittest.mock import call, patch

import pytest
from flask import render_template, render_template_string, url_for
from models.product import Product, ProductMetadata, ProductTypeChoice, PublisherPreset
from models.report import ReportItem
from pydantic import ValidationError
from responses import matchers

from frontend.cache_models import PagingData
from frontend.config import Config
from frontend.views.product_views import ProductView


@pytest.mark.parametrize(
    "url",
    [
        "//evil.example/report",
        "javascript:alert(1)",
        "https://user:password@example.com/report",
        "https://example.com\\@evil.example/report",
        "/reports/good\njavascript:alert(1)",
        "/reports/product-1 ",
        " https://reports.example/product-1",
    ],
)
def test_product_rejects_unsafe_last_published_urls(url):
    with pytest.raises(ValidationError, match="URL is not safe to open"):
        Product(title="Product", product_type_id="product-type-1", last_published_url=url)


@pytest.mark.parametrize("url", ["/reports/product-1", "https://reports.example/product-1"])
def test_product_accepts_safe_last_published_urls(url):
    product = Product(title="Product", product_type_id="product-type-1", last_published_url=url)

    assert product.last_published_url == url


@pytest.mark.parametrize(
    ("last_published_url", "expected_test_id"),
    [
        ("/reports/product-1", "last-published-product-link"),
        (None, "last-published-product-empty"),
    ],
)
def test_product_view_always_shows_last_publication_section(app, last_published_url, expected_test_id):
    product = Product.model_construct(
        id="product-1",
        title="Existing product",
        description="existing",
        product_type_id="product-type-1",
        report_items=[],
        supported_reports=[],
        last_published_url=last_published_url,
        render_result=None,
        mime_type=None,
    )

    with app.test_request_context("/publish/product-1"):
        markup = render_template(
            "publish/product.html",
            product=product,
            product_types=[],
            publishers=[],
            selected_report_items=[],
            supported_reports=[],
            submit_text="Update Product",
            is_edit=True,
            form_action='hx-put="/frontend/publish/product-1"',
        )

    assert 'data-testid="last-published-product"' in markup
    assert f'data-testid="{expected_test_id}"' in markup
    if last_published_url:
        assert f'href="{last_published_url}"' in markup
        assert 'target="_blank"' in markup
        assert 'rel="noopener noreferrer"' in markup


def test_product_download_streams_core_response(authenticated_client, responses_mock):
    product_id = "product-download-test"
    expected_content = b"binary-product" * 10000
    headers = {
        "Content-Type": "application/pdf",
        "Content-Disposition": 'attachment; filename="core-product.pdf"',
    }
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/publish/products/{product_id}/render",
        body=expected_content,
        headers=headers,
    )

    response = authenticated_client.get(f"/product/{product_id}/download")
    try:
        assert response.status_code == 200
        assert response.is_streamed
        assert response.data == expected_content
        assert response.headers["Content-Type"] == headers["Content-Type"]
        assert response.headers["Content-Disposition"] == headers["Content-Disposition"]
    finally:
        response.close()
    assert responses_mock.calls[0].response.raw.closed


def test_product_list_does_not_load_editor_catalogs():
    with patch("frontend.views.product_views.DataPersistenceLayer") as persistence_cls:
        context = ProductView.get_extra_context({"products": []})

    assert context == {"products": []}
    persistence_cls.assert_not_called()


def test_product_view_preselects_report_from_query(app):
    product_type = ProductTypeChoice(id="product-type-1", title="CERT Daily Report")
    report = ReportItem.model_construct(id="report-1", title="Selected report", report_item_type_id="report-type-1")
    product_instance = Product.model_construct(
        id="product-1",
        title="Existing product",
        description="existing",
        product_type_id="product-type-1",
        report_items=["report-2"],
        supported_reports=[{"id": "report-2", "title": "Already selected"}],
    )

    with patch("frontend.views.product_views.DataPersistenceLayer") as persistence_cls:
        persistence = persistence_cls.return_value
        persistence.get_objects.side_effect = [
            [
                PublisherPreset.model_construct(
                    id="publisher-1", name="FTP Publisher", description="Primary FTP publisher", type="FTP_PUBLISHER"
                )
            ],
            [product_type],
        ]
        persistence.get_object.return_value = report

        with app.test_request_context("/publish/product-1?report_id=report-1"):
            context = ProductView.get_extra_context({"product": product_instance})

    assert persistence.get_objects.call_args_list == [
        call(PublisherPreset),
        call(ProductTypeChoice, PagingData(query_params={"report_ids": ["report-1", "report-2"]}).set_fetch_all()),
    ]
    assert context["selected_report_items"] == ["report-2", "report-1"]
    assert context["supported_reports"] == [{"id": "report-2", "title": "Already selected"}, report.model_dump(mode="json")]


def test_product_view_uses_core_choices_cached_by_report_selection(app, responses_mock, test_cache_backend):
    for report_id, type_id in [("report-1", "type-1"), ("report-2", "type-2")]:
        responses_mock.get(
            f"{Config.TARANIS_CORE_URL}/publish/product-type-choices",
            match=[matchers.query_param_matcher({"report_ids": report_id, "fetch_all": "true"})],
            json={"items": [{"id": type_id, "title": type_id}]},
        )

    for report_id, type_id in [("report-1", "type-1"), ("report-2", "type-2"), ("report-1", "type-1")]:
        product = Product(title="New product", product_type_id=type_id, id="0", report_items=[report_id])
        with app.test_request_context("/publish/0"):
            context = ProductView.get_extra_context({"product": product})
            markup = render_template("publish/product.html", **context)
        assert context["product_types"] == [{"id": type_id, "name": type_id}]
        assert f'value="{type_id}"' in markup
    assert len(responses_mock.calls) == 2


@pytest.mark.parametrize("report_items", [[], ["report-1", "report-2"]])
def test_product_copy_prefills_only_creation_fields(app, report_items):
    source = Product(
        id="source-product",
        title="Daily report",
        description="Daily summary",
        product_type_id="product-type-1",
        report_items=report_items,
        supported_reports=[{"id": report_id, "title": report_id} for report_id in report_items],
        render_result="cmVuZGVyZWQ=",
        mime_type="text/html",
        last_published_url="/reports/source-product",
        auto_publish=True,
        default_publisher="publisher-1",
    )
    with patch("frontend.views.product_views.DataPersistenceLayer") as persistence_cls:
        persistence = persistence_cls.return_value
        persistence.get_object.return_value = source
        persistence.get_objects.side_effect = [
            [ProductTypeChoice(id="product-type-1", title="Daily")],
            [],
        ]
        with app.test_request_context("/publish/0?copy_from=source-product"):
            context = ProductView.get_create_context()
            markup = render_template("publish/product.html", **context)

    product = context["product"]
    assert product == Product(
        id="0",
        title="Daily report Copy",
        description=source.description,
        product_type_id=source.product_type_id,
        report_items=report_items,
    )
    assert context["selected_report_items"] == report_items
    assert context["supported_reports"] == source.supported_reports
    assert context["is_edit"] is False
    assert context["submit_text"] == "Create Product"
    assert "hx-post=" in markup and "hx-put=" not in markup
    assert 'value="Daily report Copy"' in markup
    assert "cmVuZGVyZWQ=" not in markup
    assert "/reports/source-product" not in markup
    assert source.title == "Daily report"
    persistence.get_object.assert_called_once_with(ProductMetadata, "source-product")
    persistence.store_object.assert_not_called()


def test_product_table_actions_link_to_each_product_copy(app):
    with app.test_request_context("/publish"):
        for product_id in ["product-1", "product-2"]:
            markup = render_template_string(
                "{% from 'macros/table.html' import table_actions %}{{ table_actions(actions, item_id, base_url) }}",
                actions=ProductView.get_default_actions(),
                item_id=product_id,
                base_url=ProductView.get_base_route(),
            )
            assert f'href="{url_for("publish.product", product_id="0", copy_from=product_id)}"' in markup
            assert 'aria-label="Create copy"' in markup
            assert f'href="{url_for("publish.product", product_id=product_id)}"' in markup
            assert f'hx-delete="{url_for("publish.product", product_id=product_id)}"' in markup


def test_product_copy_missing_source_returns_not_found(authenticated_client):
    with patch("frontend.views.product_views.DataPersistenceLayer") as persistence_cls:
        persistence_cls.return_value.get_objects.return_value = []
        persistence_cls.return_value.get_object.return_value = None
        response = authenticated_client.get("/publish/0?copy_from=missing")

    assert response.status_code == 404
