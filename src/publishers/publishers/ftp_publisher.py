import datetime
import ftplib
import os
from base64 import b64decode
from urllib.parse import urlsplit
import paramiko

from .base_publisher import BasePublisher
from schema.parameter import Parameter, ParameterType


class FTPPublisher(BasePublisher):
    type = "FTP_PUBLISHER"
    name = "FTP Publisher"
    description = "Publisher for publishing to FTP server"

    parameters = [Parameter(0, "FTP_URL", "FTP URL", "FTP server url", ParameterType.STRING)]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):

        def get_prefix_and_ftp(ftp_server_url):
            url = ftp_server_url.split(' ')
            prefix_ftp = url[0].strip()
            url_ftp = url[1].lstrip()
            return prefix_ftp, url_ftp

        try:
            ftp_url = publisher_input.parameter_values_map['FTP_URL']

            mime_type = publisher_input.mime_type[:]

            filename = ''
            if mime_type[:] == 'application/pdf':
                filename = 'file_' + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + '.pdf'
            elif mime_type[:] == 'text/plain':
                filename = 'file_' + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + '.txt'
            elif mime_type[:] == 'application/json':
                filename = 'file_' + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + '.json'
            elif mime_type[:] == 'text/html':
                filename = 'file_' + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + '.html'

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True)

            f = open(filename, 'wb')
            f.write(bytes_data)
            f.close()

            ftp_prefix = get_prefix_and_ftp(ftp_url)[0]
            ftp_url = get_prefix_and_ftp(ftp_url)[1]

            ftp_data = urlsplit(ftp_url)

            ftp_hostname = ftp_data.scheme + '.' + ftp_data.hostname
            ftp_username = ftp_data.username
            ftp_password = ftp_data.password
            ftp_port = ftp_data.port

            remote_path = ftp_data.path + filename

            if ftp_prefix == 'sftp:':
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ftp_hostname, ftp_port, ftp_username, ftp_password)
                sftp = ssh.open_sftp()
                sftp.put(filename, remote_path)
                sftp.close()
                os.remove(filename)
            else:
                ftp = ftplib.FTP()
                ftp.connect(ftp_hostname, ftp_port)
                ftp.login(ftp_username, ftp_password)
                ftp.storbinary('STOR ' + remote_path, open(filename, 'rb'))
                ftp.quit()
                os.remove(filename)
        except Exception as error:
            BasePublisher.print_exception(self, error)
