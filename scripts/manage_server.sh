#!/bin/bash

PORT=8000
EXISTING_PID=$(lsof -ti tcp:$PORT)

if [ -n "$EXISTING_PID" ]; then
    echo "Port $PORT is in use. Terminating process $EXISTING_PID"
    kill -9 $EXISTING_PID
fi

# Start uvicorn with reload
cd "$(dirname "$0")/.."
uvicorn app.main:app --reload --port $PORT
