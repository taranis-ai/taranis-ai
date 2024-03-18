import datetime
import smtplib
import logging
from email.message import EmailMessage
from email.mime.application import MIMEApplication
import requests
from worker.log import logger
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gnupg
import base64

from worker.publishers.base_publisher import BasePublisher
from worker.types import Product


class EMAILPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.msg = None
        self.type = "EMAIL_PUBLISHER"
        self.name = "EMAIL Publisher"
        self.description = "Publisher for publishing by email"

    def publish(self, publisher_input) -> dict[str, str] | None:
        print(publisher_input)
        # smtp_server = publisher_input.parameter_values_map["SMTP_SERVER"]
        # smtp_server_port = publisher_input.parameter_values_map["SMTP_SERVER_PORT"]
        # email_user = publisher_input.parameter_values_map["EMAIL_USERNAME"]
        # email_password = publisher_input.parameter_values_map["EMAIL_PASSWORD"]
        # email_recipients = publisher_input.parameter_values_map["EMAIL_RECIPIENT"]
        # email_subject = publisher_input.parameter_values_map["EMAIL_SUBJECT"]
        # email_message = publisher_input.parameter_values_map["EMAIL_MESSAGE"]
        # email_encryption = publisher_input.parameter_values_map["EMAIL_ENCRYPTION"]

        # file = "file_" + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + ".pdf"

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
        self.msg["Subject"] = "Subject of the email"
        self.msg["From"] = "test@test.test"
        self.msg["To"] = "john.doe@doemail.com"

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

        # self.msg = MIMEMultipart("alternative")
        # self.msg["Subject"] = "Subject of the email"
        # self.msg["From"] = "test@test.test"
        # self.msg["To"] = "john.doe@doemail.com"
        #
        # file_name = f"file_{datetime.datetime.now().strftime('%d-%m-%Y_%H:%M')}"
        # file_extension = rendered_product[1].split("/")[-1]
        # attachment = MIMEApplication(rendered_product[0], _subtype=file_extension)
        # logger.info(f"EMAIL Publisher: Attaching file {rendered_product[0]}")
        # attachment.add_header("Content-Disposition", "attachment", filename=f"{file_name}.{file_extension}")
        # self.msg.attach(attachment)
        # print(attachment)

    def send_email(self, rendered_product: Product):
        if rendered_product.mime_type in ["text/plain", "text/html"]:
            # if rendered_product.mime_type in [""]:
            self.set_simple_email(rendered_product)
        else:
            self.attach_file(rendered_product)
            logger.info("Product attached")

        logger.debug("EMAIL Publisher: Initiate connection to the SMTP sever.")

        try:
            s = smtplib.SMTP("localhost", 1025)
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


############################################################################################################


# def get_attachment(file_name):
#     msg_attachment = Message()
#     msg_attachment.add_header(_name="Content-Type", _value="application/pdf", name=file_name)
#     msg_attachment.add_header(_name="Content-Transfer-Encoding", _value="base64")
#     msg_attachment.add_header(_name="Content-Disposition", _value="attachment", filename=file_name)
#     msg_attachment.set_payload(data)
#     return msg_attachment
#
# def get_body(message):
#     msg_body = Message()
#     msg_body.add_header(_name="Content-Type", _value="text/plain", charset="utf-8")
#     msg_body.add_header(_name="Content-Transfer-Encoding", _value="quoted-printable")
#     msg_body.set_payload(message + 2 * "\n")
#     return msg_body

# def get_encrypted_email_string(email_address_recipient, file_name, message):
#     def get_gpg_cipher_text(string, recipient_email_address):
#         gpg = gnupg.GPG()
#         encrypted_str = str(gpg.encrypt(string, recipient_email_address))
#         return encrypted_str
#
#     msg = Message()
#     msg.add_header(_name="Content-Type", _value="multipart/mixed")
#     msg["From"] = email_user
#     msg["To"] = email_address_recipient
#     msg["Subject"] = email_subject
#
#     msg_text = Message()
#     msg_text.add_header(_name="Content-Type", _value="multipart/mixed")
#     msg_text.add_header(_name="Content-Language", _value="en-US")
#
#     msg_body = get_body(message)
#     msg_attachment = get_attachment(file_name)
#
#     msg_text.attach(msg_body)
#     msg_text.attach(msg_attachment)
#     msg.attach(msg_text)
#
#     pgp_msg = MIMEBase(_maintype="multipart", _subtype="encrypted", protocol="application/pgp-encrypted")
#     pgp_msg["From"] = email_user
#     pgp_msg["To"] = email_address_recipient
#     pgp_msg["Subject"] = email_subject
#
#     pgp_msg_part1 = Message()
#     pgp_msg_part1.add_header(_name="Content-Type", _value="application/pgp-encrypted")
#     pgp_msg_part1.add_header(_name="Content-Description", _value="PGP/MIME version identification")
#     pgp_msg_part1.set_payload("Version: 2" + "\n")
#
#     pgp_msg_part2 = Message()
#     pgp_msg_part2.add_header(_name="Content-Type", _value="application/octet-stream", name="encrypted.asc")
#     pgp_msg_part2.add_header(_name="Content-Description", _value="OpenPGP encrypted message")
#     pgp_msg_part2.add_header(_name="Content-Disposition", _value="inline", filename="encrypted.asc")
#     pgp_msg_part2.set_payload(get_gpg_cipher_text(msg.as_string(), email_address_recipient))
#
#     pgp_msg.attach(pgp_msg_part1)
#     pgp_msg.attach(pgp_msg_part2)
#
#     return pgp_msg.as_string()
#
# try:
#     server = smtplib.SMTP(smtp_server, smtp_server_port)
#     server.starttls()
#     server.login(email_user, email_password)
#
#     if publisher_input.recipients is not None:
#         recipients = publisher_input.recipients
#     else:
#         recipients = email_recipients.split(",")
#
#     if email_encryption.lower() == "yes":
#         for recipient in recipients:
#             email_msg = email_message
#             email_msg = get_encrypted_email_string(recipient, file, email_msg)
#             server.sendmail(email_user, recipient, email_msg)
#     else:
#         email_msg = MIMEMultipart()
#         email_msg["From"] = email_user
#         email_msg["To"] = email_recipients
#
#         if publisher_input.message_title is not None:
#             email_msg["Subject"] = publisher_input.message_title
#         else:
#             email_msg["Subject"] = email_subject
#
#         if publisher_input.message_body is not None:
#             body = publisher_input.message_body
#         else:
#             body = email_message
#
#         email_msg.attach(MIMEText(body + 2 * "\n", "plain"))
#
#         if data is not None:
#             attachment = get_attachment(file)
#             email_msg.attach(attachment)
#
#         text = email_msg.as_string()
#
#         server.sendmail(email_user, recipients, text)
#
#     server.quit()

# except Exception as error:
#     BasePublisher.print_exception(self, error)


if __name__ == "__main__":
    email_publisher = EMAILPublisher()
    email_publisher.publish(
        {"id": 1, "type": "text_presenter", "type_id": 3, "mime_type": "text/pdf", "report_items": [{"title": "test title"}]}
    )
