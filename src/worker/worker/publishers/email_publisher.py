import base64
import smtplib
import ssl
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTPException
from typing import Any

from worker.log import logger
from worker.publishers.base_publisher import BasePublisher
from worker.types import Product


class EMAILPublisher(BasePublisher):
    REQUIRED_PARAMETERS = ("SMTP_SERVER_ADDRESS", "EMAIL_SENDER", "EMAIL_RECIPIENT", "EMAIL_SUBJECT")

    def __init__(self):
        super().__init__()
        self.smtp_address: str
        self.smtp_port: int
        self.smtp_tls: str
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

        self.smtp_address = parameters["SMTP_SERVER_ADDRESS"]
        self.smtp_port = parameters.get("SMTP_SERVER_PORT", 25)
        self.smtp_tls = parameters.get("SERVER_TLS", "false")
        self.smtp_username = parameters.get("EMAIL_USERNAME")
        self.smtp_password = parameters.get("EMAIL_PASSWORD")
        self.msg = self.create_message(parameters)

        self.set_file_name(product)
        self.setup_email(rendered_product)

        context = ssl.create_default_context() if self.smtp_tls == "true" else None

        return self.send_with_tls(context) if context else self.send_without_tls()

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

    def smtp_login(self, server):
        try:
            server.login(self.smtp_username, self.smtp_password)
        except (SMTPAuthenticationError, SMTPException, Exception) as e:
            error_message = "SMTP authentication error" if isinstance(e, SMTPAuthenticationError) else "An SMTP error occurred"
            logger.error(f"{error_message}: {str(e)}")
            raise RuntimeError({"error": error_message}) from e

    def send_with_tls(self, context) -> str:
        with SMTP_SSL(self.smtp_address, self.smtp_port, context=context) as server:
            return self.send_mail(server)

    def send_without_tls(self) -> str:
        try:
            server = smtplib.SMTP(self.smtp_address, self.smtp_port)
            return self.send_mail(server)
        except Exception as e:
            logger.error(f"Your SMTP server throws an error: {str(e)}")
            raise RuntimeError("An SMTP error occurred") from e

    def send_mail(self, server) -> str:
        if self.smtp_username and self.smtp_password:
            self.smtp_login(server)
        try:
            server.sendmail(self.msg.get("From"), self.msg.get("To"), self.msg.as_string())
        except SMTPException as e:
            logger.error(f"Your SMTP server throws an error: {str(e)}")
            raise RuntimeError("An SMTP error occurred") from e
        finally:
            server.quit()
        return "Email Publisher: Task Successful"
