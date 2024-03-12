import datetime
import smtplib
import logging
import requests
from worker.presenters.presenter_tasks import PresenterTask
from worker.log import logger
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gnupg

from worker.publishers.base_publisher import BasePublisher


class EMAILPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.msg = None
        self.type = "EMAIL_PUBLISHER"
        self.name = "EMAIL Publisher"
        self.description = "Publisher for publishing by email"

    def publish(self, publisher_input):
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

        if publisher_input is not None:
            # self.msg.set_content("hello")
            rendered_product = self.get_rendered_product(publisher_input)
            self.send_email(rendered_product)
        else:
            logging.warning("No report items to send")
            raise ValueError("No report items to send")

    def get_rendered_product(self, publisher_input):
        print(f"this is a string {publisher_input.get('report_items')}")
        logger.info(f"EMAIL Publisher: Getting rendered product: {publisher_input.get('report_items')}")
        product_id = publisher_input.get("id")
        print(publisher_input)

        presenter_task = PresenterTask()

        # product, err = presenter_task.get_product(product_id)
        # if err or not product:
        #     return err
        print("get presenter")
        presenter, err = presenter_task.get_presenter(publisher_input)
        if err or not presenter:
            return err
        print("get template")
        type_id: int = int(publisher_input.get("type_id"))
        template, err = presenter_task.get_template(type_id)
        if err or not template:
            return err
        print("generate")
        products_render = presenter.generate(publisher_input, template)
        print("this is the rendered product")
        print(products_render)
        return products_render

    def send_email(self, rendered_product):
        self.msg = MIMEMultipart()
        self.msg["Subject"] = "Subject of the email"
        self.msg["From"] = "test@test.test"
        self.msg["To"] = "john.doe@doemail.com"

        attachment = MIMEText(rendered_product.get('data').decode("utf-8"))
        self.msg.attach(attachment)

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        print("sending email")
        s = smtplib.SMTP("localhost", 1025)
        s.sendmail(self.msg.get("From"), self.msg.get("To"), self.msg.as_string())
        s.quit()

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
        {"id": 1, "type": "text_presenter", "type_id": 3, "mime_type": "text/plain", "report_items": "This is a test email"}
    )
