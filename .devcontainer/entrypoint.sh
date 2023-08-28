#!/bin/bash

sudo service postgresql start
sudo service rabbitmq-server start
sudo service nginx start

$@
