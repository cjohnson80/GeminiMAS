# Project Summary: HEARTBEAT Task Processing

This project outlines the architecture for an autonomous agent loop designed to parse, execute, and update tasks defined in `/home/chrisj/gemini_agents/core/HEARTBEAT.md`, while strictly adhering to the hardware constraint of 2 maximum execution threads.

## 1. Directory Structure
- **Workspace Root**: `/home/chrisj/gemini_agents/workspace/20260305_090214/` (Current working context).
- **Core Source**: `/home/chrisj/gemini_agents/core/` (Location of `HEARTBEAT.md`).

## 2. Data Flow and Parsing Strategy (The 'Read' Phase)
1.  **Input Source**: The system reads the content of `/home/chrisj/gemini_agents/core/HEARTBEAT.md` using the `read_file` tool or an internal file reader.
2.  **Task Extraction**: The content must be parsed into a standardized JSON or YAML structure representing discrete tasks. This parsing logic must be robust enough to handle sequential, dependency-aware, or parallel task definitions, though parallelism will be constrained.
3.  **State Management**: A mechanism (e.g., an internal state object or a temporary file) will track the status (Pending, In Progress, Completed, Failed) of each task extracted from the heartbeat.

## 3. Execution Strategy (The 'Execute' Phase)
1.  **Constraint Adherence**: The primary constraint is the hardware limitation of **MAX_THREADS: 2** (derived from `[VERIFIED_HARDWARE_REPORT]`).
2.  **Execution Manager**: A dedicated module, likely within `$AGENT_ROOT/bin/gemini_mas.py`, will manage the execution queue.
3.  **Thread Allocation**: The execution manager will maintain a pool of up to 2 active threads/processes for task execution. If a task requires external tooling (e.g., `run_shell`), it will be submitted to this limited thread pool.
4.  **I/O Bound vs. CPU Bound**: Since I/O operations (like `web_search` or `run_shell`) are often blocking, they must be managed carefully within the thread pool to prevent one blocking call from stalling the entire system.

## 4. Update and Iteration Strategy (The 'Update' Phase)
1.  **Result Capture**: Upon task completion (success or failure), the execution manager records the output, status code, and any generated artifacts.
2.  **HEARTBEAT Update**: The system will generate a new version of the task list, reflecting the updated statuses and any new instructions generated during execution.
3.  **Commit Cycle**: To maintain traceability (per Evolution Rule), all changes to the codebase or state artifacts resulting from task execution must be staged and committed using `run_shell` commands against the current branch, ensuring the repository state reflects the completed work before attempting the next iteration of the HEARTBEAT loop.

## 5. Dependency Mapping
- **Input**: `/home/chrisj/gemini_agents/core/HEARTBEAT.md`
- **Execution Core**: `$AGENT_ROOT/bin/gemini_mas.py` (responsible for loop control and thread management).
- **I/O Interface**: `run_shell`, `web_search`, `read_file`, `write_file` tools.
- **Output**: Updated state/code artifacts and eventual commitment back to the repository structure.

This plan prioritizes thread safety and strict adherence to the defined hardware limits while establishing a clear data pipeline from input definition to execution and state update.