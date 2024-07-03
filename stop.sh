#!/bin/bash

# Stop Redis server
echo "Stopping Redis server..."
pkill redis-server

# Stop Celery worker
echo "Stopping Celery worker..."
pkill -f 'celery worker'

# Stop Celery beat
echo "Stopping Celery beat..."
pkill -f 'celery beat'

# Stop FastAPI application
echo "Stopping FastAPI application..."
pkill -f 'uvicorn'

echo "All services stopped."