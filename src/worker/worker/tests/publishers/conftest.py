from unittest.mock import patch

import mockssh
import pytest
from pytest import yield_fixture

import worker.publishers as publishers


class MockProduct:
    def __init__(self, data, mime_type):
        self.data: bytes = data
        self.mime_type: str = mime_type


class RecordingPublisher:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result if result is not None else {"message": "published"}
        self.error = error
        self.calls: list[dict[str, object]] = []

    def publish(self, publisher, product, rendered_product):
        self.calls.append(
            {
                "publisher": publisher,
                "product": product,
                "rendered_product": rendered_product,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result


class RecordingCoreApi:
    def __init__(self, product=None, publisher=None, rendered_product=None, put_response=None):
        self.product = product if product is not None else {"id": "prod-123", "title": "Example Product"}
        self.publisher = publisher if publisher is not None else {"id": "pub-1", "type": "email_publisher"}
        self.rendered_product = rendered_product if rendered_product is not None else object()
        self.put_response = put_response if put_response is not None else {"message": "saved"}
        self.seen: dict[str, object] = {}
        self.put_calls: list[dict[str, object]] = []

    def get_product(self, product_id):
        self.seen["product_id"] = product_id
        return self.product

    def get_publisher(self, publisher_id):
        self.seen["publisher_id"] = publisher_id
        return self.publisher

    def get_product_render(self, product_id):
        self.seen["render_product_id"] = product_id
        return self.rendered_product

    def api_put(self, url: str, json_data=None):
        self.put_calls.append({"url": url, "json": json_data})
        return self.put_response


@pytest.fixture
def email_publisher():
    return publishers.EMAILPublisher()


@pytest.fixture
def sftp_publisher():
    yield publishers.SFTPPublisher()


@pytest.fixture
def s3_publisher():
    yield publishers.S3Publisher()


@pytest.fixture
def taxii_publisher():
    yield publishers.TAXIIPublisher()


@pytest.fixture
def s3_publisher_testdata():
    s3_publisher_data = {
        "S3_ENDPOINT": "play.min.io",
        "S3_ACCESS_KEY": "Q3AM3UQ867SPQQA43P2F",
        "S3_SECRET_KEY": "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
        "S3_BUCKET_NAME": "taranis-test-bucket",
    }
    yield {"parameters": s3_publisher_data}


@pytest.fixture
def get_product_mock():
    from worker.tests.publishers.publishers_data import product_render_data, product_render_mime

    yield MockProduct(product_render_data, product_render_mime)


@pytest.fixture
def get_product_pdf_mock():
    from worker.tests.publishers.publishers_data import product_render_data_pdf, product_render_mime_pdf

    yield MockProduct(product_render_data_pdf, product_render_mime_pdf)


@pytest.fixture
def recording_publisher_factory():
    def _factory(result=None, error: Exception | None = None):
        return RecordingPublisher(result=result, error=error)

    return _factory


@pytest.fixture
def recording_core_api_factory():
    def _factory(product=None, publisher=None, rendered_product=None, put_response=None):
        return RecordingCoreApi(
            product=product,
            publisher=publisher,
            rendered_product=rendered_product,
            put_response=put_response,
        )

    return _factory


@pytest.fixture
def smtp_mock():
    with patch("smtplib.SMTP", autospec=True) as mock:
        smtp_instance = mock.return_value
        smtp_instance.sendmail.return_value = {}
        yield smtp_instance


@yield_fixture()
def sftp_mock(request):
    import glob
    import os

    from worker.tests.publishers.publishers_data import product_text

    users = {
        "user": {"type": "password", "password": "password"},
    }
    with mockssh.Server(users) as s:  # type: ignore
        yield s

    for product in glob.glob(f"{product_text['title']}*"):
        os.remove(product)
