#!/bin/bash
# verify_readiness.sh - Comprehensive check for project health

PROJECT_PATH=${1:-"."}
PORT=${2:-3000}

echo "--- Starting Readiness Verification for $PROJECT_PATH ---"

if [ ! -d "$PROJECT_PATH" ]; then
  echo "Error: Directory $PROJECT_PATH not found."
  exit 1
fi

cd "$PROJECT_PATH"

# 1. Check for package.json
if [ ! -f "package.json" ]; then
  echo "Error: No package.json found in $PROJECT_PATH"
  exit 1
fi

# 2. Run Linting
echo "[1/3] Running Lint..."
if npm run lint > /dev/null 2>&1; then
  echo "✅ Lint passed."
else
  echo "❌ Lint failed."
  exit 1
fi

# 3. Run Type Check (if typescript project)
if [ -f "tsconfig.json" ]; then
  echo "[2/3] Running Type Check..."
  if npx tsc --noEmit > /dev/null 2>&1; then
    echo "✅ Type check passed."
  else
    echo "❌ Type check failed."
    exit 1
  fi
else
  echo "[2/3] Skipping Type Check (no tsconfig.json found)."
fi

# 4. Run Health Check
echo "[3/3] Running Health Check (Dev Server)..."
HEALTH_CHECK_SCRIPT="$(dirname "$0")/dev_health_check.sh"

if [ -f "$HEALTH_CHECK_SCRIPT" ]; then
  bash "$HEALTH_CHECK_SCRIPT" . "$PORT" 60
  if [ $? -eq 0 ]; then
    echo "✅ Health check passed."
  else
    echo "❌ Health check failed."
    exit 1
  fi
else
  echo "❌ Error: dev_health_check.sh not found in bin/"
  exit 1
fi

echo "--- Verification Complete: PROJECT IS READY ---"
