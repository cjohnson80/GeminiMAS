#!/bin/bash
set -euo pipefail

# Enforce secure default permissions for any new files/directories
umask 077

# 1. Root Validation
if [ -z "${AGENT_ROOT:-}" ]; then
  echo "Error: AGENT_ROOT environment variable is not set." >&2
  exit 1
fi

if [[ "$AGENT_ROOT" != /* ]]; then
  echo "Error: AGENT_ROOT must be an absolute path." >&2
  exit 1
fi

if [ -L "$AGENT_ROOT" ]; then
  echo "Error: AGENT_ROOT cannot be a symlink." >&2
  exit 1
fi

if [ ! -d "$AGENT_ROOT" ]; then
  echo "Error: AGENT_ROOT directory does not exist." >&2
  exit 1
fi

MY_UID=$(id -u)

if [ "$(stat -c "%u" "$AGENT_ROOT")" != "$MY_UID" ]; then
  echo "Error: AGENT_ROOT is not owned by the current user." >&2
  exit 1
fi

# 2. Directory Definitions
CRITICAL_DIRS=("bin" "core" "logs" "workspace" "mailbox")
NON_CRITICAL_DIRS=("memory" "data" "tmp")

# 3. Validation Function
validate_dir() {
  local dir_name="$1"
  local is_critical="$2"
  local dir_path="$AGENT_ROOT/$dir_name"

  if [ -e "$dir_path" ]; then
    # Prevent Symlink Attacks & TOCTOU
    if [ -L "$dir_path" ]; then
      echo "Error: $dir_path is a symlink. Symlinks are strictly prohibited." >&2
      exit 1
    fi
    
    if [ ! -d "$dir_path" ]; then
      echo "Error: $dir_path exists but is not a directory." >&2
      exit 1
    fi
    
    # Validate Ownership
    if [ "$(stat -c "%u" "$dir_path")" != "$MY_UID" ]; then
      echo "Error: $dir_path is not owned by the current user." >&2
      exit 1
    fi
    
    # Validate Strict Permissions (avoiding check-then-chmod TOCTOU)
    local perms
    perms=$(stat -c "%a" "$dir_path")
    if [ "$perms" != "700" ]; then
      echo "Error: $dir_path has insecure permissions ($perms). Expected 700. Fix manually." >&2
      exit 1
    fi
  else
    if [ "$is_critical" = "true" ]; then
      echo "Error: Critical directory missing: $dir_path" >&2
      exit 1
    else
      # Safe Creation: Race-condition free with -m 700 and umask 077
      mkdir -m 700 -p "$dir_path"
    fi
  fi
}

# 4. Execution
for dir in "${CRITICAL_DIRS[@]}"; do
  validate_dir "$dir" "true"
done

for dir in "${NON_CRITICAL_DIRS[@]}"; do
  validate_dir "$dir" "false"
done

echo "Environment validation passed successfully."
