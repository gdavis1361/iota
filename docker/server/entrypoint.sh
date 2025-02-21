#!/bin/bash
set -e

# Validate environment variables
python /app/scripts/validate_env.py

# Wait for services
python /app/scripts/wait_for_services.py

# Apply database migrations
alembic upgrade head

# Start the FastAPI application
exec "$@"
