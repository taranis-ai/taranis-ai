import pytest

from worker.publishers.network import PublisherNetworkTimeout


def test_ftp_publisher_times_out_while_waiting_for_server_banner(ftp_publisher, get_product_mock, stalled_tcp_server):
    from tests.publishers.publishers_data import product_text

    host, port = stalled_tcp_server
    publisher = {"parameters": {"FTP_URL": f"ftp://user:password@{host}:{port}/", "NETWORK_TIMEOUT": 0.05}}

    with pytest.raises(PublisherNetworkTimeout, match="FTP publisher timed out during connect"):
        ftp_publisher.publish(publisher, product_text, get_product_mock)
