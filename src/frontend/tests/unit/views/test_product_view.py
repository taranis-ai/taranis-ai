from unittest.mock import patch

from flask import Response as FlaskResponse
from requests import Response
from requests.structures import CaseInsensitiveDict


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
