import datetime
import smtplib
import logging
from email.message import EmailMessage
from worker.log import logger
import base64

from worker.publishers.base_publisher import BasePublisher
from worker.types import Product


class EMAILPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.smtp_server_address = None
        self.smtp_server_port = None
        self.smtp_server_tls = None
        self.smtp_server_password = None
        self.smtp_server_username = None
        self.smtp_server_sender = None
        self.smtp_server_recipient = None
        self.smtp_server_subject = None

        self.msg = None
        self.type = "EMAIL_PUBLISHER"
        self.name = "EMAIL Publisher"
        self.description = "Publisher for publishing by email"

    def publish(self, publisher, publisher_input) -> dict[str, str] | None:
        print(publisher)
        self.smtp_server_address = publisher.get("parameters").get("SMTP_SERVER_ADDRESS", None)
        if self.smtp_server_address is None:
            logger.error("No SMTP server address provided")
            return {"error": "No SMTP server address provided"}

        self.smtp_server_port = publisher.get("parameters").get("SMTP_SERVER_PORT", None)
        if self.smtp_server_port is None:
            logger.error("No SMTP server port provided")
            return {"error": "No SMTP server port provided"}

        if smtp_server_tls := publisher.get("parameters").get("SERVER_TLS", None):
            self.smtp_server_tls = smtp_server_tls

        if smtp_server_username := publisher.get("parameters").get("EMAIL_USERNAME"):
            self.smtp_server_username = smtp_server_username

        if smtp_server_password := publisher.get("parameters").get("EMAIL_PASSWORD"):
            self.smtp_server_password = smtp_server_password

        if smtp_server_sender := publisher.get("parameters").get("EMAIL_SENDER"):
            self.smtp_server_sender = smtp_server_sender

        if smtp_server_recipient := publisher.get("parameters").get("EMAIL_RECIPIENT"):
            self.smtp_server_recipient = smtp_server_recipient

        if smtp_server_subject := publisher.get("parameters").get("EMAIL_SUBJECT"):
            self.smtp_server_subject = smtp_server_subject

        if publisher_input is None:
            logger.error("No user input provided")
            return {"error": "No user input provided"}

        if rendered_product := self.get_rendered_product(publisher_input):
            return self.send_email(rendered_product)
        logging.warning("Could not get rendered Product")
        return {"error": "Could not get rendered Product"}

    def get_rendered_product(self, publisher_input) -> Product | None:
        product_id = publisher_input.get("id")
        logger.debug(f"EMAIL Publisher: Getting rendered product for product {product_id}")
        return self.core_api.get_product_render(product_id)

    def set_meta_data(self):
        self.msg["Subject"] = self.smtp_server_subject
        self.msg["From"] = self.smtp_server_sender
        self.msg["To"] = self.smtp_server_recipient

    def set_simple_email(self, rendered_product):
        self.msg = EmailMessage()
        self.set_meta_data()
        self.msg.set_content(rendered_product.data.decode("utf-8"))

    def attach_file(self, rendered_product):
        self.msg = EmailMessage()
        self.set_meta_data()

        file_name = f"product_{datetime.datetime.now().strftime('%d-%m-%Y_%H-%M')}"
        maintype, subtype = rendered_product.mime_type.split("/")
        logger.info("EMAIL Publisher: Creating attachment")
        attachment_data = base64.b64decode(rendered_product.data)
        self.msg.add_attachment(attachment_data, maintype=maintype, subtype=subtype, filename=f"{file_name}")

    def send_email(self, rendered_product: Product):
        if rendered_product.mime_type in ["text/plain", "text/html"]:
            # if rendered_product.mime_type in [""]:
            self.set_simple_email(rendered_product)
        else:
            self.attach_file(rendered_product)
            logger.info("Product attached")

        logger.debug("EMAIL Publisher: Initiate connection to the SMTP sever.")

        try:
            s = smtplib.SMTP(self.smtp_server_address, self.smtp_server_port)
            s.set_debuglevel(1)
            if response := s.sendmail(self.msg.get("From"), self.msg.get("To"), self.msg.as_string()):
                logger.warning(f"EMAIL Publisher: Response from SMTP server: {response}")
                return {"error": f"Your SMTP server throws an error: {response}"}
            s.quit()
        except Exception as e:
            logging.error(f"Your SMTP server throws an error: {str(e)}")
            return {"error": f"Your SMTP server throws an error: {str(e)}"}

        logger.info("EMAIL Publisher: Email sent")
        return {"message": "Email sent successfully"}


if __name__ == "__main__":
    email_publisher = EMAILPublisher()
    email_publisher.publish(
        {
            "parameters": {
                "SMTP_SERVER_ADDRESS": "localhost",
                "SMTP_SERVER_PORT": 1025,
                "SERVER_TLS": True,
                "EMAIL_USERNAME": "admin",
                "EMAIL_PASSWORD": "admin",
                "EMAIL_SENDER": "sender@email.com",
                "EMAIL_RECIPIENT": "recipient@email.com",
                "EMAIL_SUBJECT": "Test email subject",
            },
        },
        {"id": 1, "type": "text_presenter", "type_id": 3, "mime_type": "text/pdf", "report_items": [{"title": "test title"}]},
    )
