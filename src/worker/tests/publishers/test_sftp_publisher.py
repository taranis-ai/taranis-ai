from functools import partial
from pathlib import Path

import paramiko
import pytest
from mockssh.server import SERVER_KEY_PATH


def test_sftp_publisher_publish(sftp_publisher, get_product_mock, sftp_mock, tmp_path, monkeypatch):
    from tests.publishers.publishers_data import product_text

    known_hosts = tmp_path / "known_hosts"
    host_keys = paramiko.HostKeys()
    host_keys.add(f"[{sftp_mock.host}]:{sftp_mock.port}", "ssh-rsa", paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH))
    host_keys.save(str(known_hosts))
    monkeypatch.setattr(sftp_publisher.ssh, "load_system_host_keys", partial(sftp_publisher.ssh.load_system_host_keys, str(known_hosts)))
    sftp_publisher_data = {
        "parameters": {
            "SFTP_URL": f"sftp://user:password@{sftp_mock.host}:{sftp_mock.port}",
        }
    }

    result = sftp_publisher.publish(sftp_publisher_data, product_text, get_product_mock)
    assert result == "SFTP Publisher Task Successful"
    assert Path(sftp_publisher.file_name).read_bytes() == get_product_mock.data
    assert sftp_publisher.ssh.get_transport() is None


@pytest.mark.parametrize("changed_key", [False, True], ids=["unknown-host", "changed-host-key"])
def test_sftp_publisher_rejects_untrusted_host(sftp_publisher, get_product_mock, sftp_mock, tmp_path, monkeypatch, changed_key):
    from tests.publishers.publishers_data import product_text

    known_hosts = tmp_path / "known_hosts"
    host_keys = paramiko.HostKeys()
    if changed_key:
        host_keys.add(f"[{sftp_mock.host}]:{sftp_mock.port}", "ssh-rsa", paramiko.RSAKey.generate(2048))
    host_keys.save(str(known_hosts))
    monkeypatch.setattr(sftp_publisher.ssh, "load_system_host_keys", partial(sftp_publisher.ssh.load_system_host_keys, str(known_hosts)))
    publisher = {"parameters": {"SFTP_URL": f"sftp://user:password@{sftp_mock.host}:{sftp_mock.port}"}}

    error = paramiko.BadHostKeyException if changed_key else paramiko.SSHException
    with pytest.raises(error, match=r"does not match|not found in known_hosts"):
        sftp_publisher.publish(publisher, product_text, get_product_mock)
    assert sftp_publisher.ssh.get_transport() is None
    assert not Path(sftp_publisher.file_name).exists()
