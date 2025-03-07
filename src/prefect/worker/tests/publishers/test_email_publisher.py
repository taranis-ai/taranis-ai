import pytest


def test_email_publisher_publish(email_publisher, get_product_mock, smtp_mock):
    from worker.tests.publishers.publishers_data import email_publisher_admin_input, product_text

    result = email_publisher.publish(email_publisher_admin_input, product_text, get_product_mock)
    assert result == "Email Publisher: Task Successful"
    smtp_mock.sendmail.assert_called()


def test_email_publisher_publish_pdf(email_publisher, get_product_pdf_mock, smtp_mock):
    from worker.tests.publishers.publishers_data import email_publisher_admin_input, product_text

    result = email_publisher.publish(email_publisher_admin_input, product_text, get_product_pdf_mock)
    assert result == "Email Publisher: Task Successful"
    smtp_mock.sendmail.assert_called()


def test_publish_without_smtp_address(email_publisher, get_product_mock):
    from worker.tests.publishers.publishers_data import email_publisher_admin_input_no_smtp_address, product_text

    with pytest.raises(ValueError, match="No SMTP server address provided"):
        email_publisher.publish(email_publisher_admin_input_no_smtp_address, product_text, get_product_mock)


def test_publish_without_user_input(email_publisher):
    from worker.tests.publishers.publishers_data import email_publisher_admin_input

    with pytest.raises(ValueError, match="No user input provided"):
        email_publisher.publish(email_publisher_admin_input, None, None)
