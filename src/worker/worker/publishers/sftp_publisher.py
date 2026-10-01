import contextlib
from base64 import b64decode
from io import BytesIO, StringIO
from typing import Any
from urllib.parse import ParseResult, urlparse

import paramiko
from rq.timeouts import JobTimeoutException

from worker.log import logger
from worker.publishers.execution_context import publisher_cleanup

from .base_publisher import BasePublisher


class SFTPPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.ftp_url = None
        self.ssh = paramiko.SSHClient()

        self.type = "SFTP_PUBLISHER"
        self.name = "SFTP Publisher"
        self.description = "Publisher for publishing to a SFTP server"

    def publish(self, publisher: dict[str, Any], product, rendered_product):
        parameters = self._extract_parameters(publisher)
        ftp_url = parameters.get("SFTP_URL")
        private_key = parameters.get("PRIVATE_KEY")
        timeout = self._network_timeout(parameters)

        self.set_file_name(product)
        server_config: ParseResult = urlparse(ftp_url)  # type: ignore
        rendered_data = self._require_rendered_data(rendered_product)

        if rendered_product.mime_type in ["text/plain", "text/html"]:
            data_to_upload = BytesIO(rendered_data)
        else:
            data_to_upload = BytesIO(b64decode(rendered_data))

        if not server_config:
            raise ValueError("Invalid SFTP URL")
        self.input_validation(server_config)
        if private_key:
            private_key = self.parse_private_key(private_key)

        self.upload_to_sftp(
            server_config,
            data_to_upload,
            private_key=private_key,
            host_key=parameters.get("HOST_KEY", ""),
            accept_any_host_key=parameters.get("ACCEPT_ANY_HOST_KEY", False) is True,
            timeout=timeout,
        )

        return "SFTP Publisher Task Successful"

    def input_validation(self, server_config: ParseResult):
        if not server_config.username:
            logger.error("Username is required for SFTP")
            raise ValueError("Username is required for SFTP")

        if server_config.scheme != "sftp":
            raise ValueError(f"Schema '{server_config.scheme}' not supported, choose 'sftp'")

    def parse_private_key(self, private_key: str) -> paramiko.PKey:
        from paramiko.ecdsakey import ECDSAKey
        from paramiko.ed25519key import Ed25519Key
        from paramiko.rsakey import RSAKey

        for pkey_class in (RSAKey, ECDSAKey, Ed25519Key):
            with contextlib.suppress(paramiko.SSHException):
                return pkey_class.from_private_key(StringIO(private_key))
        raise ValueError("Invalid private key format for SFTP")

    def upload_to_sftp(
        self,
        server_config: ParseResult,
        data_to_upload: BytesIO,
        private_key: paramiko.PKey | None = None,
        host_key: str = "",
        accept_any_host_key: bool = False,
        timeout: float = 30,
    ):
        ssh_port = server_config.port or 22
        remote_path = server_config.path + self.file_name
        connect_password = None if private_key else server_config.password
        hostname = server_config.hostname
        if not hostname:
            raise ValueError("Hostname is required for SFTP")

        self.ssh = paramiko.SSHClient()
        if accept_any_host_key:
            # codeql[py/paramiko-missing-host-key-validation] Admin explicitly accepts this risk; disabled by default.
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            if not host_key.strip():
                raise ValueError("A server host public key is required for SFTP")
            try:
                key_type, key_data, *_ = host_key.split()
                key = paramiko.PKey.from_type_string(key_type, b64decode(key_data, validate=True))
            except JobTimeoutException:
                raise
            except Exception as exc:
                logger.error(f"Invalid SFTP server host public key: exception_type={type(exc).__name__}")
                raise ValueError("Invalid SFTP server host public key; use OpenSSH public key format") from None
            host = hostname if ssh_port == 22 else f"[{hostname}]:{ssh_port}"
            self.ssh.get_host_keys().add(host, key.get_name(), key)
            self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        sftp = None
        try:
            with self._network_phase("connect_and_authenticate"):
                self.ssh.connect(
                    hostname=hostname,
                    port=ssh_port,
                    username=server_config.username,
                    password=connect_password,
                    pkey=private_key,
                    look_for_keys=False,
                    allow_agent=False,
                    timeout=timeout,
                    banner_timeout=timeout,
                    auth_timeout=timeout,
                    channel_timeout=timeout,
                )
            with self._network_phase("open_channel"):
                transport = self.ssh.get_transport()
                if transport is None:
                    raise paramiko.SSHException("SSH transport unavailable")
                channel = transport.open_session(timeout=timeout)
                channel.settimeout(timeout)
                channel.invoke_subsystem("sftp")
                sftp = paramiko.SFTPClient(channel)
            expected_size = data_to_upload.getbuffer().nbytes
            with self._network_phase("upload"):
                sftp.putfo(data_to_upload, remote_path, confirm=False)
            with self._network_phase("confirm"):
                actual_size = sftp.stat(remote_path).st_size
                if actual_size != expected_size:
                    raise OSError("SFTP upload size confirmation failed")
        finally:
            try:
                self._start_close_phase()
                if sftp is not None:
                    with publisher_cleanup():
                        sftp.close()
            finally:
                with publisher_cleanup():
                    self.ssh.close()
