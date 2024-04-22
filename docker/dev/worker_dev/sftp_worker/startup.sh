#!/bin/bash

echo "${SFTP_USER}:${SFTP_PASSWORD}" | chpasswd
chown -R "${SFTP_USER}" /var/www/html

/usr/sbin/sshd -eD &
nginx -g 'daemon off;' &

tail -f /var/log/nginx/access.log /var/log/nginx/error.log
