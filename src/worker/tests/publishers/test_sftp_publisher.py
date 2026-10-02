from pathlib import Path

import paramiko
import pytest
from mockssh.server import SERVER_KEY_PATH

from worker.publishers.network import PublisherNetworkTimeout


pytestmark = pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")


@pytest.mark.parametrize("accept_any", [False, True], ids=["pinned-key", "accept-any-key"])
def test_sftp_publisher_publish(sftp_publisher, get_product_mock, sftp_mock, accept_any):
    from tests.publishers.publishers_data import product_text

    key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
    parameters = {"SFTP_URL": f"sftp://user:password@{sftp_mock.host}:{sftp_mock.port}"}
    if accept_any:
        parameters["ACCEPT_ANY_HOST_KEY"] = True
        parameters["HOST_KEY"] = "ignored when accepting any key"
    else:
        parameters["HOST_KEY"] = f"{key.get_name()} {key.get_base64()} server comment\n"

    result = sftp_publisher.publish({"parameters": parameters}, product_text, get_product_mock)
    assert result == "SFTP Publisher Task Successful"
    assert Path(sftp_publisher.file_name).read_bytes() == get_product_mock.data
    assert sftp_publisher.ssh.get_transport() is None

    parameters.pop("HOST_KEY")
    parameters["ACCEPT_ANY_HOST_KEY"] = False
    with pytest.raises(ValueError, match="host public key is required"):
        sftp_publisher.publish({"parameters": parameters}, product_text, get_product_mock)


@pytest.mark.parametrize("host_key", ["", "invalid", "ssh-rsa !!!", "changed"], ids=["missing", "malformed", "invalid-base64", "changed"])
def test_sftp_publisher_rejects_untrusted_host(sftp_publisher, get_product_mock, sftp_mock, host_key):
    from tests.publishers.publishers_data import product_text

    changed_key = host_key == "changed"
    if changed_key:
        key = paramiko.RSAKey.generate(2048)
        host_key = f"{key.get_name()} {key.get_base64()}"
    publisher = {"parameters": {"SFTP_URL": f"sftp://user:password@{sftp_mock.host}:{sftp_mock.port}", "HOST_KEY": host_key}}

    error = paramiko.BadHostKeyException if changed_key else ValueError
    with pytest.raises(error, match=r"does not match|host public key"):
        sftp_publisher.publish(publisher, product_text, get_product_mock)
    assert sftp_publisher.ssh.get_transport() is None
    assert not Path(sftp_publisher.file_name).exists()


def test_sftp_publisher_rejects_upload_size_mismatch(monkeypatch, sftp_publisher, get_product_mock, mismatched_ssh_client_factory):
    from tests.publishers.publishers_data import product_text

    client = mismatched_ssh_client_factory()
    monkeypatch.setattr(paramiko, "SSHClient", lambda: client)
    monkeypatch.setattr(paramiko, "SFTPClient", lambda _channel: client.sftp)
    publisher = {
        "parameters": {
            "SFTP_URL": "sftp://user:password@example.test/",
            "ACCEPT_ANY_HOST_KEY": True,
        }
    }

    with pytest.raises(OSError, match="upload size confirmation failed"):
        sftp_publisher.publish(publisher, product_text, get_product_mock)


@pytest.mark.parametrize("sftp_mock", ["stalled"], indirect=True)
def test_sftp_publisher_times_out_during_negotiation(sftp_publisher, get_product_mock, sftp_mock):
    from tests.publishers.publishers_data import product_text

    key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
    publisher = {
        "parameters": {
            "SFTP_URL": f"sftp://user:password@{sftp_mock.host}:{sftp_mock.port}",
            "HOST_KEY": f"{key.get_name()} {key.get_base64()}",
            "NETWORK_TIMEOUT": 0.5,
        }
    }

    with pytest.raises(PublisherNetworkTimeout, match="SFTP publisher timed out during open_channel"):
        sftp_publisher.publish(publisher, product_text, get_product_mock)

    assert sftp_publisher.ssh.get_transport() is None
    assert not Path(sftp_publisher.file_name).exists()
