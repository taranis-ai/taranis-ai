import ftplib
from base64 import b64decode
from io import BytesIO
from urllib.parse import ParseResult, urlparse

from worker.log import logger
from worker.publishers.execution_context import publisher_cleanup

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
        timeout = self._network_timeout(parameters)

        self.set_file_name(product)
        server_config: ParseResult = urlparse(ftp_url)  # type: ignore
        rendered_data = self._require_rendered_data(rendered_product)

        if rendered_product.mime_type in ["text/plain", "text/html"]:
            data_to_upload = BytesIO(rendered_data)
        else:
            data_to_upload = BytesIO(b64decode(rendered_data))

        self.upload_to_ftp(server_config, data_to_upload, timeout)
        logger.info("FTP publisher upload completed")
        return "Successfully uploaded to FTP server"

    def upload_to_ftp(self, server_config: ParseResult, data_to_upload: BytesIO, timeout: float):
        ftp_port = server_config.port or 21
        remote_path = server_config.path + self.file_name
        host_name = server_config.hostname

        if not host_name:
            raise ValueError("Hostname is required for FTP")

        if server_config.scheme != "ftp":
            raise ValueError(f"Schema '{server_config.scheme}' not supported, choose 'ftp'")

        ftp = ftplib.FTP()
        completed = False
        try:
            with self._network_phase("connect"):
                ftp.connect(host=host_name, port=ftp_port, timeout=timeout)
            if server_config.username and server_config.password:
                with self._network_phase("authenticate"):
                    ftp.login(server_config.username, server_config.password)
            with self._network_phase("upload"):
                ftp.storbinary(f"STOR {remote_path}", data_to_upload)
            completed = True
        finally:
            try:
                self._start_close_phase()
                if completed:
                    with publisher_cleanup():
                        ftp.quit()
            finally:
                with publisher_cleanup():
                    ftp.close()
