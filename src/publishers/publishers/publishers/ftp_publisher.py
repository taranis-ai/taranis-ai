import datetime
import ftplib
import os
from base64 import b64decode
from urllib.parse import urlsplit
import paramiko

from .base_publisher import BasePublisher


class FTPPublisher(BasePublisher):
    type = "FTP_PUBLISHER"
    name = "FTP Publisher"
    description = "Publisher for publishing to FTP server"

    def publish(self, publisher_input):
        try:
            ftp_url = publisher_input.parameter_values_map["FTP_URL"]

            mime_type = publisher_input.mime_type[:]

            filename = ""
            if mime_type[:] == "application/pdf":
                filename = "file_" + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + ".pdf"
            elif mime_type[:] == "text/plain":
                filename = "file_" + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + ".txt"
            elif mime_type[:] == "application/json":
                filename = "file_" + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + ".json"
            elif mime_type[:] == "text/html":
                filename = "file_" + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + ".html"

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True)

            with open(filename, "wb") as f:
                f.write(bytes_data)
            ftp_data = urlsplit(ftp_url)

            ftp_hostname = ftp_data.hostname
            ftp_username = ftp_data.username
            ftp_password = ftp_data.password

            remote_path = ftp_data.path + filename

            if ftp_data.scheme == "sftp":
                ssh_port = ftp_data.port or 22
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=ftp_hostname, port=ssh_port, username=ftp_username, password=ftp_password)
                sftp = ssh.open_sftp()
                sftp.put(filename, remote_path)
                sftp.close()
            elif ftp_data.scheme == "ftp":
                ftp_port = ftp_data.port or 21
                ftp = ftplib.FTP()
                ftp.connect(host=ftp_hostname, port=ftp_port)
                ftp.login(ftp_username, ftp_password)
                ftp.storbinary(f"STOR {remote_path}", open(filename, "rb"))
                ftp.quit()
            else:
                raise Exception(f"Schema '{ftp_data.scheme}' not supported, choose 'ftp' or 'sftp'")
        except Exception as error:
            BasePublisher.print_exception(self, error)
        finally:
            os.remove(filename)
