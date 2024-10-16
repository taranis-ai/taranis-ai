#!/bin/bash

rm -f /usr/share/nginx/html/assets/*.gz
gzip -k -9 /usr/share/nginx/html/assets/*
