import datetime
import smtplib
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gnupg

from publishers.base_publisher import BasePublisher
from taranisng.schema.parameter import Parameter, ParameterType


class EMAILPublisher(BasePublisher):
    type = "EMAIL_PUBLISHER"
    name = "EMAIL Publisher"
    description = "Publisher for publishing by email"

    parameters = [
        Parameter(0, "SMTP_SERVER", "SMTP server", "SMTP server for sending emails", ParameterType.STRING),
        Parameter(0, "SMTP_SERVER_PORT", "SMTP server port", "SMTP server port for sending emails",
                  ParameterType.STRING),
        Parameter(0, "EMAIL_USERNAME", "Email username", "Username for email account", ParameterType.STRING),
        Parameter(0, "EMAIL_PASSWORD", "Email password", "Password for email account", ParameterType.STRING),
        Parameter(0, "EMAIL_RECIPIENT", "Email recipient", "Email address of recipient", ParameterType.STRING),
        Parameter(0, "EMAIL_SUBJECT", "Email subject", "Text of email subject", ParameterType.STRING),
        Parameter(0, "EMAIL_MESSAGE", "Email message", "Text of email message", ParameterType.STRING),
        Parameter(0, "EMAIL_ENCRYPTION", "Do you want use email encrypt (yes/no)", "Turn ON/OFF email encryption",
                  ParameterType.STRING)
    ]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):

        smtp_server = publisher_input.parameter_values_map['SMTP_SERVER']
        smtp_server_port = publisher_input.parameter_values_map['SMTP_SERVER_PORT']
        email_user = publisher_input.parameter_values_map['EMAIL_USERNAME']
        email_password = publisher_input.parameter_values_map['EMAIL_PASSWORD']
        email_recipients = publisher_input.parameter_values_map['EMAIL_RECIPIENT']
        email_subject = publisher_input.parameter_values_map['EMAIL_SUBJECT']
        email_message = publisher_input.parameter_values_map['EMAIL_MESSAGE']
        email_encryption = publisher_input.parameter_values_map['EMAIL_ENCRYPTION']

        file = 'file_' + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + '.pdf'

        if publisher_input.data is not None:
            data = publisher_input.data[:]
        else:
            data = None

        def get_attachment(file_name):
            msg_attachment = Message()
            msg_attachment.add_header(_name="Content-Type", _value='application/pdf', name=file_name)
            msg_attachment.add_header(_name="Content-Transfer-Encoding", _value="base64")
            msg_attachment.add_header(_name="Content-Disposition", _value="attachment", filename=file_name)
            msg_attachment.set_payload(data)
            return msg_attachment

        def get_body(message):
            msg_body = Message()
            msg_body.add_header(_name="Content-Type", _value="text/plain", charset="utf-8")
            msg_body.add_header(_name="Content-Transfer-Encoding", _value="quoted-printable")
            msg_body.set_payload(message + 2 * "\n")
            return msg_body

        def get_encrypted_email_string(email_address_recipient, file_name, message):
            def get_gpg_cipher_text(string, recipient_email_address):
                gpg = gnupg.GPG()
                encrypted_str = str(gpg.encrypt(string, recipient_email_address))
                return encrypted_str

            msg = Message()
            msg.add_header(_name="Content-Type", _value="multipart/mixed")
            msg["From"] = email_user
            msg["To"] = email_address_recipient
            msg['Subject'] = email_subject

            msg_text = Message()
            msg_text.add_header(_name="Content-Type", _value="multipart/mixed")
            msg_text.add_header(_name="Content-Language", _value="en-US")

            msg_body = get_body(message)
            msg_attachment = get_attachment(file_name)

            msg_text.attach(msg_body)
            msg_text.attach(msg_attachment)
            msg.attach(msg_text)

            pgp_msg = MIMEBase(_maintype="multipart", _subtype="encrypted", protocol="application/pgp-encrypted")
            pgp_msg["From"] = email_user
            pgp_msg["To"] = email_address_recipient
            pgp_msg['Subject'] = email_subject

            pgp_msg_part1 = Message()
            pgp_msg_part1.add_header(_name="Content-Type", _value="application/pgp-encrypted")
            pgp_msg_part1.add_header(_name="Content-Description", _value="PGP/MIME version identification")
            pgp_msg_part1.set_payload("Version: 2" + "\n")

            pgp_msg_part2 = Message()
            pgp_msg_part2.add_header(_name="Content-Type", _value="application/octet-stream", name="encrypted.asc")
            pgp_msg_part2.add_header(_name="Content-Description", _value="OpenPGP encrypted message")
            pgp_msg_part2.add_header(_name="Content-Disposition", _value="inline", filename="encrypted.asc")
            pgp_msg_part2.set_payload(get_gpg_cipher_text(msg.as_string(), email_address_recipient))

            pgp_msg.attach(pgp_msg_part1)
            pgp_msg.attach(pgp_msg_part2)

            return pgp_msg.as_string()

        try:

            server = smtplib.SMTP(smtp_server, smtp_server_port)
            server.starttls()
            server.login(email_user, email_password)

            if publisher_input.recipients is not None:
                recipients = publisher_input.recipients
            else:
                recipients = email_recipients.split(',')

            if email_encryption.lower() == 'yes':
                for recipient in recipients:
                    email_msg = email_message
                    email_msg = get_encrypted_email_string(recipient, file, email_msg)
                    server.sendmail(email_user, recipient, email_msg)
            else:
                email_msg = MIMEMultipart()
                email_msg['From'] = email_user
                email_msg['To'] = email_recipients

                if publisher_input.message_title is not None:
                    email_msg['Subject'] = publisher_input.message_title
                else:
                    email_msg['Subject'] = email_subject

                if publisher_input.message_body is not None:
                    body = publisher_input.message_body
                else:
                    body = email_message

                email_msg.attach(MIMEText(body + 2 * "\n", 'plain'))

                if data is not None:
                    attachment = get_attachment(file)
                    email_msg.attach(attachment)

                text = email_msg.as_string()

                server.sendmail(email_user, recipients, text)

            server.quit()

        except Exception as error:
            BasePublisher.print_exception(self, error)
