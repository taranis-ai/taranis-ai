import pytest

from worker.publishers.execution_context import PublisherNetworkTimeout


def test_email_publisher_publish(email_publisher, get_product_mock, smtp_mock):
    from tests.publishers.publishers_data import email_publisher_admin_input, product_text

    result = email_publisher.publish(email_publisher_admin_input, product_text, get_product_mock)
    assert result == "Email Publisher: Task Successful"
    smtp_mock.sendmail.assert_called()
    smtp_mock.quit.assert_called_once()
    smtp_mock.close.assert_called_once()


def test_email_publisher_publish_pdf(email_publisher, get_product_pdf_mock, smtp_mock):
    from tests.publishers.publishers_data import email_publisher_admin_input, product_text

    result = email_publisher.publish(email_publisher_admin_input, product_text, get_product_pdf_mock)
    assert result == "Email Publisher: Task Successful"
    smtp_mock.sendmail.assert_called()


def test_publish_without_user_input(email_publisher):
    from tests.publishers.publishers_data import email_publisher_admin_input

    with pytest.raises(ValueError, match="No user input provided"):
        email_publisher.publish(email_publisher_admin_input, None, None)


def test_email_publisher_times_out_while_waiting_for_server_banner(email_publisher, stalled_tcp_server):
    from tests.publishers.publishers_data import email_publisher_admin_input, product_text

    host, port = stalled_tcp_server
    publisher = {
        "parameters": email_publisher_admin_input["parameters"]
        | {"SMTP_SERVER_ADDRESS": host, "SMTP_SERVER_PORT": port, "NETWORK_TIMEOUT": 0.05}
    }

    with pytest.raises(PublisherNetworkTimeout, match="Email publisher timed out during connect"):
        email_publisher.publish(publisher, product_text, type("Product", (), {"data": b"body", "mime_type": "text/plain"})())
