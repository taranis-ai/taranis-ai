from unittest.mock import patch

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
    core_response._content = expected_content
    core_response.headers = headers

    with patch("frontend.views.product_views.CoreApi") as core_api_cls:
        core_api_instance = core_api_cls.return_value
        core_api_instance.download_product.return_value = core_response

        response = authenticated_client.get(f"/product/{product_id}/download")

    core_api_instance.download_product.assert_called_once_with(product_id)
    assert response.status_code == core_response.status_code
    assert response.data == expected_content
    assert response.headers["Content-Type"] == headers["Content-Type"]
    assert response.headers["Content-Disposition"] == headers["Content-Disposition"]
