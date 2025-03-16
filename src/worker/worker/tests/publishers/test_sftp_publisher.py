def test_sftp_publisher_publish(sftp_publisher, get_product_mock, sftp_mock):
    from worker.tests.publishers.publishers_data import product_text

    sftp_publisher_data = {
        "parameters": {
            "SFTP_URL": f"sftp://user:password@{sftp_mock.host}:{sftp_mock.port}",
        }
    }

    with sftp_mock.client("user") as client:
        sftp_publisher.ssh = client

    result = sftp_publisher.publish(sftp_publisher_data, product_text, get_product_mock)
    assert result == "SFTP Publisher Task Successful"
