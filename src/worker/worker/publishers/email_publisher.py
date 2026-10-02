import base64
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from models.product import WorkerProduct as Product
from rq.timeouts import JobTimeoutException

from worker.log import logger
from worker.publishers.base_publisher import BasePublisher
from worker.publishers.network import PublisherNetworkTimeout, effective_network_timeout, is_network_timeout


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
        timeout = effective_network_timeout(parameters)

        self.smtp_address = parameters["SMTP_SERVER_ADDRESS"]
        self.smtp_port = parameters.get("SMTP_SERVER_PORT", 25)
        self.smtp_tls = parameters.get("SERVER_TLS", False)
        self.smtp_username = parameters.get("EMAIL_USERNAME")
        self.smtp_password = parameters.get("EMAIL_PASSWORD")
        self.msg = self.create_message(parameters)

        self.set_file_name(product)
        self.setup_email(rendered_product)

        context = ssl.create_default_context() if self.smtp_tls else None

        return self.send_mail(context, timeout)

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

    def send_mail(self, context: ssl.SSLContext | None, timeout: float) -> str:
        sender = self.msg.get("From")
        recipient = self.msg.get("To")
        if sender is None or recipient is None:
            raise ValueError("Email sender and recipient are required")
        server = None
        completed = False
        operation = "connect"
        try:
            logger.info("Email publisher connecting")
            if context is not None:
                server = smtplib.SMTP_SSL(self.smtp_address, self.smtp_port, context=context, timeout=timeout)
            else:
                server = smtplib.SMTP(self.smtp_address, self.smtp_port, timeout=timeout)
            if self.smtp_username and self.smtp_password:
                operation = "authenticate"
                logger.info("Email publisher authenticating")
                server.login(self.smtp_username, self.smtp_password)
            operation = "send"
            logger.info("Email publisher sending")
            server.sendmail(sender, recipient, self.msg.as_string())
            completed = True
        except JobTimeoutException:
            raise
        except Exception as exc:
            if is_network_timeout(exc):
                raise PublisherNetworkTimeout(self.type, operation) from exc
            logger.error(f"Email publisher failed: operation={operation} exception_type={type(exc).__name__}")
            raise RuntimeError("An SMTP error occurred") from exc
        finally:
            self._close_server(server, graceful=completed)
        return "Email Publisher: Task Successful"

    def _close_server(self, server, *, graceful: bool) -> None:
        if server is None:
            return
        try:
            logger.info("Email publisher closing connection")
            if graceful:
                try:
                    server.quit()
                except JobTimeoutException:
                    raise
                except Exception as exc:
                    logger.warning(f"Email publisher shutdown failed: exception_type={type(exc).__name__}")
        finally:
            try:
                server.close()
            except JobTimeoutException:
                raise
            except Exception as exc:
                logger.warning(f"Email publisher close failed: exception_type={type(exc).__name__}")
