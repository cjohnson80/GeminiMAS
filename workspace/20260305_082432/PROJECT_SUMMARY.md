# Project Summary: HeartbeatManager Architecture

## 1. Overview
The `HeartbeatManager` system is designed to periodically process structured input (expected to be derived from a continuous monitoring source or a scheduled trigger) formatted in Markdown. Its primary function is to safely parse this input to identify executable tasks, manage their execution state, and ensure thread-safe updates to the overall system state.

## 2. Core Components

### 2.1. `HeartbeatParser` (Module: `heartbeat_parser.py`)
*   **Responsibility:** Responsible for robustly parsing the raw Markdown input. It must identify specific directives (e.g., `[TASK]`, `[CONFIG_UPDATE]`, `[QUERY]`) using regex or a dedicated Markdown parser library (like `mistune` or custom state machine).
*   **Output:** A list of structured `HeartbeatInstruction` objects.
*   **Dependency:** Depends on `gemini_mas.py` for system context if needed, but primarily self-contained.

### 2.2. `HeartbeatInstruction` (Data Structure: `instruction_models.py`)
*   **Responsibility:** A Pydantic/dataclass model defining the standardized structure for any parsed instruction.
*   **Fields (Example):** `instruction_id` (UUID), `type` (Enum: TASK, CONFIG, QUERY), `payload` (Dict/Str), `target_module` (Str, e.g., 'ToolManager').

### 2.3. `TaskExecutor` (Module: `task_executor.py`)
*   **Responsibility:** Manages the execution lifecycle of parsed tasks. It routes instructions to the appropriate underlying system component (e.g., Shell execution, File I/O, Web API calls).
*   **Concurrency:** Must utilize the system's allowed thread pool (defined by `MAX_THREADS` in hardware profile) for parallel execution of non-blocking tasks.
*   **Dependency:** Depends on `ToolManager` (to access available tools) and the system's logging infrastructure.

### 2.4. `StateManager` (Module: `state_manager.py`)
*   **Responsibility:** Ensures thread-safe updates to shared system state (e.g., configuration variables, execution logs, cached results). Crucial for preventing race conditions when tasks modify global context.
*   **Mechanism:** Must employ locks (e.g., `threading.Lock` or `RLock`) around all write operations to shared resources.
*   **Dependency:** Depends on the central data store or in-memory cache.

## 3. Data Flow and Execution Pipeline

1.  **Input Reception:** Raw Markdown data is fed into the system (e.g., via a periodic thread or an external API call).
2.  **Parsing:** `HeartbeatParser` converts Markdown to a list of `HeartbeatInstruction` objects.
3.  **Dispatch:** The main loop iterates through instructions, dispatching them to the `TaskExecutor`.
4.  **Execution:** `TaskExecutor` runs the instruction, potentially calling external tools via the `ToolManager`.
5.  **State Update:** Upon successful or failed execution, the `TaskExecutor` notifies the `StateManager` to persist the result or update configuration safely.

## 4. Safety and Concurrency

*   **Parsing Safety:** The parser must sanitize input to prevent injection attacks if the source is untrusted. Markdown parsing should be sandboxed if possible.
*   **Execution Safety:** Tasks executed by `TaskExecutor` must adhere to strict execution time limits to prevent resource starvation.
*   **State Consistency:** All modifications to shared memory structures initiated by the heartbeat process **must** pass through the `StateManager` to guarantee atomicity and consistency, respecting the hardware profile's thread limits.

## 5. System Interfaces

| Component | Primary Interface | Description |
| :--- | :--- | :--- |
| `HeartbeatParser` | `parse(markdown_string: str) -> List[HeartbeatInstruction]` | Converts raw data to structured instructions. |
| `TaskExecutor` | `execute(instruction: HeartbeatInstruction)` | Initiates the defined action. |
| `StateManager` | `update_config(key, value)` / `get_log(id)` | Thread-safe access to system state. |
