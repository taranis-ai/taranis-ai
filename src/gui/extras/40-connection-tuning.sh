#! /bin/sh

sed -i -e "s/worker_processes.*/worker_processes  ${NGINX_WORKERS};/" -e "s/worker_connections.*/worker_connections  ${NGINX_CONNECTIONS};/" /etc/nginx/nginx.conf
