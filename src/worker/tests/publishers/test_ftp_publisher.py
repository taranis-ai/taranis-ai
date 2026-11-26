import unicodedata

import pytest

from worker.publishers.base_publisher import BasePublisher
from worker.publishers.network import PublisherNetworkTimeout


def test_ftp_publisher_times_out_while_waiting_for_server_banner(ftp_publisher, get_product_mock, stalled_tcp_server):
    from tests.publishers.publishers_data import product_text

    host, port = stalled_tcp_server
    publisher = {"parameters": {"FTP_URL": f"ftp://user:password@{host}:{port}/", "NETWORK_TIMEOUT": 0.05}}

    with pytest.raises(PublisherNetworkTimeout, match="FTP publisher timed out during connect"):
        ftp_publisher.publish(publisher, product_text, get_product_mock)


@pytest.mark.parametrize(
    "title",
    ["../target", "..\\target", "．．／target", "target\x00\r\n", "界" * 300],
    ids=["posix-separators", "windows-separators", "normalized-separators", "controls", "excessive-length"],
)
def test_remote_file_name_is_a_bounded_basename(title):
    file_name = BasePublisher.get_safe_remote_file_name({"title": title, "mime_type": "text/plain"})

    assert file_name == unicodedata.normalize("NFKC", file_name)
    assert "/" not in file_name
    assert "\\" not in file_name
    assert ".." not in file_name
    assert not any(unicodedata.category(character).startswith("C") for character in file_name)
    assert len(file_name.encode("utf-8")) <= 240
