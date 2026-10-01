from unittest.mock import patch

import pytest

from worker.publishers.execution_context import PublisherNetworkTimeout


def test_ftp_publisher_times_out_while_waiting_for_server_banner(ftp_publisher, get_product_mock, stalled_tcp_server):
    from tests.publishers.publishers_data import product_text

    host, port = stalled_tcp_server
    publisher = {"parameters": {"FTP_URL": f"ftp://user:password@{host}:{port}/", "NETWORK_TIMEOUT": 0.05}}

    with pytest.raises(PublisherNetworkTimeout, match="FTP publisher timed out during connect"):
        ftp_publisher.publish(publisher, product_text, get_product_mock)


def test_ftp_publisher_applies_timeout_and_closes_connection(ftp_publisher, get_product_mock, recording_ftp_factory):
    from tests.publishers.publishers_data import product_text

    ftp = recording_ftp_factory()
    publisher = {"parameters": {"FTP_URL": "ftp://user:password@example.test/", "NETWORK_TIMEOUT": 12}}
    with patch("ftplib.FTP", return_value=ftp):
        assert ftp_publisher.publish(publisher, product_text, get_product_mock) == "Successfully uploaded to FTP server"

    assert ftp.calls[0] == ("connect", {"host": "example.test", "port": 21, "timeout": 12.0})
    assert [name for name, _details in ftp.calls][-2:] == ["quit", "close"]
