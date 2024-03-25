import base64
import datetime
import smtplib
import ssl
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTPException

from worker.log import logger
from worker.publishers.base_publisher import BasePublisher
from worker.types import Product


class EMAILPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.smtp_address = None
        self.smtp_port = None
        self.smtp_tls = False
        self.smtp_username = None
        self.smtp_password = None
        self.sender = None
        self.recipient = None
        self.mail_subject = None

        self.msg = None
        self.type = "EMAIL_PUBLISHER"
        self.name = "EMAIL Publisher"
        self.description = "Publisher for publishing by email"

    def publish(self, publisher, publisher_input) -> dict:
        self.smtp_address = publisher.get("parameters").get("SMTP_SERVER_ADDRESS")
        if not self.smtp_address:
            logger.error("No SMTP server address provided")
            return {"error": "No SMTP server address provided"}

        self.smtp_port = publisher.get("parameters").get("SMTP_SERVER_PORT", 25)
        self.smtp_tls = publisher.get("parameters").get("SERVER_TLS")
        self.smtp_username = publisher.get("parameters").get("EMAIL_USERNAME")
        self.smtp_password = publisher.get("parameters").get("EMAIL_PASSWORD")
        self.sender = publisher.get("parameters").get("EMAIL_SENDER")
        self.recipient = publisher.get("parameters").get("EMAIL_RECIPIENT")
        self.mail_subject = publisher.get("parameters").get("EMAIL_SUBJECT")

        if publisher_input is None:
            logger.error("No user input provided")
            return {"error": "No user input provided"}

        if rendered_product := self.get_rendered_product(publisher_input):
            self.setup_email(rendered_product)

            context = ssl.create_default_context() if self.smtp_tls else None

            return self.send_with_tls(context) if context else self.send_without_tls()

        logger.warning("Could not get rendered Product")
        return {"error": "Could not get rendered Product"}

    def get_rendered_product(self, publisher_input) -> Product | None:
        product_id = publisher_input.get("id")
        logger.debug(f"EMAIL Publisher: Getting rendered product for product {product_id}")
        return self.core_api.get_product_render(product_id)

    def set_meta_data(self):
        self.msg["Subject"] = self.mail_subject
        self.msg["From"] = self.sender
        self.msg["To"] = self.recipient

    def setup_simple_email(self, rendered_product):
        self.msg = EmailMessage()
        self.set_meta_data()
        self.msg.set_content(rendered_product.data.decode("utf-8"))

    def attach_file(self, rendered_product):
        self.msg = EmailMessage()
        self.set_meta_data()

        file_name = f"product_{datetime.datetime.now().strftime('%d-%m-%Y_%H-%M')}"
        maintype, subtype = rendered_product.mime_type.split("/")
        logger.debug("EMAIL Publisher: Creating attachment")
        attachment_data = base64.b64decode(rendered_product.data)
        self.msg.add_attachment(attachment_data, maintype=maintype, subtype=subtype, filename=f"{file_name}")

    def setup_email(self, rendered_product: Product):
        if rendered_product.mime_type in ["text/plain", "text/html"]:
            self.setup_simple_email(rendered_product)
        else:
            self.attach_file(rendered_product)
            logger.debug("Product attached")

    def smtp_login(self, server) -> dict | None:
        try:
            server.login(self.smtp_username, self.smtp_password)
            return {"message": "Email Publisher: Task Successful"}
        except (SMTPAuthenticationError, SMTPException, Exception) as e:
            error_message = "SMTP authentication error" if isinstance(e, SMTPAuthenticationError) else "An SMTP error occurred"
            logger.error(f"{error_message}: {str(e)}")
            return {"error": error_message}

    def send_with_tls(self, context) -> dict | None:
        try:
            with SMTP_SSL(self.smtp_address, self.smtp_port, context=context) as server:
                return self.send_mail(server)
        except Exception as e:
            logger.error(f"Your SMTP server with TLS context throws an error: {str(e)}")
            return {"error": "An SMTP error occurred"}

    def send_without_tls(self) -> dict | None:
        try:
            server = smtplib.SMTP(self.smtp_address, self.smtp_port)
            return self.send_mail(server)
        except Exception as e:
            logger.error(f"Your SMTP server throws an error: {str(e)}")
            return {"error": "An SMTP error occurred"}

    def send_mail(self, server) -> dict | None:
        # s.set_debuglevel(1)
        if self.smtp_username and self.smtp_password:
            self.smtp_login(server)
        try:
            server.sendmail(self.msg.get("From"), self.msg.get("To"), self.msg.as_string())
        except smtplib.SMTPException as e:
            logger.error(f"Your SMTP server throws an error: {str(e)}")
            return {"error": "An SMTP error occurred"}
        finally:
            server.quit()
        return {"message": "Email Publisher: Task Successful"}


if __name__ == "__main__":
    email_publisher = EMAILPublisher()
    email_publisher.publish(
        # {
        #     "parameters": {
        #         "SMTP_SERVER_ADDRESS": "",
        #         "SMTP_SERVER_PORT": ,
        #         "SERVER_TLS": False,
        #         "EMAIL_USERNAME": "",
        #         "EMAIL_PASSWORD": "",
        #         "EMAIL_SENDER": "sender@email.com",
        #         "EMAIL_RECIPIENT": "",
        #         "EMAIL_SUBJECT": "Test email subject",
        #     },
        {
            "parameters": {
                "SMTP_SERVER_ADDRESS": "localhost",
                "SMTP_SERVER_PORT": 1025,
                "SERVER_TLS": False,
                "EMAIL_USERNAME": "",
                "EMAIL_PASSWORD": "",
                "EMAIL_SENDER": "sender@email.com",
                "EMAIL_RECIPIENT": "taranis@dev.taranis.ai",
                "EMAIL_SUBJECT": "Test email subject",
            },
        },
        {"id": 1, "type": "text_presenter", "type_id": 3, "mime_type": "text/plain", "report_items": [{"title": "test title"}]},
    )
