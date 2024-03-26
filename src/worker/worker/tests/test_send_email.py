from unittest.mock import patch
from unittest.mock import MagicMock
import pytest

import worker.publishers as publishers


@pytest.fixture
def email_publisher():
    return publishers.email_publisher.EMAILPublisher()


@pytest.fixture
def get_product_mock(requests_mock):
    from worker.tests.publishers_data import product_render_data, product_render_mime

    requests_mock.get(
        "http://taranis/api/worker/products/1/render", content=product_render_data, headers={"Content-Type": product_render_mime}
    )


@pytest.fixture
def smtp_mock():
    with patch("smtplib.SMTP", autospec=True) as mock:
        smtp_instance = mock.return_value
        smtp_instance.sendmail.return_value = {}
        yield smtp_instance


def test_email_publisher_publish(email_publisher, get_product_mock, smtp_mock):
    from worker.tests.publishers_data import email_publisher_admin_input, email_publisher_input

    result = email_publisher.publish(email_publisher_admin_input, email_publisher_input)
    assert result == {"message": "Email Publisher: Task Successful"}
    smtp_mock.sendmail.assert_called()


def test_publish_without_smtp_address(email_publisher):
    from worker.tests.publishers_data import email_publisher_admin_input_no_smtp_address, email_publisher_input

    result = email_publisher.publish(email_publisher_admin_input_no_smtp_address, email_publisher_input)
    assert result == {"error": "No SMTP server address provided"}


def test_publish_without_user_input(email_publisher):
    from worker.tests.publishers_data import email_publisher_admin_input

    result = email_publisher.publish(email_publisher_admin_input, None)
    assert result == {"error": "No user input provided"}
