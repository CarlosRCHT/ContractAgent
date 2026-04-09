#!/bin/bash
# Azure App Service startup script
# This script is executed by the App Service Linux container

# Set Python path
export PYTHONPATH=/home/site/wwwroot

# Create temp directory
mkdir -p /tmp/redline

# Start the application
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
