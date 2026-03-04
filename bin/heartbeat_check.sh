#!/bin/bash
# Optimization: Prevent redundant heartbeat loops
# Strategy: Check state file before execution

STATE_FILE="/home/chrisj/gemini_agents/workspace/state.lock"

if [ -f "$STATE_FILE" ]; then
    exit 0
fi

touch "$STATE_FILE"
# Core logic execution follows...