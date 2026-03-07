#!/bin/bash
# Usage: ./dev_health_check.sh [path_to_project] [port] [timeout_seconds]

PROJECT_PATH=${1:-"."}
PORT=${2:-3000}
TIMEOUT=${3:-60}
URL="http://localhost:$PORT"

# Ensure we can reach the directory
if [ ! -d "$PROJECT_PATH" ]; then
  echo "Error: Directory $PROJECT_PATH does not exist."
  exit 1
fi

cd "$PROJECT_PATH"

echo "Starting npm run dev in $PROJECT_PATH..."
npm run dev > /dev/null 2>&1 &
DEV_PID=$!

# Function to cleanup
cleanup() {
  echo "Terminating dev server (PID: $DEV_PID)..."
  kill $DEV_PID 2>/dev/null
  wait $DEV_PID 2>/dev/null
  echo "Done."
}

trap cleanup EXIT

echo "Waiting for $URL to return 200 OK (timeout: ${TIMEOUT}s)..."
START_TIME=$(date +%s)

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))

  if [ $ELAPSED -gt $TIMEOUT ]; then
    echo "Timeout reached. Server failed to respond with 200 OK within ${TIMEOUT}s."
    exit 1
  fi

  # Check HTTP status code
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
  
  if [ "$STATUS" == "200" ]; then
    echo "Success! Server is up and returned 200 OK."
    exit 0
  fi

  echo "Current status: $STATUS... waiting..."
  sleep 2
done
