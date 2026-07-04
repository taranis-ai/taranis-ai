from unittest.mock import call, patch

from flask import Response as FlaskResponse
from models.product import Product, ProductType, PublisherPreset
from models.report import ReportItem
from requests import Response
from requests.structures import CaseInsensitiveDict

from frontend.views.product_views import ProductView


def test_product_download_streams_core_response(authenticated_client):
    product_id = "product-download-test"
    expected_content = b"binary-product"
    headers = CaseInsensitiveDict(
        {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="core-product.pdf"',
        }
    )

    core_response = Response()
    core_response.status_code = 200
    core_response.headers = headers

    proxied = FlaskResponse(
        expected_content,
        status=200,
        headers={
            "Content-Type": headers["Content-Type"],
            "Content-Disposition": headers["Content-Disposition"],
        },
    )

    with patch("frontend.views.product_views.CoreApi") as core_api_cls:
        core_api_instance = core_api_cls.return_value
        core_api_instance.download_product.return_value = core_response
        core_api_cls.stream_proxy.return_value = proxied

        response = authenticated_client.get(f"/product/{product_id}/download")

    core_api_instance.download_product.assert_called_once_with(product_id)
    assert response.status_code == core_response.status_code
    assert response.data == expected_content
    assert response.headers["Content-Type"] == headers["Content-Type"]
    assert response.headers["Content-Disposition"] == headers["Content-Disposition"]


def test_product_view_uses_publish_product_types_endpoint():
    product_types = [
        ProductType(
            id="product-type-1",
            title="CERT Daily Report",
            description="cert.at Daily Report HTML",
            type="HTML_PRESENTER",
        )
    ]
    publishers = [
        PublisherPreset(
            id="publisher-1",
            name="FTP Publisher",
            description="Primary FTP publisher",
            type="FTP_PUBLISHER",
        )
    ]

    with patch("frontend.views.product_views.DataPersistenceLayer") as persistence_cls:
        persistence = persistence_cls.return_value
        persistence.get_objects.side_effect = [product_types, publishers]

        context = ProductView.get_extra_context({})

    assert persistence.get_objects.call_args_list == [call(ProductType), call(PublisherPreset)]
    assert context["product_types"] == [{"id": "product-type-1", "name": "CERT Daily Report"}]
    assert context["publishers"] == [{"id": "publisher-1", "name": "FTP Publisher"}]


def test_product_view_preselects_report_from_query(app):
    product_type = ProductType.model_construct(
        id="product-type-1", title="CERT Daily Report", description="cert.at Daily Report HTML", type="HTML_PRESENTER"
    )
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
            [product_type],
            [
                PublisherPreset.model_construct(
                    id="publisher-1", name="FTP Publisher", description="Primary FTP publisher", type="FTP_PUBLISHER"
                )
            ],
        ]
        persistence.get_object.return_value = report

        with app.test_request_context("/publish/product-1?report_id=report-1"):
            context = ProductView.get_extra_context({"product": product_instance})

    assert persistence.get_objects.call_args_list == [call(ProductType), call(PublisherPreset)]
    assert context["selected_report_items"] == ["report-2", "report-1"]
    assert context["supported_reports"] == [{"id": "report-2", "title": "Already selected"}, report.model_dump(mode="json")]
