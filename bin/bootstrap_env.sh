#!/bin/bash

set -euo pipefail

# 1. Root Validation
if [ -z "${AGENT_ROOT:-}" ]; then
  echo "[FATAL] AGENT_ROOT environment variable is not set." >&2
  exit 1
fi

if [ ! -d "$AGENT_ROOT" ]; then
  echo "[FATAL] AGENT_ROOT ($AGENT_ROOT) is not a valid directory." >&2
  exit 1
fi

# 2. Strict Verification of Critical Directories
CRITICAL_DIRS=("bin" "core" "logs" "workspace" "mailbox")
for dir in "${CRITICAL_DIRS[@]}"; do
  TARGET="$AGENT_ROOT/$dir"
  if [ ! -d "$TARGET" ]; then
    echo "[FATAL] Critical directory missing: $TARGET" >&2
    exit 1
  fi
done

# 3. Safe Creation of Non-Critical Directories
NON_CRITICAL_DIRS=("memory" "data" "tmp" "skills" "knowledge")
for dir in "${NON_CRITICAL_DIRS[@]}"; do
  TARGET="$AGENT_ROOT/$dir"
  if [ ! -d "$TARGET" ]; then
    mkdir -p "$TARGET"
    echo "[INFO] Created missing non-critical directory: $TARGET"
  fi
  # Enforce strict permissions (700) to prevent unauthorized access
  chmod 700 "$TARGET"
done

echo "[SUCCESS] Environment validation complete. All critical invariants met."
exit 0
