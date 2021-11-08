import json
import os
import urllib.request
from base64 import b64decode

from managers.ftp_manager import create_sftp_client
from managers.email_manager import email_sender

filename = 'file.pdf'


def get_presenters_data():

    with urllib.request.urlopen("http://127.0.0.1:5002/api/presenters/data") as url:
        dist = json.loads(url.read().decode())
        b64 = dist['file']['data']
        bytes_data = b64decode(b64, validate=True)

    f = open('file.pdf', 'wb')
    f.write(bytes_data)
    f.close()


def send_email():

    get_presenters_data()

    email_sender()

    os.remove(filename)


def send_to_ftp():

    get_presenters_data()

    remote_path = os.getenv('FTP_DIR') + filename

    ftp_url = os.getenv('FTP_URL')
    ftp_username = os.getenv('FTP_USERNAME')
    ftp_password = os.getenv('FTP_PASSWORD')
    ftp_port = os.getenv('FTP_PORT')

    sftp_client = create_sftp_client(ftp_url, ftp_port, ftp_username, ftp_password)

    sftp_client.put(filename, remote_path)

    sftp_client.close()
