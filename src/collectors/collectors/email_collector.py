import datetime
import hashlib
import uuid
import imaplib
import poplib
from email import policy
import email.header
import email.utils
import socket

from .base_collector import BaseCollector
from schema.news_item import NewsItemData, NewsItemAttribute
from schema.parameter import Parameter, ParameterType


class EmailCollector(BaseCollector):
    type = "EMAIL_COLLECTOR"
    name = "EMAIL Collector"
    description = "Collector for gathering data from emails"

    parameters = [
        Parameter(0, "EMAIL_SERVER_TYPE", "Email server type", "Server type parameter means IMAP or POP3 email server",
                  ParameterType.STRING),
        Parameter(0, "EMAIL_SERVER_HOSTNAME", "Email server hostname", "Hostname of email server",
                  ParameterType.STRING),
        Parameter(0, "EMAIL_SERVER_PORT", "Email server port", "Port of email server",
                  ParameterType.NUMBER),
        Parameter(0, "EMAIL_USERNAME", "Username", "Username of email account", ParameterType.STRING),
        Parameter(0, "EMAIL_PASSWORD", "Password", "Password of email account", ParameterType.STRING)
    ]

    parameters.extend(BaseCollector.parameters)

    def collect(self, source):

        news_items = []

        email_server_type = source.parameter_values['EMAIL_SERVER_TYPE']
        email_server_hostname = source.parameter_values['EMAIL_SERVER_HOSTNAME']
        email_server_port = source.parameter_values['EMAIL_SERVER_PORT']
        email_username = source.parameter_values['EMAIL_USERNAME']
        email_password = source.parameter_values['EMAIL_PASSWORD']
        proxy_server = source.parameter_values['PROXY_SERVER']

        def proxy_tunnel():
            server = email_server_type.lower() + '.' + email_server_hostname.lower()
            port = email_server_port

            server_proxy = proxy_server.rsplit(':', 1)[0]
            server_proxy_port = proxy_server.rsplit(':', 1)[-1]

            proxy = (str(server_proxy), int(server_proxy_port))
            con = f'CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n'

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(proxy)
            s.send(str.encode(con))
            s.recv(4096)

        def get_data():
            review = ''
            content = ''
            url = ''
            link = ''
            key = ''
            value = ''

            date_tuple = email.utils.parsedate_tz(email_message['Date'])
            local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            published = f'{str(local_date.strftime("%a, %d %b %Y %H:%M:%S"))}'

            author = str(email.header.make_header(email.header.decode_header(email_message['From'])))
            title = str(email.header.make_header(email.header.decode_header(email_message['Subject'])))
            message_id = str(email.header.make_header(email.header.decode_header(email_message['Message-ID'])))

            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    content = part.get_payload(decode=True)
                    review = content[:500].decode('utf-8')
                    content = content.decode('utf-8')

                for_hash = author + title + message_id

                news_item = NewsItemData(uuid.uuid4(), hashlib.sha256(for_hash.encode()).hexdigest(), title,
                                         review, url, link, published, author, datetime.datetime.now(), content,
                                         source.id, attributes)

                if part.get_content_maintype() == 'multipart':
                    pass
                if part.get('Content-Disposition') is None:
                    pass

                file_name = part.get_filename()

                if file_name:

                    binary_mime_type = part.get_content_type()
                    binary_value = part.get_payload()

                    news_attribute = NewsItemAttribute(uuid.uuid4(), key, value, binary_mime_type, binary_value)
                    news_item.attributes.append(news_attribute)

                news_items.append(news_item)

        if email_server_type.upper() == 'IMAP':
            try:
                if proxy_server:
                    proxy_tunnel()

                connection = imaplib.IMAP4_SSL(email_server_type.lower() + '.' + email_server_hostname.lower(),
                                               email_server_port)
                connection.login(email_username, email_password)
                connection.select('inbox')

                result, data = connection.uid('search', None, 'UNSEEN')
                i = len(data[0].split())

                for x in range(i):
                    attributes = []
                    latest_email_uid = data[0].split()[x]
                    result, email_data = connection.uid('fetch', latest_email_uid, '(RFC822)')
                    raw_email = email_data[0][1]
                    raw_email_string = raw_email.decode('utf-8')
                    email_message = email.message_from_string(raw_email_string, policy=policy.default)

                    get_data()

                connection.close()
                connection.logout()
            except Exception as error:
                BaseCollector.print_exception(source, error)
        else:
            try:
                if proxy_server:
                    proxy_tunnel()

                connection = poplib.POP3_SSL(email_server_type.lower() + '.' + email_server_hostname.lower(),
                                             email_server_port)
                connection.user(email_username)
                connection.pass_(email_password)

                num_messages = len(connection.list()[1])

                for i in range(num_messages):
                    attributes = []

                    raw_email = b"\n".join(connection.retr(i + 1)[1])
                    email_message = email.message_from_bytes(raw_email)

                    get_data()

                connection.quit()
            except Exception as error:
                BaseCollector.print_exception(source, error)

        BaseCollector.publish(news_items, source)
