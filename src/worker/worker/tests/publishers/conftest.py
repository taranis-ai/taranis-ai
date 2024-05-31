from unittest.mock import patch
from pytest import yield_fixture
import mockssh
import pytest

import worker.publishers as publishers


class MockProduct:
    def __init__(self, data, mime_type):
        self.data: bytes = data
        self.mime_type: str = mime_type


@pytest.fixture
def email_publisher():
    return publishers.EMAILPublisher()


@pytest.fixture
def sftp_publisher():
    return publishers.SFTPPublisher()


@pytest.fixture
def get_product_mock():
    from worker.tests.publishers.publishers_data import product_render_data, product_render_mime

    yield MockProduct(product_render_data, product_render_mime)


@pytest.fixture
def get_product_pdf_mock():
    from worker.tests.publishers.publishers_data import product_render_data_pdf, product_render_mime_pdf

    yield MockProduct(product_render_data_pdf, product_render_mime_pdf)


@pytest.fixture
def smtp_mock():
    with patch("smtplib.SMTP", autospec=True) as mock:
        smtp_instance = mock.return_value
        smtp_instance.sendmail.return_value = {}
        yield smtp_instance


@yield_fixture()
def sftp_mock(request):
    from worker.tests.publishers.publishers_data import product_text
    import os
    import glob

    users = {
        "user": {"type": "password", "password": "password"},
    }
    with mockssh.Server(users) as s:
        yield s

    for product in glob.glob(f"{product_text['title']}*"):
        os.remove(product)
