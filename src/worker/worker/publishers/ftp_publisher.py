import ftplib
from base64 import b64decode
from io import BytesIO
from urllib.parse import ParseResult, urlparse

from worker.log import logger

from .base_publisher import BasePublisher


class FTPPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.ftp_url = None

        self.type = "FTP_PUBLISHER"
        self.name = "FTP Publisher"
        self.description = "Publisher for publishing to FTP server"

    def publish(self, publisher, product, rendered_product):
        parameters = self._extract_parameters(publisher)
        ftp_url = parameters.get("FTP_URL")

        self.set_file_name(product)
        server_config: ParseResult = urlparse(ftp_url)  # type: ignore
        rendered_data = self._require_rendered_data(rendered_product)

        if rendered_product.mime_type in ["text/plain", "text/html"]:
            data_to_upload = BytesIO(rendered_data)
        else:
            data_to_upload = BytesIO(b64decode(rendered_data))

        self.upload_to_ftp(server_config, data_to_upload)
        logger.info({"message": f"Successfully uploaded {self.file_name} to FTP server"})
        return "Successfully uploaded to FTP server"

    def upload_to_ftp(self, server_config: ParseResult, data_to_upload: BytesIO):
        ftp_port = server_config.port or 21
        remote_path = server_config.path + self.file_name
        host_name = server_config.hostname

        if not host_name:
            raise ValueError("Hostname is required for FTP")

        if server_config.scheme != "ftp":
            raise ValueError(f"Schema '{server_config.scheme}' not supported, choose 'ftp'")

        with ftplib.FTP() as ftp:
            ftp.connect(host=host_name, port=ftp_port)
            if server_config.username and server_config.password:
                ftp.login(server_config.username, server_config.password)
            ftp.storbinary(f"STOR {remote_path}", data_to_upload)
