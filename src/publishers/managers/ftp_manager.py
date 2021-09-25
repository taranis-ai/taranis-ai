import paramiko


def create_sftp_client(host, port, username, password):

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, username, password)
        sftp = ssh.open_sftp()
        return sftp
    except paramiko.AuthenticationException as e:
        raise e
