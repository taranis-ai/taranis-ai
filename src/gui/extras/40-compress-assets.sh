#!/bin/bash

rm -f /usr/share/nginx/html/taranis/assets/*.gz
gzip -k -9 /usr/share/nginx/html/taranis/assets/*
