#!/bin/bash

# Start the Background Monitoring Worker in the background
echo "Starting CheckMyServer Monitor Worker..."
python backend/main.py &

# Start the Flask API Web Server in the foreground
echo "Starting CheckMyServer API..."
python backend/api.py
