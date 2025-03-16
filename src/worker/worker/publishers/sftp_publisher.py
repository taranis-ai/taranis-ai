import contextlib
from io import BytesIO
import paramiko
from urllib.parse import urlsplit, ParseResult
from base64 import b64decode

from worker.log import logger
from .base_publisher import BasePublisher


class SFTPPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.ftp_url = None
        self.ssh = paramiko.SSHClient()

        self.type = "SFTP_PUBLISHER"
        self.name = "SFTP Publisher"
        self.description = "Publisher for publishing to a SFTP server"

    def publish(self, publisher, product, rendered_product):
        parameters = publisher.get("parameters", {})
        ftp_url = parameters.get("SFTP_URL")
        private_key = parameters.get("PRIVATE_KEY")

        self.set_file_name(product)
        server_config = urlsplit(ftp_url)

        if rendered_product.mime_type in ["text/plain", "text/html"]:
            data_to_upload = BytesIO(rendered_product.data)
        else:
            data_to_upload = BytesIO(b64decode(rendered_product.data))

        self.input_validation(server_config, private_key)
        if private_key:
            private_key = self.parse_private_key(private_key)

        self.upload_to_sftp(server_config, data_to_upload, private_key=private_key)

        return "SFTP Publisher Task Successful"

    def input_validation(self, server_config: ParseResult, private_key: str):
        if not server_config.username:
            logger.error(f"{server_config.username=}")
            raise ValueError("Username is required for SFTP")

        if not private_key and not server_config.password:
            logger.error(f"Private key: {private_key}, Password: {server_config.password}")
            raise ValueError("Private key or password are required for SFTP")

        if server_config.scheme != "sftp":
            raise ValueError(f"Schema '{server_config.scheme}' not supported, choose 'sftp'")

    def parse_private_key(self, private_key: str) -> paramiko.PKey:
        from paramiko.rsakey import RSAKey
        from paramiko.dsskey import DSSKey
        from paramiko.ecdsakey import ECDSAKey
        from paramiko.ed25519key import Ed25519Key

        for pkey_class in (RSAKey, DSSKey, ECDSAKey, Ed25519Key):
            with contextlib.suppress(paramiko.SSHException):
                return pkey_class.from_private_key(BytesIO(private_key.encode("utf-8")))

    def upload_to_sftp(self, server_config: ParseResult, data_to_upload: BytesIO, private_key: paramiko.PKey = None):
        ssh_port = server_config.port or 22
        remote_path = server_config.path + self.file_name
        if private_key:
            server_config.password = None

        logger.debug(f"Uploading to SFTP: {server_config.hostname}:{ssh_port} {remote_path}")

        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname=server_config.hostname,
            port=ssh_port,
            username=server_config.username,
            password=server_config.password,
            pkey=private_key,
            look_for_keys=False,
            allow_agent=False,
        )
        with self.ssh.open_sftp() as sftp:
            sftp.putfo(data_to_upload, remote_path)
        self.ssh.close()
