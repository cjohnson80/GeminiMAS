# Project Summary: Heartbeat Processor Architecture

## 1. Goal
To create a robust, self-managing task execution engine (`heartbeat_processor.py`) that reads operational tasks from `HEARTBEAT.md`, executes them sequentially or concurrently based on priority/dependencies, and updates the status within the same file, ensuring system continuity.

## 2. Core Components & Data Flow

**A. `HEARTBEAT.md` (Data Source/Sink):**
*   **Format:** Markdown file containing structured task definitions (e.g., YAML blocks or custom delimited sections).
*   **Structure Example (Conceptual):**
    ```markdown
    --- TASK_ID: T-001, STATUS: PENDING, PRIORITY: HIGH ---
    Action: Web Search for latest ML architecture trends.
    --- END_TASK ---
    ```
*   **Data Flow:** Read $ightarrow$ Parse $ightarrow$ Execute $ightarrow$ Update Status $ightarrow$ Write Back.

**B. `heartbeat_processor.py` (The Engine):**
*   **Initialization:** Loads configuration from `local_config.json` (e.g., threading limits, tool availability). Uses `$AGENT_ROOT/bin/gemini_mas.py` as the core execution context.
*   **Task Reading & Parsing:**
    1.  Reads `HEARTBEAT.md` using file I/O.
    2.  Uses Regular Expressions or a dedicated Markdown parser to extract structured task objects.
*   **Execution Logic:**
    1.  **Concurrency Model:** Leverages Python's `concurrent.futures.ThreadPoolExecutor` (limited by `MAX_THREADS` from hardware profile, currently 2) for parallel execution of independent tasks.
    2.  **Task Dispatcher:** Maps task actions (e.g., 'Web Search', 'File Write') to available tool wrappers (e.g., `web_search`, `write_file`).
    3.  **Status Tracking:** Maintains an in-memory map of `TASK_ID` to current execution state (RUNNING, COMPLETE, FAILED).
*   **Persistence (Update):**
    1.  Once a task completes, the processor updates its status in the in-memory representation.
    2.  Periodically (or upon completion of all tasks), it reconstructs the `HEARTBEAT.md` file content, writing back the updated statuses.

## 3. Adherence to Evolution Rules & Conservation Principle

*   **Conservation Principle Enforcement:** If a specific task type or execution method defined in `HEARTBEAT.md` is deemed suboptimal or resource-intensive (e.g., verbose logging), the corresponding feature in the core codebase (`$AGENT_ROOT/bin/gemini_mas.py` or related utilities) **MUST NOT** be deleted.
*   **Disabling Mechanism:** Instead of removal, the feature must be globally disabled via the `local_config.json` file. The Heartbeat Processor must check this configuration before attempting to execute a disabled operation.
    *   *Example:* If `telemetry_verbose` is disabled, the processor skips any task instructing it to log verbose data, respecting the configuration set by the AGI.

## 4. Dependencies
*   `HEARTBEAT.md` (Input/Output Data)
*   `local_config.json` (Configuration/Constraints)
*   `$AGENT_ROOT/bin/gemini_mas.py` (Core logic access)
*   `concurrent.futures` (For thread pooling)