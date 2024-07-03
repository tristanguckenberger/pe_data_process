#!/bin/bash

# Start Redis server
echo "Starting Redis server..."
redis-server &

# # Start Celery worker
# echo "Starting Celery worker..."
# celery -A main.celery worker --loglevel=info &

# # Start Celery beat
# echo "Starting Celery beat..."
# celery -A main.celery beat --loglevel=info &

# Start FastAPI application
echo "Starting FastAPI application..."
uvicorn main:app --reload &

echo "All services started."