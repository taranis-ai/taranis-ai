import base64
import contextlib
import smtplib
import ssl
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTPException
from typing import Any

from models.product import WorkerProduct as Product

from worker.log import logger
from worker.publishers.base_publisher import BasePublisher
from worker.publishers.execution_context import PublisherNetworkTimeout


class EMAILPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.smtp_address: str
        self.smtp_port: int
        self.smtp_tls: bool
        self.smtp_username = None
        self.smtp_password = None

        self.msg: EmailMessage
        self.type = "EMAIL_PUBLISHER"
        self.name = "EMAIL Publisher"
        self.description = "Publisher for publishing by email"

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product) -> str:
        if not rendered_product or not product or not publisher:
            logger.error("No user input provided")
            raise ValueError("No user input provided")

        parameters = self._extract_parameters(publisher)
        timeout = self._network_timeout(parameters)

        self.smtp_address = parameters["SMTP_SERVER_ADDRESS"]
        self.smtp_port = parameters.get("SMTP_SERVER_PORT", 25)
        self.smtp_tls = parameters.get("SERVER_TLS", False)
        self.smtp_username = parameters.get("EMAIL_USERNAME")
        self.smtp_password = parameters.get("EMAIL_PASSWORD")
        self.msg = self.create_message(parameters)

        self.set_file_name(product)
        self.setup_email(rendered_product)

        context = ssl.create_default_context() if self.smtp_tls else None

        return self.send_with_tls(context, timeout) if context else self.send_without_tls(timeout)

    def create_message(self, parameters: dict[str, Any]) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = parameters["EMAIL_SUBJECT"]
        msg["From"] = parameters["EMAIL_SENDER"]
        msg["To"] = parameters["EMAIL_RECIPIENT"]
        return msg

    def setup_simple_email(self, rendered_product):
        self.msg.set_content(rendered_product.data.decode("utf-8"))

    def attach_file(self, rendered_product):
        maintype, subtype = rendered_product.mime_type.split("/")
        logger.debug("EMAIL Publisher: Creating attachment")
        attachment_data = base64.b64decode(rendered_product.data)
        self.msg.add_attachment(attachment_data, maintype=maintype, subtype=subtype, filename=f"{self.file_name}")

    def setup_email(self, rendered_product: Product):
        if rendered_product.mime_type in ["text/plain", "text/html"]:
            self.setup_simple_email(rendered_product)
        else:
            self.attach_file(rendered_product)
            logger.debug("Product attached")

    def smtp_login(self, server, timeout: float):
        try:
            with self._network_phase("authenticate", timeout):
                server.login(self.smtp_username, self.smtp_password)
        except PublisherNetworkTimeout:
            raise
        except Exception as e:
            error_message = "SMTP authentication error" if isinstance(e, SMTPAuthenticationError) else "An SMTP error occurred"
            logger.error(f"{error_message}: exception_type={type(e).__name__}")
            raise RuntimeError({"error": error_message}) from e

    def send_with_tls(self, context, timeout: float) -> str:
        server = None
        completed = False
        try:
            with self._network_phase("connect", timeout):
                server = SMTP_SSL(self.smtp_address, self.smtp_port, context=context, timeout=timeout)
            result = self.send_mail(server, timeout)
            completed = True
            return result
        finally:
            self._close_server(server, graceful=completed)

    def send_without_tls(self, timeout: float) -> str:
        server = None
        completed = False
        try:
            with self._network_phase("connect", timeout):
                server = smtplib.SMTP(self.smtp_address, self.smtp_port, timeout=timeout)
            result = self.send_mail(server, timeout)
            completed = True
            return result
        except PublisherNetworkTimeout:
            raise
        except Exception as e:
            logger.error(f"SMTP publisher operation failed: exception_type={type(e).__name__}")
            raise RuntimeError("An SMTP error occurred") from e
        finally:
            self._close_server(server, graceful=completed)

    def send_mail(self, server, timeout: float) -> str:
        if self.smtp_username and self.smtp_password:
            self.smtp_login(server, timeout)
        try:
            with self._network_phase("send", timeout):
                server.sendmail(self.msg.get("From"), self.msg.get("To"), self.msg.as_string())
        except SMTPException as e:
            logger.error(f"SMTP publisher send failed: exception_type={type(e).__name__}")
            raise RuntimeError("An SMTP error occurred") from e
        return "Email Publisher: Task Successful"

    def _close_server(self, server, *, graceful: bool) -> None:
        if server is None:
            return
        self._start_close_phase()
        if graceful:
            with contextlib.suppress(Exception):
                server.quit()
        with contextlib.suppress(Exception):
            server.close()
