# Project Summary: Heartbeat Processor Initialization

## 1. Architecture Overview

The Heartbeat Processor utility is designed to manage a set of asynchronous, long-running tasks defined in a centralized configuration file, ensuring system state is periodically checked and updated.

**Core Components:**
1.  **`HEARTBEAT.md` (Data Source):** Located at `$AGENT_ROOT/core/HEARTBEAT.md`. This file stores the current state and configuration of all managed tasks. It will be parsed on startup.
2.  **`HeartbeatProcessor` (Execution Engine):** Located at `$AGENT_ROOT/bin/heartbeat_processor.py`. This script handles the main logic: Read, Parse, Filter (by status/schedule), Execute (using thread pool), and Persist updates.

## 2. Data Flow and State Management

1.  **Initialization:** `HeartbeatProcessor` reads `HEARTBEAT.md`.
2.  **Parsing:** Content is parsed into an in-memory data structure (e.g., a list of task dictionaries).
3.  **Execution Loop:** Tasks marked as 'pending' or 'running' (if timeout exceeded) are submitted to a ThreadPoolExecutor, limited to 2 concurrent threads based on hardware profile.
4.  **State Update:** Upon task completion or timeout, the in-memory structure is updated (e.g., status changes from 'running' to 'success' or 'failed', next_run_time updated).
5.  **Persistence:** The updated structure is serialized back to `HEARTBEAT.md`. Atomic writes are required to prevent corruption.

## 3. Constraints and Dependencies

*   **Concurrency Limit:** Max 2 threads (`MAX_THREADS` from hardware profile).
*   **Dependency:** Relies on the existence and readability of `$AGENT_ROOT/core/HEARTBEAT.md` and the existence of `$AGENT_ROOT/bin/gemini_mas.py` for core configuration context if needed.
*   **File Format (TBD):** Initial assumption is YAML/structured text for readability, requiring robust parsing logic in the processor.