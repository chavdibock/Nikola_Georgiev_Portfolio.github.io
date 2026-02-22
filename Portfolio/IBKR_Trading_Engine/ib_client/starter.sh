#!/bin/bash

echo "Listing files in /app directory:"

sh bin/run.sh root/conf.yaml &

sleep 5

echo "Starting Authentication..."
./venv/bin/python -u main.py